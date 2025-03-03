"""
LangGraph Agent implementation for Resource Genie using function calling and workflows.

This module implements a very simple agent using LangGraph to avoid compatibility issues.
"""

import os
import time
import json
import logging
from typing import Dict, List, Any, Optional, TypedDict, Union, Tuple, Literal
from datetime import datetime
import uuid
import hashlib
import random

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool, tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define schema models
class TimeRange(BaseModel):
    type: Literal["specific_weeks", "relative"]
    weeks: List[int] = Field(description="List of week numbers between 1-52")
    relative_reference: Optional[Literal["next_month", "this_month", "next_week"]] = None
    reasoning: str

class LocationInfo(BaseModel):
    mentioned: List[str] = Field(description="Locations as mentioned in query")
    resolved: List[str] = Field(description="Actual database locations")
    reasoning: str

class QueryAnalysis(BaseModel):
    query_type: Literal["new_search", "followup"]
    needs_availability: bool
    time_period: TimeRange
    locations: LocationInfo
    reasoning: str
    next_action: Literal["search_resources", "fetch_availability", "use_previous_results"]

class SearchParams(BaseModel):
    locations: List[str]
    skills: List[str]
    ranks: List[str]
    validation_notes: str

class AgentState(BaseModel):
    """State management for the ReAct agent."""
    session_id: str
    current_message: str
    previous_results: List[dict] = Field(default_factory=list)
    current_context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None
    analysis: Optional[QueryAnalysis] = None
    search_params: Optional[SearchParams] = None
    resources: Optional[List[dict]] = None
    availability_data: Optional[Dict[str, List[dict]]] = None
    final_response: Optional[str] = None
    error: Optional[str] = None

# Define function schemas
FUNCTION_SCHEMAS = {
    "analyze_query": {
        "name": "analyze_query",
        "description": "Analyze a user query about resources",
        "parameters": {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["new_search", "followup"],
                    "description": "Type of the query"
                },
                "needs_availability": {
                    "type": "boolean",
                    "description": "Whether availability check is needed"
                },
                "time_period": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["specific_weeks", "relative"]},
                        "weeks": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 1, "maximum": 52}
                        },
                        "relative_reference": {
                            "type": "string",
                            "enum": ["next_month", "this_month", "next_week", None]
                        },
                        "reasoning": {"type": "string"}
                    },
                    "required": ["type", "weeks", "reasoning"]
                },
                "locations": {
                    "type": "object",
                    "properties": {
                        "mentioned": {"type": "array", "items": {"type": "string"}},
                        "resolved": {"type": "array", "items": {"type": "string"}},
                        "reasoning": {"type": "string"}
                    },
                    "required": ["mentioned", "resolved", "reasoning"]
                },
                "reasoning": {"type": "string"},
                "next_action": {
                    "type": "string",
                    "enum": ["search_resources", "fetch_availability", "use_previous_results"]
                }
            },
            "required": ["query_type", "needs_availability", "time_period", "locations", "reasoning", "next_action"]
        }
    },
    "validate_params": {
        "name": "validate_params",
        "description": "Validate search parameters against database values",
        "parameters": {
            "type": "object",
            "properties": {
                "skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Valid skills from the database"
                },
                "ranks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Valid ranks from the database"
                },
                "validation_notes": {
                    "type": "string",
                    "description": "Notes about parameter validation"
                }
            },
            "required": ["skills", "ranks", "validation_notes"]
        }
    }
}

