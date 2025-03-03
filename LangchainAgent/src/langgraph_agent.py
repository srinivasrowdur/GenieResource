"""
LangGraph Agent implementation for Resource Genie

This module implements a very simple agent using LangGraph to avoid compatibility issues.
"""

import os
import time
import json
import logging
from typing import Dict, List, Any, Optional, TypedDict, Union, Tuple
from datetime import datetime
import uuid
import hashlib

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Response schema
class AgentResponse(TypedDict):
    response: str
    execution_time: Optional[float]
    cached: bool

# Define cache entry structure
class CacheEntry:
    def __init__(self, response: str, timestamp: float, ttl: int = 3600):
        self.response = response
        self.timestamp = timestamp
        self.ttl = ttl

    def is_valid(self) -> bool:
        """Check if the cache entry is still valid."""
        return time.time() - self.timestamp < self.ttl

# Add state management class
class AgentState:
    """State management for the ReAct agent."""
    def __init__(self):
        self.previous_results = []  # Store previous query results
        self.current_context = {}   # Store current conversation context
        self.last_query = None      # Store last query parameters
        self.conversation_history = []  # Store conversation history
        self.metadata = None  # Store database metadata

    def update_metadata(self, metadata: dict):
        """Update metadata from database"""
        self.metadata = metadata

