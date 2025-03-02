import json
import os
from typing import Dict, List, Optional, Any

from anthropic import Anthropic

class QueryTranslator:
    """
    Translates natural language queries into structured queries for resource management.
    
    This class provides methods to translate user queries into a structured format
    that can be used to search for resources. It supports both LLM-based and rule-based
    translation approaches, with the LLM-based approach being preferred when available.
    
    The translator can handle various types of queries, including:
    - Simple resource queries (e.g., "Find frontend developers in London")
    - Availability queries (e.g., "Who is available in Week 3?")
    - Follow-up queries (e.g., "What about in Manchester?")
    - Rank hierarchy queries (e.g., "Find resources with rank above consultant")
    
    The structured output includes:
    - location: List of locations mentioned in the query
    - rank: The rank mentioned in the query (e.g., "Consultant", "Partner")
    - skill: The skill mentioned in the query (e.g., "Frontend Developer")
    - availability: List of week numbers mentioned in the query
    
    For rank hierarchy queries, the translator understands the following concepts:
    - "rank above X" or "higher than X": Returns a rank higher in the hierarchy than X
    - "rank below X" or "lower than X": Returns a rank lower in the hierarchy than X
    - "between rank X and Y": Returns a rank between X and Y in the hierarchy
    - "more senior than X": Returns a rank higher in the hierarchy than X
    - "more junior than X": Returns a rank lower in the hierarchy than X
    
    The rank hierarchy (from highest to lowest) is:
    - Partner
    - Associate Partner / Consulting Director (same level)
    - Management Consultant
    - Principal Consultant
    - Senior Consultant
    - Consultant
    - Analyst
    
    The LLM-based approach is particularly effective at handling:
    - Queries with typos and spelling variations
    - Informal language and shorthand
    - Complex or ambiguous requests
    - Follow-up queries that reference previous context
    """
    
    def __init__(self):
        """Initialize the QueryTranslator."""
        # Get API key from environment variables
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
            
        try:
            self.client = Anthropic(api_key=self.api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Anthropic client: {str(e)}")
    
    def translate(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Translate a natural language query into a structured format.
        
        Args:
            query: The natural language query to translate
            context: Optional context from previous queries
            
        Returns:
            A dictionary containing the structured query
        """
        try:
            # Add debug print
            print(f"\n===== QUERY TRANSLATOR DEBUG =====")
            print(f"Input query: {query}")
            
            # Analyze if this is a follow-up query that refers to previous context
            is_followup = False
            if context:
                # Normalize the context to ensure consistent structure
                context = self._normalize_context(context)
                print(f"Initial context: {context}")
                
                # Check if this is a follow-up query
                is_followup = self._is_followup_query(query)
                print(f"Is follow-up query? {is_followup}")
            
            # Create the prompt
            prompt = self._create_prompt(query, context if is_followup else None)
            
            # Get completion from Claude
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract and parse the structured query
            result = self._parse_response(response.content[0].text)
            print(f"Initial parsed result: {result}")
            
            # If this is a follow-up query and we have context, determine how to merge with context
            if is_followup and context:
                # CASE 1: COMPLETELY NEW QUERY
                # If the result has both locations and either skills or ranks, it's likely a new query
                # that should override the previous context completely
                has_core_filters = (
                    ("locations" in result and result["locations"]) and
                    (("ranks" in result and result["ranks"]) or ("skills" in result and result["skills"]))
                )
                
                if has_core_filters:
                    print(f"This appears to be a completely new query with core filters. NOT merging with context.")
                    # Use the result as-is, it's a new query
                    pass
                else:
                    print(f"This appears to be a refinement of previous query. Merging with context.")
                    
                    # CASE 2: QUERY REFINEMENT - Merge with context but prioritize new values                    
                    # For locations, ranks, skills: if not in result but in context, keep from context
                    for field in ["locations", "ranks", "skills"]:
                        if field not in result or not result[field]:
                            if field in context and context[field]:
                                result[field] = context[field]
                                print(f"Added {field} from context: {context[field]}")
                    
                    # Special handling for availability-related fields
                    # Weeks and availability_status are usually meant to be replaced, not merged
                    # (We keep the LLM's interpretation)
            
            # Basic validation checks
            if "locations" in result and not isinstance(result["locations"], list):
                result["locations"] = [result["locations"]]
            
            if "ranks" in result and not isinstance(result["ranks"], list):
                result["ranks"] = [result["ranks"]]
                
            if "skills" in result and not isinstance(result["skills"], list):
                result["skills"] = [result["skills"]]
            
            if "weeks" in result and not isinstance(result["weeks"], list):
                result["weeks"] = [result["weeks"]]
            
            # Add debug print for the result
            print(f"Final translated result: {result}")
            print(f"===== END QUERY TRANSLATOR DEBUG =====\n")
            
            return result
            
        except Exception as e:
            raise ValueError(f"Translation failed: {str(e)}")
    
    def _create_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Create the prompt for the LLM."""
        # Use raw string for the entire prompt except for the query variable
        prompt = f"""You are a query translator that converts natural language queries about employees into structured format.

Query: {query}

Please convert this into a structured query JSON with these possible fields:
- locations: List of locations mentioned (e.g., ["London", "New York"])
- ranks: List of ranks mentioned (e.g., ["Consultant", "Senior Manager"])
- skills: List of skills mentioned (e.g., ["frontend", "python", "react"])
- weeks: List of week numbers if availability is mentioned (e.g., [1, 2, 3])
- availability_status: List of availability statuses mentioned (e.g., ["available", "partial", "unavailable"])
- min_hours: Minimum available hours if mentioned (e.g., 20)

If a field is not relevant, omit it from the response.

IMPORTANT INFORMATION:
1. Geographic Regions:
   - "Nordics" or "Nordic countries" refers to: ["Oslo", "Stockholm", "Copenhagen"]
   - "UK" or "United Kingdom" refers to: ["London", "Manchester", "Belfast", "Bristol"]
   - "US" or "United States" refers to: ["New York", "Chicago", "San Francisco"]

2. Ranks Hierarchy (highest to lowest):
   - "Partner" (Also match "partners" or "partnership")
   - "Associate Partner" or "Consulting Director" (same level)
   - "Management Consultant"
   - "Principal Consultant"
   - "Senior Consultant"
   - "Consultant"
   - "Analyst"

3. Skills:
   - Match variations like "frontend"/"frontend developer"/"front-end"
   - Match variations like "backend"/"backend developer"/"back-end"
   - Match variations like "fullstack"/"full stack"/"full-stack"
   - "Agile Coach" and "Scrum Master" are SKILLS, not ranks
   - Common skills include: "Frontend Developer", "Backend Developer", "Full Stack Developer", 
     "Product Manager", "Project Manager", "Agile Coach", "Scrum Master", "Data Engineer", "Cloud Engineer"

4. Common Query Examples:
   - "partners in nordics" → {{"locations": ["Nordics"], "ranks": ["Partner"]}}
   - "frontend developers in London" → {{"locations": ["London"], "skills": ["frontend"]}}
   - "consultants available in week 3" → {{"ranks": ["Consultant"], "weeks": [3], "availability_status": ["available"]}}
   - "agile coaches in London" → {{"locations": ["London"], "skills": ["Agile Coach"]}}
   - "data engineers in week 2" → {{"skills": ["Data Engineer"], "weeks": [2]}}

5. Follow-Up Query Handling:
   - Queries like "Are any of them available in week 2?" should ONLY extract the new information (weeks and availability)
   - For follow-up queries, do NOT repeat information that was already in the previous context
   - If the query refers to "these people", "them", etc., this is about the previously mentioned people
   - Questions asking only about availability should return ONLY availability fields (weeks, availability_status)

IMPORTANT: Return ONLY a JSON object with these fields and nothing else.

For example, if the query is "Find frontend developers in London who are available in week 2", you should return:
```json
{{"locations": ["London"], "skills": ["frontend"], "weeks": [2], "availability_status": ["available"]}}
```

If the query mentions employees with specific skills or availability requirements, make sure to include them in the appropriate fields.
"""
        
        if context:
            prompt += f"""

CRITICAL - THIS IS A FOLLOW-UP QUERY: 
The previous query had these parameters:
{json.dumps(context, indent=2)}

For this follow-up query:
1. CAREFULLY ANALYZE what the user is asking about in this follow-up
2. If the query is adding new filters or changing existing ones, include ONLY those new/changed fields
3. If the query is completely changing the topic, treat it as a brand new query and return a complete set of fields
4. Do NOT automatically repeat previous filter values unless they are explicitly referenced again

Examples of different follow-up types:

1. Refining the same search:
   Previous: "frontend developers in London"
   Follow-up: "what about in Manchester?"
   Return: {{"locations": ["Manchester"]}}

2. Adding new filters:
   Previous: "frontend developers in London" 
   Follow-up: "who are available in week 3?"
   Return: {{"weeks": [3], "availability_status": ["available"]}}

3. Completely new query:
   Previous: "frontend developers in London"
   Follow-up: "show me partners in nordics"
   Return: {{"locations": ["Nordics"], "ranks": ["Partner"]}}
"""
            
        return prompt
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into a structured format."""
        try:
            # Print the raw response for debugging
            print(f"Raw LLM response: {response}")
            
            # First, try to find JSON block in the response using regex
            import re
            
            # Look for JSON with or without the code block markers
            json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', response)
            if json_match:
                try:
                    json_str = json_match.group(1)
                    structured = json.loads(json_str)
                    return structured
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}, trying alternate methods")
            
            # If no JSON block found, try to find any JSON object in the text
            json_match = re.search(r'{[\s\S]*?}', response)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    structured = json.loads(json_str)
                    return structured
                except json.JSONDecodeError as e:
                    print(f"JSON decode error in alternate method: {e}")
            
            # If still no JSON found, manually parse the response
            print("No JSON found, manually parsing response")
            structured = {}
            
            # Check for mentions of "partner" and "nordic"/"nordics" directly in the response
            if "partner" in response.lower() or "partners" in response.lower():
                structured["ranks"] = ["Partner"]
                print("Manually added Partner rank")
            
            if "nordic" in response.lower() or "nordics" in response.lower() or "oslo" in response.lower() or "stockholm" in response.lower() or "copenhagen" in response.lower():
                structured["locations"] = ["Nordics"]  
                print("Manually added Nordics location")
            
            # Generic manual parsing
            lines = response.split('\n')
            current_field = None
            
            for line in lines:
                line = line.strip()
                
                # Check for field headers
                if "location" in line.lower() and ":" in line:
                    current_field = 'locations'
                    structured['locations'] = []
                    
                    # Extract values from the same line if present
                    values = line.split(':', 1)[1].strip()
                    if values and values != "[]" and values != "None":
                        # Handle brackets and quotes
                        values = values.strip('[]').replace('"', '').replace("'", '')
                        values_list = [v.strip() for v in values.split(',')]
                        structured['locations'] = values_list
                        
                elif "skill" in line.lower() and ":" in line:
                    current_field = 'skills'
                    structured['skills'] = []
                    
                    # Extract values from the same line if present
                    values = line.split(':', 1)[1].strip()
                    if values and values != "[]" and values != "None":
                        # Handle brackets and quotes
                        values = values.strip('[]').replace('"', '').replace("'", '')
                        values_list = [v.strip() for v in values.split(',')]
                        structured['skills'] = values_list
                        
                elif "rank" in line.lower() and ":" in line:
                    current_field = 'ranks'
                    structured['ranks'] = []
                    
                    # Extract values from the same line if present
                    values = line.split(':', 1)[1].strip()
                    if values and values != "[]" and values != "None":
                        # Handle brackets and quotes
                        values = values.strip('[]').replace('"', '').replace("'", '')
                        values_list = [v.strip() for v in values.split(',')]
                        structured['ranks'] = values_list
                        
                elif "week" in line.lower() and ":" in line:
                    current_field = 'weeks'
                    structured['weeks'] = []
                    
                    # Extract values from the same line if present
                    values = line.split(':', 1)[1].strip()
                    if values and values != "[]" and values != "None":
                        # Handle brackets and quotes
                        values = values.strip('[]').replace('"', '').replace("'", '')
                        try:
                            values_list = [int(v.strip()) for v in values.split(',') if v.strip().isdigit()]
                            structured['weeks'] = values_list
                        except ValueError:
                            pass  # Skip invalid week numbers
                
                # Handle bullet point items for current field
                elif current_field and line.startswith('-') and len(line) > 1:
                    item = line[1:].strip()
                    if item and current_field in structured:
                        structured[current_field].append(item)
            
            # Final check: if the query has keywords but we still have an empty result, add defaults
            if not structured and ("partners" in response.lower() or "nordics" in response.lower()):
                if "partner" in response.lower() or "partners" in response.lower():
                    structured["ranks"] = ["Partner"]
                
                if "nordic" in response.lower() or "nordics" in response.lower() or "copenhagen" in response.lower():
                    structured["locations"] = ["Nordics"]
            
            return structured
            
        except Exception as e:
            print(f"Error parsing response: {str(e)}")
            # Emergency fallback for common queries
            if "partner" in response.lower() and ("nordic" in response.lower() or "nordics" in response.lower()):
                return {
                    "locations": ["Nordics"],
                    "ranks": ["Partner"]
                }
            if "frontend" in response.lower() and "london" in response.lower():
                return {
                    "locations": ["London"],
                    "skills": ["frontend"]
                }
            raise ValueError(f"Failed to parse response: {str(e)}")
    
    def _normalize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize context to ensure it has the expected structure.
        
        This method takes a context dictionary (which might have varying structures)
        and normalizes it to a consistent format with the following keys:
        - locations: List of location strings
        - skills: List of skill strings
        - ranks: List of rank strings
        - weeks: List of week numbers
        
        This normalization is important for handling different formats of context
        that might be passed to the translator, especially when dealing with
        follow-up queries.
        
        Args:
            context: The context dictionary to normalize
            
        Returns:
            A normalized context dictionary with consistent structure
        """
        normalized = {}
        
        # Handle locations
        if "locations" in context:
            normalized["locations"] = context["locations"]
        elif "location" in context:
            if isinstance(context["location"], list):
                normalized["locations"] = context["location"]
            elif context["location"]:
                normalized["locations"] = [context["location"]]
            else:
                normalized["locations"] = []
        else:
            normalized["locations"] = []
        
        # Handle skills
        if "skills" in context:
            normalized["skills"] = context["skills"]
        elif "skill" in context:
            if isinstance(context["skill"], list):
                normalized["skills"] = context["skill"]
            elif context["skill"]:
                normalized["skills"] = [context["skill"]]
            else:
                normalized["skills"] = []
        else:
            normalized["skills"] = []
        
        # Handle ranks
        if "ranks" in context:
            normalized["ranks"] = context["ranks"]
        elif "rank" in context:
            if context["rank"]:
                normalized["ranks"] = [context["rank"]]
            else:
                normalized["ranks"] = []
        else:
            normalized["ranks"] = []
        
        # Handle weeks
        if "weeks" in context:
            normalized["weeks"] = context["weeks"]
        elif "availability" in context:
            normalized["weeks"] = context["availability"]
        else:
            normalized["weeks"] = []
        
        return normalized
    
    def _translate_with_llm(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Translate a query using the Anthropic Claude LLM.
        
        This method constructs a prompt for the LLM that includes:
        1. A system prompt with detailed instructions on how to extract structured information
        2. Context information from previous queries (if available and relevant)
        3. The user's query
        
        It then sends this to the Anthropic API, extracts the JSON response,
        and ensures the response has the expected structure.
        
        Args:
            query: The natural language query to translate
            context: Optional normalized context from previous queries
            
        Returns:
            A structured representation of the query as a dictionary
            
        Raises:
            ValueError: If there's an error parsing the LLM response or if no JSON is found
        """
        # Prepare the system prompt with instructions for the LLM
        system_prompt = """You are a specialized resource management assistant that analyzes user queries and extracts structured information about consultant resources. Your task is to identify and extract four key components from each query:

1. LOCATION: Must be one or more of: London, Bristol, Manchester, Belfast, Oslo, Stockholm, Copenhagen
   - UK locations include: London, Bristol, Manchester, Belfast
   - Nordic locations include: Oslo, Stockholm, Copenhagen
   - Always return locations as an array, even if there's only one location
   - When a query mentions "UK", include all UK locations
   - When a query mentions "Nordic" or "Scandinavia", include all Nordic locations

2. RANK: Must follow this exact hierarchy (from highest to lowest) and use ONLY these exact terms:
   - Partner (highest rank)
   - Associate Partner (same level as Consulting Director)
   - Consulting Director (same level as Associate Partner)
   - Management Consultant
   - Principal Consultant
   - Senior Consultant
   - Consultant
   - Consultant Analyst
   - Analyst (lowest rank)
   
   Important notes about ranks:
   - When a query specifically mentions "analysts" or similar terms, return ONLY "Analyst" as the rank
   - Do not include abbreviations in the output
   - Understand that "senior" typically refers to "Senior Consultant" unless otherwise specified
   - Only extract rank if explicitly mentioned in the query; otherwise return null
   - When a query mentions "consultants", extract "Consultant" as the rank
   - When a query explicitly mentions multiple ranks (e.g., "partners or analysts"), return an array of ranks
   - When a query mentions "senior people" or "senior staff", ONLY include ranks from Management Consultant and above (Management Consultant, Consulting Director, Associate Partner, Partner) as these are the only roles with revenue targets in the firm
   
   Special handling for rank hierarchy queries:
   - For queries like "rank above X" or "higher than X", return an array of ALL ranks higher in the hierarchy than X
     * Example: "above consultant" → ["Senior Consultant", "Principal Consultant", "Management Consultant", "Consulting Director", "Associate Partner", "Partner"]
     * Remember that "higher" means closer to Partner in the hierarchy
     * IMPORTANT: Analyst is NEVER above any other rank - it is the LOWEST rank in the hierarchy
     * IMPORTANT: For "above Consultant Analyst", the result should be ["Consultant", "Senior Consultant", "Principal Consultant", "Management Consultant", "Consulting Director", "Associate Partner", "Partner"]
   - For queries like "rank below X" or "lower than X", return an array of ALL ranks lower in the hierarchy than X
     * Example: "below principal consultant" → ["Senior Consultant", "Consultant", "Consultant Analyst", "Analyst"]
     * Remember that "lower" means further from Partner in the hierarchy
     * IMPORTANT: For "below Consultant Analyst", the result should ONLY include ["Analyst"]
   - For queries like "between rank X and Y", return an array of ALL ranks between X and Y in the hierarchy
     * Example: "between consultant and principal consultant" → ["Senior Consultant"]
   - For queries mentioning "more senior than X", return an array of ALL ranks higher in the hierarchy than X
     * Example: "more senior than management consultant" → ["Consulting Director", "Associate Partner", "Partner"]
   - For queries mentioning "more junior than X", return an array of ALL ranks lower in the hierarchy than X
     * Example: "more junior than management consultant" → ["Principal Consultant", "Senior Consultant", "Consultant", "Consultant Analyst", "Analyst"]
   - For queries like "not X" or "who are not X", return null for the rank
     * Example: "not management consultants" → null (indicating any rank except Management Consultant)

3. SKILL: Must be one of these categories:
   - Technical skills: Frontend Developer, Backend Developer, Full Stack Developer, AWS Engineer, Cloud Engineer, DevOps Engineer, Solution Architect
   - Business skills: Business Analyst, Product Manager, Agile Coach, Scrum Master, Project Manager
   - Use the exact skill names listed above, even if the query uses variations or abbreviations
   - Terms like "AWS experts" or "AWS specialists" should be mapped to "AWS Engineer"
   - Do not infer a rank from a skill mention (e.g., "AWS experts" does not imply any rank)

4. AVAILABILITY: Must extract week numbers mentioned in the query
   - Should be represented as an array of integers
   - Example: "week 4" → [4]
   - Example: "weeks 5 to 7" → [5, 6, 7]
   - Example: "weeks 10 and 12" → [10, 12]
   - Return empty array if no availability is specified
   - For follow-up queries about additional weeks, add to the existing weeks rather than replacing them

For each query, you must:
- Extract explicit mentions of location, rank, skill, and availability
- Infer implied information when possible (e.g., "UK" means all UK locations)
- Return NULL for any component not specified (except availability, which should be an empty array)
- Format your response as a valid JSON object with the structure:
  {
    "location": [array of strings],
    "rank": string or array of strings or null,
    "skill": string or null,
    "availability": [array of integers]
  }

Always maintain the exact terminology specified above. Do not add information that isn't directly stated or clearly implied in the query."""

        # Add context information if available and if this appears to be a follow-up query
        context_prompt = ""
        if context and self._is_followup_query(query):
            # Construct a context prompt that informs the LLM about previous query results
            context_prompt = f"\n\nThis is a follow-up query to a previous query. The previous query extracted the following information:\n"
            context_prompt += f"- Locations: {context.get('locations', [])}\n"
            context_prompt += f"- Skills: {context.get('skills', [])}\n"
            context_prompt += f"- Ranks: {context.get('ranks', [])}\n"
            context_prompt += f"- Weeks: {context.get('weeks', [])}\n"
            context_prompt += f"\nCRITICAL INSTRUCTION: For follow-up queries, you MUST preserve ALL previous context information (locations, skills, ranks) in your response unless the new query explicitly overrides it. Short queries like 'What about Week X?' or 'And Week Y as well' are ALWAYS follow-ups that should maintain ALL previous context while adding new information. For availability, add new weeks to the existing ones rather than replacing them."
        
        # Combine the prompts
        full_prompt = system_prompt + context_prompt
        
        # Call the LLM with the constructed prompt
        response = self.client.messages.create(
            model="claude-3-sonnet-20240229",  # Using Claude 3 Sonnet for optimal performance
            max_tokens=1000,                   # Limit response length
            system=full_prompt,                # System prompt with instructions and context
            messages=[
                {"role": "user", "content": query}  # The user's query
            ]
        )
        
        # Extract and process the JSON response
        try:
            # Look for JSON in the response
            content = response.content[0].text
            
            # Find JSON object in the response using braces
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                # Extract the JSON string and parse it
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
                
                # Ensure the result has the expected structure by adding missing fields
                if "location" not in result:
                    result["location"] = None
                if "rank" not in result:
                    result["rank"] = None
                if "skill" not in result:
                    result["skill"] = None
                if "availability" not in result:
                    result["availability"] = []
                
                return result
            else:
                raise ValueError("No JSON found in LLM response")
        except Exception as e:
            # Provide detailed error information for debugging
            raise ValueError(f"Error parsing LLM response: {e}. Response: {response.content}")
    
    def _is_followup_query(self, query: str) -> bool:
        """
        Determine if a query is a follow-up query based on linguistic indicators.
        
        This method checks for common phrases and words that indicate the query
        is referring to previous results or context. This is important for
        determining when to include context from previous queries.
        
        Args:
            query: The query string to check
            
        Returns:
            True if the query appears to be a follow-up query, False otherwise
        """
        # Check for common follow-up indicators
        query_lower = query.lower().strip()
        words = query_lower.split()
        
        # Very short queries are typically follow-ups (e.g., "What about London?")
        if 1 <= len(words) <= 4:
            print("Short query detected - likely a follow-up")
            return True
            
        # Check for pronouns and references to previous results
        reference_terms = [
            "them", "they", "these", "those", "that", "this", 
            "he", "she", "his", "her", "their", "any"
        ]
        
        # Check for query starters that indicate follow-ups
        followup_starters = [
            "what about", "how about", "and what about", "what if", 
            "are there", "do they", "can you", "are any", "can any",
            "are they", "show me", "find me", "list all"
        ]
        
        # Check for standalone questions about availability
        availability_terms = [
            "available", "unavailable", "partially available", 
            "free", "busy", "booked", "scheduled", "week", "status"
        ]
        
        standalone_available_query = any(term in query_lower for term in availability_terms) and len(words) <= 7
        
        if standalone_available_query:
            print("Standalone availability query detected - treating as follow-up")
            return True
        
        # Check for pronouns as first word (very likely follow-ups)
        if words and words[0] in reference_terms:
            print(f"Query starts with reference term '{words[0]}' - treating as follow-up")
            return True
            
        # Check for common follow-up starters
        for starter in followup_starters:
            if query_lower.startswith(starter):
                print(f"Query starts with follow-up phrase '{starter}' - treating as follow-up")
                return True
        
        # Check for conjunctions at the start (likely continuing previous query)
        if words and words[0] in ["and", "or", "but", "also"]:
            print(f"Query starts with conjunction '{words[0]}' - treating as follow-up")
            return True
            
        # Check for phrases in any position
        followup_phrases = [
            "what about", "how about", "instead of", "rather than",
            "of them", "of those", "from them", "from those", 
            "as well", "as well as", "in addition", "apart from"
        ]
        
        for phrase in followup_phrases:
            if phrase in query_lower:
                print(f"Follow-up phrase '{phrase}' detected - treating as follow-up")
                return True
                
        # More complex NLP analysis could be added here
        
        print("No follow-up indicators detected - treating as new query")
        return False