def get_database_metadata() -> Dict[str, Any]:
    """Get metadata from Firebase."""
    try:
        if not hasattr(get_database_metadata, 'metadata'):
            # Cache metadata
            get_database_metadata.metadata = {
                "locations": [
                    "Manchester", "London", "Oslo", "Stockholm",
                    "Copenhagen", "Belfast", "Bristol"
                ],
                "skills": [
                    "DevOps Engineer", "Data Engineer", "Business Analyst",
                    "Scrum Master", "Frontend Developer", "Backend Developer",
                    "Full Stack Developer", "Agile Coach", "Cloud Engineer",
                    "UX Designer", "Project Manager", "Product Owner",
                    "Python", "Java", "JavaScript", ".NET"
                ],
                "ranks": [
                    "Partner", "Associate Partner", "Consulting Director",
                    "Principal Consultant", "Managing Consultant", "Senior Consultant",
                    "Consultant", "Consultant Analyst", "Analyst"
                ],
                "region_mappings": {
                    "Nordics": ["Oslo", "Stockholm", "Copenhagen"],
                    "UK": ["London", "Manchester", "Belfast", "Bristol"]
                }
            }
        return get_database_metadata.metadata
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        return {}

# Cache entry structure
class CacheEntry:
    def __init__(self, response: str, timestamp: float, ttl: int = 3600):
        self.response = response
        self.timestamp = timestamp
        self.ttl = ttl

    def is_valid(self) -> bool:
        """Check if the cache entry is still valid."""
        return time.time() - self.timestamp < self.ttl

# Node functions for the workflow
def analyze_query(state: AgentState, model: BaseChatModel) -> AgentState:
    """Analyze the query and decide next action."""
    max_retries = 5  # Increased from 3
    base_delay = 1  # Base delay in seconds
    
    def parse_json_response(content: str) -> dict:
        """Parse and validate JSON from LLM response."""
        try:
            # First try to find JSON between triple backticks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            else:
                # If no code blocks, try to find JSON between curly braces
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    content = content[start_idx:end_idx + 1].strip()
            
            # Remove any trailing or leading text
            content = content.strip()
            if not content.startswith('{'):
                raise ValueError("No valid JSON object found in response")
            
            parsed = json.loads(content)
            logger.info(f"Successfully parsed JSON structure with keys: {list(parsed.keys())}")
            return parsed
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.error(f"Raw content: {content}")
            raise
    
    for attempt in range(max_retries):
        try:
            # Update metadata if needed
            if not state.metadata:
                state.metadata = get_database_metadata()

            # Calculate exponential backoff with jitter
            delay = min(300, base_delay * (2 ** attempt))  # Cap at 5 minutes
            jitter = random.uniform(0, 0.1 * delay)  # 10% jitter
            total_delay = delay + jitter

            if attempt > 0:
                logger.info(f"Retry attempt {attempt + 1}/{max_retries} with {total_delay:.2f}s delay")
                time.sleep(total_delay)

            # Analyze query using function calling
            messages = [
                SystemMessage(content="""You are Resource Genie, analyzing queries about resource management.
                Your task is to analyze the query and return a JSON object with the following structure:
                {
                    "query_type": "new_search" or "followup",
                    "needs_availability": boolean,
                    "time_period": {
                        "type": "specific_weeks" or "relative",
                        "weeks": [list of integers 1-52],
                        "reasoning": "explanation"
                    },
                    "locations": {
                        "mentioned": ["list of locations"],
                        "resolved": ["list of actual locations"],
                        "reasoning": "explanation"
                    },
                    "reasoning": "overall analysis",
                    "next_action": "search_resources" or "fetch_availability" or "use_previous_results"
                }
                
                Use ONLY these values:
                - Locations: Manchester, London, Oslo, Stockholm, Copenhagen, Belfast, Bristol
                - Region mappings:
                  * Nordics -> Oslo, Stockholm, Copenhagen
                  * UK -> London, Manchester, Belfast, Bristol"""),
                HumanMessage(content=f"""
                Current date: {datetime.now().strftime("%Y-%m-%d")}
                Current week: {datetime.now().isocalendar()[1]}
                Previous context: {state.current_context}
                Previous results: {len(state.previous_results)} resources
                
                Query: {state.current_message}
                """)
            ]

            logger.info(f"Attempt {attempt + 1}/{max_retries} to analyze query")
            response = model.invoke(messages)
            
            try:
                # First try to get function call
                if hasattr(response, 'additional_kwargs') and 'function_call' in response.additional_kwargs:
                    function_args = json.loads(response.additional_kwargs["function_call"]["arguments"])
                    logger.info("Successfully extracted analysis from function call")
                else:
                    # Try to extract JSON from response content
                    function_args = parse_json_response(response.content)
                    logger.info("Successfully extracted analysis from response content")
                
                analysis = QueryAnalysis.parse_obj(function_args)
                state.analysis = analysis
                logger.info(f"Query analysis: {analysis.dict()}")
                return state
                
            except Exception as e:
                logger.error(f"Failed to parse response: {e}")
                if attempt < max_retries - 1:
                    continue
                state.error = "Failed to analyze query: Could not parse response"
                return state
                
        except Exception as e:
            logger.error(f"Error in analyze_query attempt {attempt + 1}: {str(e)}", exc_info=True)
            if attempt < max_retries - 1:
                continue
            state.error = f"Error in query analysis after {max_retries} attempts: {str(e)}"
            return state

    return state

