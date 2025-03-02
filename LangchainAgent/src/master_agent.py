"""
Master Agent module that orchestrates the resource management workflow using LangGraph.
"""

from typing import Dict, Any, List, Annotated, TypedDict, Literal
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool

from .query_translator import QueryTranslator
from .resource_fetcher import ResourceFetcher
from .response_generator import ResponseGenerator

class AgentState(TypedDict):
    """State maintained between nodes in the graph."""
    messages: Annotated[List[BaseMessage], operator.add]
    current_query: Dict[str, Any]
    results: List[Dict[str, Any]]
    session_history: List[Dict[str, Any]]

class MasterAgent:
    """
    Master Agent that orchestrates the resource management workflow using LangGraph.
    Coordinates between QueryTranslator, ResourceFetcher, and ResponseGenerator.
    """
    
    def __init__(
        self,
        query_translator: QueryTranslator,
        resource_fetcher: ResourceFetcher,
        response_generator: ResponseGenerator
    ):
        """
        Initialize the MasterAgent with its component services.
        
        Args:
            query_translator: Service for translating natural language to structured queries
            resource_fetcher: Service for fetching resources from the database
            response_generator: Service for generating human-friendly responses
        """
        self.query_translator = query_translator
        self.resource_fetcher = resource_fetcher
        self.response_generator = response_generator
        self.workflow = self._create_workflow()
        # Add last_query_context to store context between queries
        self.last_query_context = None
        
    def _create_workflow(self):
        """Create the LangGraph workflow that orchestrates the components."""
        
        # Define the tools using the @tool decorator
        @tool
        def translate_query(query: str, history: Dict[str, Any] = None) -> Dict[str, Any]:
            """
            Translate a natural language query into a structured format.
            
            Args:
                query: The user's natural language query
                history: Optional context from previous interactions
                
            Returns:
                A structured query representation
            """
            return self.query_translator.translate(query, context=history)
        
        @tool
        def fetch_resources(structured_query: Dict[str, Any]) -> Dict[str, Any]:
            """
            Fetch resources based on a structured query.
            
            Args:
                structured_query: The structured query to use for fetching
                
            Returns:
                A dictionary containing employees and total_count
            """
            return self.resource_fetcher.fetch_resources(
                locations=structured_query.get('locations'),
                ranks=structured_query.get('ranks'),
                skills=structured_query.get('skills'),
                weeks=structured_query.get('weeks'),
                availability_status=structured_query.get('availability_status'),
                min_hours=structured_query.get('min_hours')
            )
        
        @tool
        def generate_response(
            results: List[Dict[str, Any]], 
            query: Dict[str, Any], 
            original_question: str
        ) -> str:
            """
            Generate a human-friendly response based on query results.
            
            Args:
                results: The resource results to include in the response
                query: The structured query that was used
                original_question: The original user message
                
            Returns:
                A human-friendly response
            """
            return self.response_generator.generate(results, query, original_question)
        
        # Define the tools list
        tools = [translate_query, fetch_resources, generate_response]
        
        # Create the tool execution node
        tool_node = ToolNode(tools)
        
        # Create the workflow graph
        workflow = StateGraph(AgentState)
        
        # Define the agent node (process messages and decide what to do)
        def agent(state: AgentState) -> Dict[str, Any]:
            # Extract the latest user message
            messages = state["messages"]
            latest_msg = next((msg for msg in reversed(messages) if isinstance(msg, HumanMessage)), None)
            
            if not latest_msg:
                return {"messages": [AIMessage(content="No user message found.")]}
            
            # First phase: translate the query if not done yet
            if not state.get("current_query"):
                # Get the history for context if available
                history = state["session_history"][-1] if state["session_history"] else {}
                
                # Call the translate_query tool
                structured_query = translate_query.invoke(
                    {"query": latest_msg.content, "history": history}
                )
                
                # Update state
                state["current_query"] = structured_query
                
                # Signal to fetch resources next
                return state
            
            # Third phase: generate a response if we have results
            elif state.get("results"):
                # Extract the actual list of results from the dictionary if needed
                results_list = state["results"]["employees"] if isinstance(state["results"], dict) and "employees" in state["results"] else state["results"]
                
                # Generate the response
                response = generate_response.invoke(
                    {
                        "results": results_list,
                        "query": state["current_query"],
                        "original_question": latest_msg.content
                    }
                )
                
                # Update session history
                state["session_history"].append({
                    "query": state["current_query"],
                    "results": state["results"],
                    "response": response
                })
                
                # Add the response to messages
                return {"messages": [AIMessage(content=response)]}
            
            # This shouldn't happen but return current state as fallback
            return state
        
        # Define the tools execution node
        def tools_executor(state: AgentState) -> Dict[str, Any]:
            # Second phase: fetch resources using the structured query
            if state.get("current_query") and not state.get("results"):
                results = fetch_resources.invoke(
                    {"structured_query": state["current_query"]}
                )
                state["results"] = results
                return state
            
            # This shouldn't happen but return current state as fallback
            return state
        
        # Add nodes to the graph
        workflow.add_node("agent", agent)
        workflow.add_node("tools", tools_executor)
        
        # Define conditional routing
        def should_continue(state: AgentState) -> Literal["tools", END]:
            # If we have a query but no results, go to tools to fetch resources
            if state.get("current_query") and not state.get("results"):
                return "tools"
            # Otherwise we're done (either no query yet or we have results)
            return END
        
        # Add edges to the graph
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")
        
        # Compile the graph
        return workflow.compile()
    
    def process_message(self, message: str, debug=False):
        """
        Process a user message and generate a response.
        
        Args:
            message: User message to process
            debug: Whether to print debug information
            
        Returns:
            Generated response
        """
        try:
            if debug:
                print(f"\n===== MASTER AGENT: Starting to process message: {message} =====")
            
            # Step 1: Translate the query, using previous context if available
            if debug:
                print("\n----- QUERY TRANSLATOR: Translating query -----")
                if self.last_query_context:
                    print(f"Using previous context: {self.last_query_context}")
            
            query_translation = self.query_translator.translate(message, context=self.last_query_context)
            
            # Store the current translation for future follow-up queries
            self.last_query_context = query_translation
            
            if debug:
                print(f"Translated query result: {query_translation}")
            
            # Step 2: Fetch resources
            if debug:
                print("\n----- RESOURCE FETCHER: Fetching resources -----")
                print(f"Input filters: {query_translation}")
            
            resource_result = self.resource_fetcher.fetch_resources(query_dict=query_translation)
            resources = resource_result.get("employees", [])
            
            if debug:
                print(f"Found {len(resources)} resources")
                for i, res in enumerate(resources[:3] if len(resources) >= 3 else resources):  # Print first 3 for brevity
                    print(f"Resource {i+1}: {res.get('name', 'Unknown')} - {res.get('employee_number', 'No ID')}")
                if len(resources) > 3:
                    print(f"... and {len(resources) - 3} more")
                if "error" in resource_result:
                    print(f"Error in resource fetching: {resource_result.get('error')}")
            
            # Step 3: Generate response
            if debug:
                print("\n----- RESPONSE GENERATOR: Generating response -----")
                print(f"Input: Query='{message}', Resources={len(resources)} items")
            
            response = self.response_generator.generate(
                results=resources,
                query=query_translation,
                original_question=message
            )
            
            if debug:
                print(f"Generated response: {response[:100]}... (truncated)" if response and len(response) > 100 else f"Generated response: {response}")
                print("\n===== MASTER AGENT: Processing complete =====")
            
            return response
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            print(f"ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            return f"I encountered an error: {error_msg}"
    
    def update_plan(self, message: str, response: str):
        """
        Update the NewPlan.md file with the latest interaction.
        
        Args:
            message: The user's query
            response: The system's response
        """
        with open("NewPlan.md", "a") as f:
            f.write(f"\n\n## Latest Interaction\n")
            f.write(f"User Query: {message}\n")
            f.write(f"System Response: {response}\n")
            f.write("---\n")
