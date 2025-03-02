"""
Query Tools for LangGraph

This module contains tools for transforming natural language queries into structured queries
and generating human-readable responses from query results.
"""

from typing import Dict, List, Optional, Any, Union, Callable, Type
from langchain_core.tools import BaseTool, StructuredTool, Tool
import json
import re
from pydantic import BaseModel, Field

# Define input schemas for our tools
class TranslateQueryInput(BaseModel):
    query: str = Field(..., description="Natural language query from the user")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context from previous queries")

class GenerateResponseInput(BaseModel):
    results: List[Dict[str, Any]] = Field(..., description="List of resource objects matching the query")
    query: Dict[str, Any] = Field(..., description="The structured query that produced these results")
    original_question: str = Field(..., description="The original natural language question")

class QueryTools:
    """
    Tools for transforming natural language queries and generating responses.
    """

    def __init__(self, model):
        """
        Initialize the QueryTools.

        Args:
            model: LLM model for query transformation and response generation
        """
        self.model = model
        self.last_context = None

        # Create tool objects using simpler Tool approach
        self.translate_query = Tool(
            name="translate_query",
            description="Translate a natural language query into a structured query format.",
            func=self._translate_query_impl
        )
        
        self.generate_response = Tool(
            name="generate_response",
            description="Generate a human-readable response based on query results.",
            func=self._generate_response_impl
        )

    def _translate_query_impl(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Implementation of translate_query tool.
        """
        prompt = self._create_query_translation_prompt(query, context)
        
        try:
            # Call the model to translate the query
            response = self.model.invoke(prompt)
            
            # Parse the structured query from the model response
            structured_query = self._parse_translation_response(response.content)
            
            # Store context for future follow-up queries
            self.last_context = {
                "query": query,
                "structured_query": structured_query
            }
            
            return structured_query
        except Exception as e:
            print(f"Error translating query: {e}")
            return {
                "error": f"Failed to translate query: {e}",
                "locations": [],
                "ranks": [],
                "skills": [],
                "weeks": [],
                "availability_status": []
            }
    
    def _generate_response_impl(
        self, 
        results: List[Dict[str, Any]], 
        query: Dict[str, Any], 
        original_question: str
    ) -> str:
        """
        Implementation of generate_response tool.
        """
        # Create a prompt for generating the response
        prompt = self._create_response_generation_prompt(
            results=results,
            query=query,
            original_question=original_question
        )
        
        try:
            # Call the model to generate the response
            response = self.model.invoke(prompt)
            
            # Return the generated response
            return response.content
        except Exception as e:
            print(f"Error generating response: {e}")
            
            # Fallback to a simple response
            if results and len(results) > 0:
                return f"I found {len(results)} resources matching your query. The first result is {results[0]['name']}."
            else:
                return "I couldn't find any resources matching your query."
    
    def _create_query_translation_prompt(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a prompt for translating a natural language query into a structured query.
        
        Args:
            query: Natural language query
            context: Optional context from previous queries
            
        Returns:
            Formatted prompt string
        """
        context_str = ""
        if context:
            context_str = f"\nPrevious query context: {json.dumps(context, indent=2)}"
            
        system_prompt = """You are an AI assistant tasked with translating natural language queries about resources (employees) into structured queries.

The structured query should include:
- locations: List of locations mentioned (e.g., ["London", "Manchester"])
- ranks: List of ranks mentioned (e.g., ["Consultant", "Senior Consultant"])
- skills: List of skills mentioned (e.g., ["Frontend Developer", "Python"])
- weeks: List of week numbers mentioned for availability checks (e.g., [1, 2, 3])
- availability_status: List of availability statuses mentioned (e.g., ["Available", "Partial"])
- min_hours: Minimum hours of availability if mentioned

The rank hierarchy (from highest to lowest) is:
- Partner
- Associate Partner / Consulting Director (same level)
- Management Consultant
- Principal Consultant
- Senior Consultant
- Consultant
- Analyst

If the query mentions "rank above X" or similar, include all ranks above X in the hierarchy.
If the query is a follow-up question, use the context from previous queries.

Respond ONLY with the JSON structure, no other text."""

        user_prompt = f"Translate this query into a structured format:{context_str}\n\nQuery: {query}"
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def _parse_translation_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the model's response to extract the structured query.
        
        Args:
            response_text: Text response from the model
            
        Returns:
            Structured query dictionary
        """
        # Extract JSON from response if it's embedded in text
        pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        match = re.search(pattern, response_text)
        
        if match:
            json_str = match.group(1)
        else:
            json_str = response_text
        
        try:
            query_dict = json.loads(json_str)
            
            # Ensure all expected keys exist
            for key in ["locations", "ranks", "skills", "weeks", "availability_status"]:
                if key not in query_dict:
                    query_dict[key] = []
            
            return query_dict
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from response: {response_text}")
            return {
                "locations": [],
                "ranks": [],
                "skills": [],
                "weeks": [],
                "availability_status": [],
                "error": "Failed to parse response"
            }
    
    def _create_response_generation_prompt(
        self, 
        results: List[Dict[str, Any]], 
        query: Dict[str, Any], 
        original_question: str
    ) -> str:
        """
        Create a prompt for generating a human-readable response from query results.
        
        Args:
            results: List of resource objects matching the query
            query: The structured query that produced these results
            original_question: The original natural language question
            
        Returns:
            Formatted prompt string
        """
        results_str = json.dumps(results, indent=2)
        query_str = json.dumps(query, indent=2)
        
        system_prompt = """You are an AI assistant helping with resource management.
Your task is to generate a helpful, concise response to a user's query about resources (employees).
You'll be given the original query, the structured interpretation of that query, and the matching results.

Format your response in a friendly, helpful way. Be concise but informative.
If there are no results, explain why this might be and suggest alternatives.
If there are results, summarize them clearly, mentioning key details like names, ranks, locations, and availability."""

        user_prompt = f"""Original question: {original_question}

Structured query:
{query_str}

Results ({len(results)} found):
{results_str}

Generate a helpful response to the original question based on these results."""
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ] 