def validate_search_params(state: AgentState, model: BaseChatModel) -> AgentState:
    """Validate and prepare search parameters."""
    def parse_json_response(content: str) -> dict:
        """Parse and validate JSON from LLM response."""
        try:
            # First try to find JSON between triple backticks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            else:
                # If no code blocks, try to find JSON between curly braces
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    content = content[start_idx:end_idx + 1].strip()
            
            parsed = json.loads(content)
            logger.info(f"Successfully parsed JSON structure with keys: {list(parsed.keys())}")
            return parsed
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.error(f"Raw content: {content}")
            raise

    try:
        if not state.analysis:
            state.error = "No query analysis available"
            return state

        # Get valid parameters from metadata
        valid_params = {
            "locations": state.metadata.get("locations", []),
            "skills": state.metadata.get("skills", []),
            "ranks": state.metadata.get("ranks", [])
        }

        # Use function calling to validate parameters
        messages = [
            SystemMessage(content="""You are a parameter validator for database queries.
            Your task is to extract and validate search parameters that EXACTLY match our database values.
            You must return a JSON object with the following structure:
            {
                "locations": ["list of valid locations"],
                "skills": ["list of valid skills"],
                "ranks": ["list of valid ranks"],
                "validation_notes": "explanation of validation decisions"
            }
            
            IMPORTANT:
            - Only use values from the provided valid parameter lists
            - Invalid values will be ignored
            - Lists can be empty if no valid values found
            - For queries about "Partners", always include "Partner" in ranks
            - Always include validation_notes explaining your decisions"""),
            HumanMessage(content=f"""
            Valid parameters:
            {json.dumps(valid_params, indent=2)}
            
            Query analysis:
            {state.analysis.dict()}
            
            Current message:
            {state.current_message}
            
            Extract and validate the parameters, ensuring they match the database values exactly.
            If the query mentions "Partners", make sure to include "Partner" in the ranks list.
            """)
        ]

        response = model.invoke(messages)
        
        try:
            # First try to get function call
            if hasattr(response, 'additional_kwargs') and 'function_call' in response.additional_kwargs:
                params_dict = json.loads(response.additional_kwargs["function_call"]["arguments"])
                logger.info("Successfully extracted parameters from function call")
            else:
                # Try to extract JSON from response content
                params_dict = parse_json_response(response.content)
                logger.info("Successfully extracted parameters from response content")
            
            # Ensure "Partner" is included if query is about partners
            if "partner" in state.current_message.lower() and "Partner" not in params_dict.get("ranks", []):
                params_dict["ranks"] = ["Partner"]
                params_dict["validation_notes"] = "Added Partner rank based on query context. " + params_dict.get("validation_notes", "")
            
            # Create SearchParams object
            params = SearchParams(
                locations=params_dict.get("locations", []),
                skills=params_dict.get("skills", []),
                ranks=params_dict.get("ranks", []),
                validation_notes=params_dict.get("validation_notes", "")
            )
            
            state.search_params = params
            logger.info(f"Validated parameters: {params.dict()}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to parse validation response: {e}")
            state.error = f"Failed to validate parameters: {str(e)}"
            return state

    except Exception as e:
        state.error = f"Error in parameter validation: {str(e)}"
        return state

