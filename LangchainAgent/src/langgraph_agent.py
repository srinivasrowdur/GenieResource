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
        
        logger.info("ReActAgentGraph initialized successfully")

    def process_message(self, message: str, session_id: Optional[str] = None) -> AgentResponse:
        """
        Process a message using a simple chat model approach.
        
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
            
            # Step 2: Query the database if available
            resources = []
            firebase_connected = False
            
            if self.firebase_client and (self.firebase_client.is_connected or self.firebase_client.is_demo_mode):
                firebase_connected = True
                try:
                    # Check for demo mode
                    if self.firebase_client.is_demo_mode:
                        logger.info(f"Using demo mode for resources")
                        resources = self.firebase_client._get_sample_resources(
                            locations=query_params.get("locations", []),
                            skills=query_params.get("skills", []),
                            ranks=query_params.get("ranks", [])
                        )
                    else:
                        # Get the query parameters
                        locations = query_params.get("locations", [])
                        skills = query_params.get("skills", [])
                        ranks = query_params.get("ranks", [])
                        
                        # For the real database, we know it's using 'employees' collection with 100 records
                        collection_name = 'employees'
                        logger.info(f"Using '{collection_name}' collection from real database")
                        
                        # Log the search criteria
                        logger.info(f"Searching for: locations={locations}, skills={skills}, ranks={ranks}")
                        
                        # Add debugging for rank structure (we know ranks are nested objects)
                        logger.info("✓ Note: Ranks in this database are nested objects with 'official_name' field")
                        logger.info("✓ Looking for ranks with official_name matching: " + ", ".join(ranks))
                        
                        # Use the standard get_resources method but specify the collection and nested_ranks=True
                        resources = self.firebase_client.get_resources(
                            locations=locations,
                            skills=skills,
                            ranks=ranks,
                            collection='employees',  # Explicitly use employees collection
                            nested_ranks=True  # Tell the method to look for nested rank structure
                        )
                    
                    logger.info(f"Found {len(resources)} resources in database/demo")
                    
                    # Log the resources for debugging
                    if resources:
                        for i, resource in enumerate(resources[:3]):  # Log up to 3 resources to avoid clutter
                            logger.info(f"Resource {i+1}: {resource.get('name', 'Unknown')} - {resource.get('rank', 'Unknown')} in {resource.get('location', 'Unknown')}")
                        if len(resources) > 3:
                            logger.info(f"...and {len(resources) - 3} more resources")
                except Exception as e:
                    logger.error(f"Error querying resources: {e}")
                    resources = []
            
            # Get conversation history
            history = self._sessions.get(session_id, [])
            
            # Step 3: Generate response based on the query results
            response_prompt = f"""You are Resource Genie, an AI assistant that helps users find resources based on their needs.
            
            The user is looking for resources with the following parameters:
            - Locations: {', '.join(query_params.get('locations', [])) or 'Not specified'}
            - Skills: {', '.join(query_params.get('skills', [])) or 'Not specified'}
            - Ranks: {', '.join(query_params.get('ranks', [])) or 'Not specified'}
            
            {"I found the following matching resources:" if resources else "I couldn't find any resources matching those criteria."}
            """
            
            # Add resources to the prompt if any were found
            if resources:
                resource_details = []
                for i, resource in enumerate(resources[:10]):  # Limit to 10 resources to avoid huge prompts
                    details = f"""
                    Resource {i+1}:
                    Name: {resource.get('name', 'Unknown')}
                    Location: {resource.get('location', 'Unknown')}
                    Rank: {resource.get('rank', 'Unknown')}
                    Skills: {', '.join(resource.get('skills', []))}
                    Availability: {resource.get('availability', 'Unknown')}
                    """
                    resource_details.append(details)
                
                response_prompt += "\n\n" + "\n".join(resource_details)
                
                if len(resources) > 10:
                    response_prompt += f"\n\nAnd {len(resources) - 10} more resources not shown."
            
            response_prompt += """
            
            Respond in a helpful, conversational way to the user's query. Focus on the resources that match their criteria.
            If no resources match, suggest broadening their search criteria.
            """
            
            # Prepare messages for the model
            messages = [
                SystemMessage(content=response_prompt),
            ]
            
            # Add the new message
            messages.append(HumanMessage(content=message))
            
            # Call the model
            response = self.model.invoke(messages)
            
            # Extract response text
            response_text = response.content
            
            # Update session history
            new_history = history.copy()
            new_history.append(HumanMessage(content=message))
            new_history.append(AIMessage(content=response_text))
            
            # Keep only the last 10 messages to avoid context overflow
            if len(new_history) > 10:
                new_history = new_history[-10:]
                
            # Save updated history
            self._sessions[session_id] = new_history
            
            # Step 4: Save query data if Firebase is available
            if firebase_connected:
                try:
                    # Create metadata from extracted parameters
                    metadata = {
                        "timestamp": datetime.now().isoformat(),
                        "query_length": len(message),
                        "response_length": len(response_text),
                        "locations": query_params.get("locations", []),
                        "skills": query_params.get("skills", []),
                        "ranks": query_params.get("ranks", [])
                    }
                    
                    # Save query data
                    query_id = self.firebase_client.save_query_data(
                        query=message,
                        response=response_text,
                        metadata=metadata,
                        session_id=session_id
                    )
                    
                    if query_id:
                        logger.info(f"✅ Query data saved to Firestore with ID: {query_id}")
                
                except Exception as e:
                    logger.error(f"Error saving query data: {e}")
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Cache the response if caching is enabled
            if self.use_cache:
                cache_key = self._generate_cache_key(message)
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