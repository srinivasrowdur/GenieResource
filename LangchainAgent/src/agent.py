"""
LangGraph Agent Module

This module implements the Resource Genie agent using LangGraph's ReAct agent architecture.
It connects the tools with the model to create a conversational agent.
"""

from typing import Dict, List, Any, Optional
import hashlib
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.agents import AgentExecutor
import uuid
import time

from .tools.resource_tools import ResourceTools
from .tools.query_tools import QueryTools
from .firebase_utils import FirebaseClient

class ReActAgent:
    """
    Resource Genie agent implemented using LangGraph's ReAct architecture.
    This agent handles the complete workflow from natural language query to response generation.
    """
    
    def __init__(self, model, firebase_client: FirebaseClient = None, use_cache: bool = True, cache_ttl: int = 3600):
        """
        Initialize the ReAct agent with required components.
        
        Args:
            model: The LLM model (Claude, GPT, etc.) to use for reasoning
            firebase_client: Optional Firebase client for resource access
            use_cache: Whether to use caching for query responses
            cache_ttl: Time-to-live for cached results in seconds (default: 1 hour)
        """
        self.model = model
        self.firebase_client = firebase_client
        self.resource_tools = ResourceTools(firebase_client) if firebase_client else None
        self.query_tools = QueryTools(model)
        self.thread_id = str(uuid.uuid4())  # Generate a default thread ID
        self.session_history = []
        self.agent = self._setup_agent()
        
        # Caching configuration
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self.response_cache = {}  # {query_hash: {"response": response, "timestamp": timestamp}}
        self.cache_hits = 0
        self.cache_misses = 0
        
    def _setup_agent(self):
        """
        Set up the agent with all necessary tools.
        
        Returns:
            Configured agent
        """
        tools = []
        
        # Add query translation and response generation tools
        tools.append(self.query_tools.translate_query)
        tools.append(self.query_tools.generate_response)
        
        # Add resource tools if Firebase client is available
        if self.resource_tools:
            tools.append(self.resource_tools.query_resources)
            tools.append(self.resource_tools.get_resource_metadata)
            tools.append(self.resource_tools.save_query)
        
        # Create a prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are Resource Genie, an AI assistant that helps users find and manage resources (employees).
You can translate natural language queries into structured queries, fetch matching resources, and generate helpful responses.
Use the available tools to help the user find the information they need.

When processing a resource query, ALWAYS follow these steps in order:
1. Use the translate_query tool to convert the natural language query into a structured format.
2. Use the query_resources tool with the structured parameters to retrieve matching resources.
3. Use the generate_response tool to create a human-friendly response from the results.
4. Use the save_query tool to store the query data for analytics.