def search_resources(state: AgentState, firebase_client: Any) -> AgentState:
    """Search for resources using validated parameters."""
    try:
        if not state.search_params:
            state.error = "No search parameters available"
            return state

        # Execute search with validated parameters
        resources = firebase_client.get_resources(
            locations=state.search_params.locations,
            skills=state.search_params.skills,
            ranks=state.search_params.ranks,
            collection='employees',
            nested_ranks=True
        )

        state.resources = resources
        logger.info(f"Found {len(resources)} resources")
        return state
    except Exception as e:
        state.error = f"Error in resource search: {str(e)}"
        return state

def check_availability(state: AgentState, firebase_client: Any) -> AgentState:
    """Check availability for resources."""
    try:
        # Get filtered results from current context if available
        filtered_results = state.current_context.get('filtered_results', [])
        
        # For follow-up queries, use filtered results from context, then fall back to current resources
        resources_to_check = filtered_results if filtered_results else state.resources
        
        if not resources_to_check:
            state.error = "No resources found to check availability for"
            return state
        
        if not state.analysis or not state.analysis.time_period.weeks:
            state.error = "Missing required data for availability check"
            return state

        logger.info(f"Checking availability for {len(resources_to_check)} resources")

        # Validate employee numbers and weeks
        employee_numbers = [
            str(r.get('employee_number')) 
            for r in resources_to_check 
            if r.get('employee_number') and str(r.get('employee_number')).startswith('EMP')
        ]

        valid_weeks = [
            w for w in state.analysis.time_period.weeks 
            if isinstance(w, int) and 1 <= w <= 52
        ]

        if not valid_weeks:
            logger.warning(f"No valid week numbers found in: {state.analysis.time_period.weeks}")
            state.error = "No valid week numbers provided"
            return state

        if not employee_numbers:
            logger.warning("No valid employee numbers found")
            state.error = "No valid employee numbers found"
            return state

        # Fetch availability data
        availability = firebase_client._fetch_availability_batch(
            employee_numbers=employee_numbers,
            weeks=valid_weeks
        )

        state.availability_data = availability
        state.resources = resources_to_check  # Keep the filtered resources for response
        logger.info(f"Fetched availability for {len(employee_numbers)} employees in weeks {valid_weeks}")
        return state
    except Exception as e:
        state.error = f"Error in availability check: {str(e)}"
        return state

def generate_response(state: AgentState, model: BaseChatModel) -> AgentState:
    """Generate final response based on collected data."""
    try:
        # Prepare context for response generation
        context = {
            "analysis": state.analysis.dict() if state.analysis else None,
            "resources": state.resources,
            "availability": state.availability_data,
            "query": state.current_message
        }

        # Generate response using function calling
        response = model.invoke([
            SystemMessage(content="""You are Resource Genie, providing helpful responses about resources.
            Generate a clear and informative response based on the available data."""),
            HumanMessage(content=f"Context: {json.dumps(context, indent=2)}")
        ])

        state.final_response = response.content
        return state
    except Exception as e:
        state.error = f"Error in response generation: {str(e)}"
        return state