# Main agent class
class ReActAgentGraph:
    """
    A simple implementation of an agent that processes resource queries.
    """
    
    def __init__(
        self,
        model: BaseChatModel,
        firebase_client: Any = None,
        use_cache: bool = True,
        cache_ttl: int = 3600,
        verbose: bool = False
    ):
        """
        Initialize the ReActAgentGraph.
        
        Args:
            model: The language model to use for the agent.
            firebase_client: Firebase client for resource management.
            use_cache: Whether to use caching for responses.
            cache_ttl: Time to live (in seconds) for cached responses.
            verbose: Whether to enable verbose logging.
        """
        self.model = model
        self.firebase_client = firebase_client
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self.verbose = verbose
        
        # Cache management
        self._response_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Session management - simple dictionary
        self._sessions = {}
        
        # System prompt for resource queries
        self.system_prompt = """You are Resource Genie, an AI assistant that helps users find resources based on their needs.
        
        When a user asks about finding resources, try to identify:
        1. Locations mentioned (e.g., London, Manchester, Edinburgh)
        2. Skills mentioned (e.g., Python, Java, frontend, backend)
        3. Ranks or positions mentioned (e.g., Analyst, Consultant, Manager)
        
        If the user is looking for resources, respond in a helpful, conversational way.
        If the request isn't about resources, respond as a helpful assistant.
        """
        
        # Add state management
        self._state = {}  # Dictionary to store state per session
        
        logger.info("ReActAgentGraph initialized successfully")

    def _get_or_create_state(self, session_id: str) -> AgentState:
        """Get or create state for a session."""
        if session_id not in self._state:
            self._state[session_id] = AgentState()
        return self._state[session_id]

    def process_message(self, message: str, session_id: Optional[str] = None) -> AgentResponse:
        """
        Process a message using ReAct pattern.
        
        Args:
            message: The user's message to process.
            session_id: Optional session ID for tracking conversation history.
            
        Returns:
            A dictionary with the agent's response and performance metrics.
        """
        # Generate a session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            
        logger.info(f"Processing message for session {session_id}: {message}")
        
        # Try to get response from cache if caching is enabled
        if self.use_cache:
            cache_key = self._generate_cache_key(message)
            cached_response = self._get_from_cache(cache_key)
            
            if cached_response:
                logger.info(f"Cache hit for message: {message}")
                self._cache_hits += 1
                
                return {
                    "response": cached_response,
                    "cached": True,
                    "execution_time": 0.0
                }
            
            self._cache_misses += 1
        
        # Start timing
        start_time = time.time()
        
        try:
            # Get session state
            state = self._get_or_create_state(session_id)
            
            # Update metadata if needed
            if not state.metadata and self.firebase_client:
                try:
                    metadata = self.firebase_client.get_resource_metadata()
                    state.update_metadata(metadata)
                except Exception as e:
                    logger.error(f"Error fetching metadata: {e}")
            
            # First, let the agent reason about the query
            reasoning_prompt = f'''You are Resource Genie, an AI assistant that helps users find resources based on their needs.
            You have access to a database of employees and their availability information.
            
            Current date: {datetime.now().strftime("%Y-%m-%d")}
            Current week number: {datetime.now().isocalendar()[1]}
            
            Previous context: {state.current_context}
            Previous results: {len(state.previous_results)} resources found
            
            Available database metadata:
            {json.dumps(state.metadata, indent=2) if state.metadata else "Metadata not available"}
            
            The user's message is: "{message}"
            
            Your task is to analyze the query and return a STRICTLY FORMATTED JSON response.
            The response MUST follow this exact structure and contain only valid values:
            
            {{
                "query_type": "new_search" or "followup",
                "needs_availability": true or false,
                "time_period": {{
                    "type": "specific_weeks" or "relative",
                    "weeks": [valid week numbers between 1-52],
                    "relative_reference": "next_month" or "this_month" or "next_week" or null,
                    "reasoning": "Explain how you determined these weeks"
                }},
                "locations": {{
                    "mentioned": [locations exactly as mentioned in query],
                    "resolved": [must be from: {", ".join(state.metadata.get("locations", []))} if available],
                    "reasoning": "Explain how you mapped locations"
                }},
                "reasoning": "Explain your overall analysis",
                "next_action": "search_resources" or "fetch_availability" or "use_previous_results"
            }}
            
            Example for "Partners in Nordics":
            {{
                "query_type": "new_search",
                "needs_availability": false,
                "time_period": {{
                    "type": "specific_weeks",
                    "weeks": [],
                    "relative_reference": null,
                    "reasoning": "No time period mentioned in query"
                }},
                "locations": {{
                    "mentioned": ["Nordics"],
                    "resolved": ["Oslo", "Stockholm", "Copenhagen"],
                    "reasoning": "Nordics region maps to Oslo, Stockholm, and Copenhagen in our database"
                }},
                "reasoning": "New search for Partners in Nordic locations",
                "next_action": "search_resources"
            }}
            
            IMPORTANT: 
            1. Only use valid location names from the metadata
            2. Week numbers must be between 1 and 52
            3. Query type must be exactly "new_search" or "followup"
            4. All fields are required
            '''
            
            # Get the agent's analysis
            analysis_messages = [
                SystemMessage(content=reasoning_prompt),
                HumanMessage(content=message)
            ]
            
            analysis_response = self.model.invoke(analysis_messages)
            analysis = self._parse_json_response(analysis_response.content)
            logger.info(f"Query analysis: {analysis}")
            
            # Let the agent decide what to do next
            if analysis["needs_availability"]:
                # Handle availability query
                week_numbers = analysis["time_period"]["weeks"]
                logger.info(f"Weeks to check: {week_numbers}")
                
                if analysis["query_type"] == "followup":
                    resources = state.previous_results
                    logger.info(f"Using previous results ({len(resources)} resources)")
                else:
                    # New search with availability
                    resources = self._fetch_resources(analysis, state)
                
                # Fetch availability data
                if resources and week_numbers:
                    resources = self._fetch_availability(resources, week_numbers)
                
                # Generate response about availability
                response_text = self._generate_availability_response(resources, analysis, message)
            else:
                # Handle normal search
                resources = self._fetch_resources(analysis, state)
                response_text = self._generate_search_response(resources, analysis, message)
            
            # Update state
            state.previous_results = resources
            state.current_context.update({
                "last_query_type": analysis["query_type"],
                "last_time_period": analysis["time_period"],
                "last_locations": analysis["locations"]
            })
            
            # Handle caching and timing
            execution_time = time.time() - start_time
            if self.use_cache:
                self._add_to_cache(cache_key, response_text)
            
            logger.info(f"Message processed in {execution_time:.2f} seconds")
            
            return {
                "response": response_text,
                "execution_time": execution_time,
                "cached": False
            }
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            execution_time = time.time() - start_time
            
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "execution_time": execution_time,
                "cached": False
            }

    def reset(self, session_id: Optional[str] = None) -> None:
        """
        Reset the agent's state for a specific session or all sessions.
        
        Args:
            session_id: Optional session ID to reset. If None, resets all sessions.
        """
        if session_id:
            # Remove the specific session
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Reset session {session_id}")
            else:
                logger.warning(f"Session {session_id} not found")
        else:
            # Reset all sessions
            self._sessions = {}
            logger.info("Reset all sessions")

    def _generate_cache_key(self, message: str) -> str:
        """
        Generate a cache key for a message.
        
        Args:
            message: The message to generate a key for.
            
        Returns:
            A string representing the cache key.
        """
        # Generate a hash of the message for the cache key
        return hashlib.md5(message.encode('utf-8')).hexdigest()

    def _add_to_cache(self, key: str, response: str) -> None:
        """
        Add a response to the cache.
        
        Args:
            key: The cache key.
            response: The response to cache.
        """
        self._response_cache[key] = CacheEntry(
            response=response,
            timestamp=time.time(),
            ttl=self.cache_ttl
        )

    def _get_from_cache(self, key: str) -> Optional[str]:
        """
        Get a response from the cache if it exists and is valid.
        
        Args:
            key: The cache key.
            
        Returns:
            The cached response or None if not found or expired.
        """
        if key in self._response_cache:
            entry = self._response_cache[key]
            
            if entry.is_valid():
                return entry.response
            else:
                # Remove expired entry
                del self._response_cache[key]
                
        return None

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._response_cache = {}
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, Union[int, float]]:
        """
        Get statistics about the cache.
        
        Returns:
            A dictionary with cache statistics.
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0
        
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": hit_rate,
            "size": len(self._response_cache)
        }

    # Add back the extraction prompt
    def extract_query_parameters(self, message: str) -> Dict[str, List[str]]:
        """
        Extract query parameters from a user's message.
        
        Args:
            message: The user's message to extract parameters from.
            
        Returns:
            A dictionary containing extracted parameters.
        """
        # Step 1: Extract query parameters using the model
        extraction_prompt = """You are an expert at parsing resource queries. 
        Extract structured information from user queries about finding resources.
        
        Your task is to extract the following information:
        - locations: List of locations mentioned in the query
        - skills: List of skills or technologies mentioned in the query
        - ranks: List of job ranks or levels mentioned in the query
        
        ONLY USE THE FOLLOWING VALUES FROM OUR DATABASE:
        
        AVAILABLE LOCATIONS:
        - Manchester
        - London
        - Oslo
        - Stockholm
        - Copenhagen
        - Belfast
        - Bristol
        
        AVAILABLE RANKS:
        - Partner
        - Associate Partner
        - Consulting Director
        - Principal Consultant
        - Managing Consultant
        - Senior Consultant
        - Consultant
        - Consultant Analyst
        - Analyst
        
        AVAILABLE SKILLS:
        - DevOps Engineer
        - Data Engineer
        - Business Analyst
        - Scrum Master
        - Frontend Developer
        - Backend Developer
        - Full Stack Developer
        - Agile Coach
        - Cloud Engineer
        - UX Designer
        - Project Manager
        - Product Owner
        - Python
        - Java
        - JavaScript
        - .NET
        
        REGION MAPPINGS:
        If the query mentions a region, map to ONLY these cities that exist in our database:
        - "Nordics" or "Scandinavia" -> ["Oslo", "Stockholm", "Copenhagen"]
        - "UK" or "United Kingdom" -> ["London", "Manchester", "Belfast", "Bristol"]
        
        Examples:
        
        1. For "Find Python developers in London", you would extract:
        {
            "locations": ["London"],
            "skills": ["Python"],
            "ranks": []
        }
        
        2. For "Partners in Manchester", you would extract:
        {
            "locations": ["Manchester"],
            "skills": [],
            "ranks": ["Partner"]
        }
        
        3. For "Partners in Nordics", you would extract:
        {
            "locations": ["Oslo", "Stockholm", "Copenhagen"],
            "skills": [],
            "ranks": ["Partner"]
        }
        
        IMPORTANT: Only use locations, skills and ranks from the lists above.
        Return ONLY the JSON without any other text.
        """
        
        extraction_messages = [
            SystemMessage(content=extraction_prompt),
            HumanMessage(content=f"Parse this resource query: '{message}'")
        ]
        
        # Get the extraction response
        extraction_response = self.model.invoke(extraction_messages)
        extraction_content = extraction_response.content
        
        # Extract JSON if it's within a code block
        if "```json" in extraction_content:
            extraction_content = extraction_content.split("```json")[1].split("```")[0].strip()
        elif "```" in extraction_content:
            extraction_content = extraction_content.split("```")[1].split("```")[0].strip()
        
        try:
            query_params = json.loads(extraction_content)
            logger.info(f"Extracted parameters: {query_params}")
        except:
            # Default parameters if parsing fails
            query_params = {
                "locations": [],
                "skills": [],
                "ranks": []
            }
            logger.warning(f"Failed to parse extracted parameters, using defaults")
        
        return query_params 

    def _fetch_resources(self, analysis: dict, state: AgentState) -> List[dict]:
        """Fetch resources based on analysis with strict parameter validation."""
        try:
            # Define valid parameters from metadata
            valid_params = {
                "locations": state.metadata.get("locations", []),
                "skills": state.metadata.get("skills", []),
                "ranks": state.metadata.get("ranks", [])
            }

            # Extract and validate locations
            locations = [
                loc for loc in analysis["locations"]["resolved"]
                if loc in valid_params["locations"]
            ]

            # Get other parameters with strict validation
            params_prompt = f"""You are a parameter validator for database queries.
            Your task is to extract search parameters that EXACTLY match our database values.

            VALID VALUES (only these can be used):
            LOCATIONS: {json.dumps(valid_params["locations"])}
            SKILLS: {json.dumps(valid_params["skills"])}
            RANKS: {json.dumps(valid_params["ranks"])}

            User Query Analysis:
            {json.dumps(analysis, indent=2)}

            Return a JSON object with EXACTLY this structure:
            {{
                "skills": [list of skills from VALID SKILLS only],
                "ranks": [list of ranks from VALID RANKS only],
                "validation_notes": "Explain which parameters were valid/invalid"
            }}

            IMPORTANT:
            - Only use values from the valid lists
            - Invalid values will be ignored
            - Lists can be empty if no valid values found
            """
            
            params_response = self.model.invoke([SystemMessage(content=params_prompt)])
            params = self._parse_json_response(params_response.content)
            
            # Validate parameters
            validated_params = {
                "locations": locations,
                "skills": [s for s in params["skills"] if s in valid_params["skills"]],
                "ranks": [r for r in params["ranks"] if r in valid_params["ranks"]],
                "collection": "employees",
                "nested_ranks": True
            }

            logger.info(f"Validated parameters for Firebase: {validated_params}")
            if params.get("validation_notes"):
                logger.info(f"Validation notes: {params['validation_notes']}")

            return self.firebase_client.get_resources(**validated_params)

        except Exception as e:
            logger.error(f"Error in parameter validation: {e}")
            return []

    def _fetch_availability(self, resources: List[dict], week_numbers: List[int]) -> List[dict]:
        """Fetch availability data with strict parameter validation."""
        try:
            # Validate employee numbers
            employee_numbers = [
                str(r.get('employee_number')) 
                for r in resources 
                if r.get('employee_number') and str(r.get('employee_number')).startswith('EMP')
            ]

            # Validate week numbers
            valid_weeks = [
                w for w in week_numbers 
                if isinstance(w, int) and 1 <= w <= 52
            ]

            if not valid_weeks:
                logger.warning(f"No valid week numbers found in: {week_numbers}")
                return resources

            if not employee_numbers:
                logger.warning("No valid employee numbers found")
                return resources

            logger.info(f"Fetching availability for {len(employee_numbers)} employees in weeks {valid_weeks}")
            
            availability_data = self.firebase_client._fetch_availability_batch(
                employee_numbers=employee_numbers,
                week_numbers=valid_weeks
            )
            
            # Add availability data to resources
            for resource in resources:
                emp_num = str(resource.get('employee_number'))
                resource['availability'] = availability_data.get(emp_num, [])

            return resources

        except Exception as e:
            logger.error(f"Error in availability validation: {e}")
            return resources

    def _generate_availability_response(self, resources: List[dict], analysis: dict, message: str) -> str:
        """Generate response for availability queries with structured data."""
        prompt = f"""You are Resource Genie, an AI assistant that helps users find resources based on their needs.
        
        Query Analysis:
        {json.dumps(analysis, indent=2)}
        
        Resource Data:
        {json.dumps([{
            'name': r.get('name'),
            'location': r.get('location'),
            'rank': r.get('rank', {}).get('official_name') if isinstance(r.get('rank'), dict) else r.get('rank'),
            'availability': r.get('availability', [])
        } for r in resources], indent=2)}
        
        Generate a response that includes:
        1. Clear summary of who is available/unavailable
        2. Specific availability status for each week requested
        3. Any relevant notes about availability
        4. Suggestions if no one is available
        
        Format numbers and lists clearly in your response.
        """
        
        response = self.model.invoke([SystemMessage(content=prompt)])
        return response.content

    def _generate_search_response(self, resources: List[dict], analysis: dict, message: str) -> str:
        """Generate response for search queries."""
        prompt = f"""You are Resource Genie, an AI assistant that helps users find resources based on their needs.
        
        The user's query: "{message}"
        
        Analysis of the query:
        {json.dumps(analysis, indent=2)}
        
        Here are the matching resources:
        {json.dumps([{
            'name': r.get('name'),
            'location': r.get('location'),
            'rank': r.get('rank', {}).get('official_name') if isinstance(r.get('rank'), dict) else r.get('rank'),
            'skills': r.get('skills', [])
        } for r in resources], indent=2)}
        
        Please provide a helpful summary of the results. If no resources match, suggest ways to broaden the search.
        Be concise but informative.
        """
        
        response = self.model.invoke([SystemMessage(content=prompt)])
        return response.content

    def _parse_json_response(self, content: str) -> dict:
        """Parse and validate JSON from LLM response."""
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(content)
            
            # Log the parsed structure for debugging
            logger.info(f"Parsed JSON structure: {list(parsed.keys())}")
            
            return parsed
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.error(f"Raw content: {content}")
            raise 