Always be helpful, concise, and informative. If you're unsure about any parameters, make reasonable assumptions based on the query."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Bind the tools to the model
        llm_with_tools = self.model.bind_tools(tools)
        
        # Create the agent
        agent = (
            {
                "input": lambda x: x["input"],
                "chat_history": lambda x: x.get("chat_history", []),
                "agent_scratchpad": lambda x: format_to_openai_function_messages(
                    x.get("intermediate_steps", [])
                ),
            }
            | prompt
            | llm_with_tools
            | OpenAIFunctionsAgentOutputParser()
        )
        
        # Create the agent executor with a higher max iterations to ensure completion
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,  # Increase max iterations to ensure completion
            early_stopping_method="generate"  # Use force generation if stuck
        )
        
        return agent_executor
    
    def _hash_query(self, message: str, session_history: List) -> str:
        """
        Create a hash of the query and relevant context for cache key.
        
        Args:
            message: The user's message
            session_history: The conversation history
            
        Returns:
            String hash to use as cache key
        """
        # Create a string representation of the last 2 messages (if they exist)
        # This provides context without making the cache key too specific
        context = ""
        if session_history and len(session_history) >= 2:
            context = str(session_history[-2].content) + str(session_history[-1].content)
        
        # Create a hash of the message and context
        hash_input = (message + context).encode('utf-8')
        return hashlib.md5(hash_input).hexdigest()
    
    def _check_cache(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """
        Check if the query result is in cache and not expired.
        
        Args:
            query_hash: The hash of the query to check
            
        Returns:
            Cached response or None if not found or expired
        """
        if not self.use_cache or query_hash not in self.response_cache:
            return None
        
        cached_item = self.response_cache[query_hash]
        current_time = time.time()
        
        # Check if the cache item has expired
        if current_time - cached_item["timestamp"] > self.cache_ttl:
            # Remove expired item
            del self.response_cache[query_hash]
            return None
        
        return cached_item["response"]
    
    def _update_cache(self, query_hash: str, response: Dict[str, Any]):
        """
        Update the cache with a new response.
        
        Args:
            query_hash: The hash to use as the key
            response: The response to cache
        """
        if self.use_cache:
            self.response_cache[query_hash] = {
                "response": response,
                "timestamp": time.time()
            }
            
            # Simple cache size management - keep only the last 100 responses
            if len(self.response_cache) > 100:
                # Remove the oldest entry (first one in dictionary)
                oldest_key = next(iter(self.response_cache))
                del self.response_cache[oldest_key]
    
    def process_message(self, message: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        Args:
            message: The user's message
            session_id: Optional session ID for state management
            
        Returns:
            Dictionary with response and additional metadata
        """
        # Use provided session_id or the default thread_id
        if session_id:
            self.thread_id = session_id
            
        # Check cache first if enabled
        if self.use_cache:
            query_hash = self._hash_query(message, self.session_history)
            cached_response = self._check_cache(query_hash)
            
            if cached_response:
                self.cache_hits += 1
                print(f"Cache hit! Using cached response for query: {message}")
                
                # Still add to history for context
                self.session_history.append(HumanMessage(content=message))
                self.session_history.append(AIMessage(content=cached_response["response"]))
                
                # Keep history at a reasonable length
                if len(self.session_history) > 10:
                    self.session_history = self.session_history[-10:]
                
                # Return cached response with cache metadata
                return {
                    **cached_response,
                    "cached": True,
                    "cache_stats": {
                        "hits": self.cache_hits,
                        "misses": self.cache_misses
                    }
                }
            else:
                self.cache_misses += 1
        
        try:
            # Measure execution time for performance tracking
            start_time = time.time()
            
            # Enable verbose mode to see the full chain of reasoning
            self.agent.verbose = True
            
            # Invoke the agent with tracing enabled
            result = self.agent.invoke({
                "input": message,
                "chat_history": self.session_history
            })
            
            execution_time = time.time() - start_time
            
            # Print full intermediate steps for debugging
            print(f"Full agent result: {result}")
            if "intermediate_steps" in result:
                print(f"Intermediate steps: {result['intermediate_steps']}")
            
            # Extract the response
            response = result["output"]
            
            # If the response is not a string but a structured output with 'text' and 'tool_use' keys,
            # extract just the text content for the user
            if isinstance(response, list):
                # This means we're getting the internal format of the agent's reasoning process
                print(f"Structured response detected: {response}")
                
                # Look for the final response in the intermediate steps
                if "intermediate_steps" in result and result["intermediate_steps"]:
                    # Get the last observation from intermediate steps
                    last_step = result["intermediate_steps"][-1]
                    if len(last_step) > 1 and last_step[1]:  # Check if we have an observation
                        # Use the last observation as it's likely the final response
                        print(f"Using final observation as response: {last_step[1]}")
                        if isinstance(last_step[1], str):
                            response = last_step[1]
                        elif isinstance(last_step[1], dict) and "results" in last_step[1]:
                            # If it's the result of query_resources, generate a response
                            try:
                                results = last_step[1]["results"]
                                query = last_step[1]["query"]
                                response = self.query_tools.generate_response.run(
                                    results=results,
                                    query=query,
                                    original_question=message
                                )
                                print(f"Generated response from results: {response}")
                            except Exception as e:
                                print(f"Error generating response from results: {e}")
                
                # Extract all text parts if we still have a list
                if isinstance(response, list):
                    text_parts = [item['text'] for item in response if isinstance(item, dict) and 'text' in item]
                    if text_parts:
                        response = " ".join(text_parts)
                    else:
                        # Fallback if no text parts found
                        response = "I've processed your request, but I'm having trouble formatting the response. Please try again with more specific details."
            
            # If response appears incomplete (just contains the initial acknowledgment)
            if "I'll help you" in response and "Let me do that for you" in response and "find" in message.lower():
                # This looks like just the initial acknowledgment
                location = None
                
                # Try to extract location from the message
                if "manchester" in message.lower():
                    location = "Manchester"
                elif "london" in message.lower():
                    location = "London"
                elif "edinburgh" in message.lower():
                    location = "Edinburgh"
                
                if location:
                    # Complete the query manually
                    print(f"Response appears incomplete, completing query for {location}")
                    
                    # Query resources directly
                    resource_results = None
                    if self.resource_tools:
                        resource_results = self.resource_tools.query_resources.run(
                            locations=[location]
                        )
                        
                        # Generate a response with the resource results
                        if resource_results and "results" in resource_results:
                            results = resource_results["results"]
                            query = {"locations": [location]}
                            
                            try:
                                completion = self.query_tools.generate_response.run(
                                    results=results,
                                    query=query,
                                    original_question=message
                                )
                                
                                # Append the completion to the acknowledgment
                                response = f"{response}\n\n{completion}"
                                print(f"Completed response: {response}")
                            except Exception as e:
                                print(f"Error completing response: {e}")
            
            # Add messages to history
            self.session_history.append(HumanMessage(content=message))
            self.session_history.append(AIMessage(content=response))
            
            # Keep history at a reasonable length
            if len(self.session_history) > 10:
                self.session_history = self.session_history[-10:]
            
            # Create response object
            response_obj = {
                "response": response,
                "success": True,
                "execution_time": execution_time,
                "cached": False,
                "cache_stats": {
                    "hits": self.cache_hits,
                    "misses": self.cache_misses
                }
            }
            
            # Cache the successful response if enabled
            if self.use_cache:
                query_hash = self._hash_query(message, self.session_history[:-2])  # Exclude the just-added messages
                self._update_cache(query_hash, response_obj)
            
            return response_obj
        except Exception as e:
            print(f"Error processing message: {e}")
            return {
                "response": f"I encountered an error: {str(e)}",
                "success": False,
                "error": str(e),
                "cached": False,
                "cache_stats": {
                    "hits": self.cache_hits,
                    "misses": self.cache_misses
                }
            }
    
    def reset(self):
        """
        Reset the agent's state.
        """
        self.session_history = []
        # Reset the query tools' context
        self.query_tools.last_context = None
        # Reset the resource tools' cache
        if self.resource_tools:
            self.resource_tools.cached_results = None
            self.resource_tools.last_query = None
        # Generate a new thread ID
        self.thread_id = str(uuid.uuid4())

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_queries = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_queries if total_queries > 0 else 0
        
        return {
            "enabled": self.use_cache,
            "ttl_seconds": self.cache_ttl,
            "size": len(self.response_cache),
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "total_queries": total_queries,
            "hit_rate": hit_rate
        }
    
    def clear_cache(self):
        """
        Clear the response cache.
        """
        self.response_cache = {}
        print("Response cache cleared") 