class ReActAgentGraph:
    """
    Implementation of Resource Genie using LangGraph's ReAct agent pattern.
    """
    
    def __init__(
        self,
        model: BaseChatModel,
        firebase_client: Any = None,
        use_cache: bool = True,
        cache_ttl: int = 3600,
        verbose: bool = False
    ):
        self.model = model
        self.firebase_client = firebase_client
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self.verbose = verbose
        
        # Initialize tools
        self.tools = self._create_tools()
        
        # Initialize memory for state persistence
        self.checkpointer = MemorySaver()
        
        # Create ReAct agent
        self.agent = create_react_agent(
            self.model,
            self.tools,
            checkpointer=self.checkpointer
        )
        
        logger.info("ReActAgentGraph initialized with ReAct agent pattern")

    def _create_tools(self) -> List[Tool]:
        """Create the tools for the agent."""
        
        @tool
        def search_resources(query: str) -> str:
            """Search for resources based on a natural language query. The query will be parsed to extract locations, skills, and ranks."""
            try:
                # Get valid parameters from metadata
                metadata = get_database_metadata()
                
                # Extract parameters from query
                params = self.extract_query_parameters(query)
                
                # Validate parameters against metadata
                validated_params = {
                    "locations": [loc for loc in params["locations"] if loc in metadata["locations"]],
                    "skills": [skill for skill in params["skills"] if skill in metadata["skills"]],
                    "ranks": [rank for rank in params["ranks"] if rank in metadata["ranks"]],
                    "collection": "employees",
                    "nested_ranks": True
                }
                
                logger.info(f"Searching with validated parameters: {validated_params}")
                resources = self.firebase_client.get_resources(**validated_params)
                
                return json.dumps({
                    "found": len(resources),
                    "resources": resources,
                    "parameters": validated_params
                })
            except Exception as e:
                return f"Error searching resources: {str(e)}"

        @tool
        def check_availability(employee_numbers: List[str], weeks: List[int]) -> str:
            """Check availability for specific employees in given weeks."""
            try:
                # Validate week numbers
                valid_weeks = [w for w in weeks if isinstance(w, int) and 1 <= w <= 52]
                if not valid_weeks:
                    return "Error: No valid week numbers provided"
                
                # Validate employee numbers
                valid_employees = [
                    emp for emp in employee_numbers 
                    if isinstance(emp, str) and emp.startswith('EMP')
                ]
                if not valid_employees:
                    return "Error: No valid employee numbers provided"
                
                availability = self.firebase_client._fetch_availability_batch(
                    employee_numbers=valid_employees,
                    weeks=valid_weeks
                )
                return json.dumps(availability)
            except Exception as e:
                return f"Error checking availability: {str(e)}"

        return [search_resources, check_availability]

    def process_message(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a message using the ReAct agent."""
        try:
            logger.info(f"Processing message: {message}")
            if not session_id:
                session_id = str(uuid.uuid4())
                logger.info(f"Generated new session ID: {session_id}")

            # Create message for the agent
            messages = [{"role": "user", "content": message}]

            # Invoke agent with thread_id for memory persistence
            logger.info("Invoking ReAct agent")
            final_state = self.agent.invoke(
                {"messages": messages},
                config={"configurable": {"thread_id": session_id}}
            )
            logger.info("Agent execution completed")

            # Extract response from final state
            response = final_state["messages"][-1].content

            return {
                "response": response,
                "state": final_state
            }

        except Exception as e:
            logger.error(f"Critical error in process_message: {str(e)}", exc_info=True)
            return {
                "response": "I apologize, but something went wrong while processing your request. Please try again.",
                "error": str(e)
            }

    def reset(self, session_id: Optional[str] = None) -> None:
        """Reset the agent's state."""
        if session_id:
            # Clear specific session state
            self.checkpointer.delete_state(session_id)
            logger.info(f"Reset session {session_id}")
        else:
            # Clear all session states
            self.checkpointer.clear()
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
                weeks=valid_weeks
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
            # First try to find JSON between triple backticks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            else:
                # If no code blocks, try to find JSON between curly braces
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    content = content[start_idx:end_idx + 1].strip()
            
            # Remove any trailing or leading text
            content = content.strip()
            if not content.startswith('{'):
                raise ValueError("No valid JSON object found in response")
            
            parsed = json.loads(content)
            logger.info(f"Successfully parsed JSON structure with keys: {list(parsed.keys())}")
            return parsed
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.error(f"Raw content: {content}")
            raise 