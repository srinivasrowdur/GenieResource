"""
Response Generator module for creating human-friendly responses about employee availability.
"""

from typing import Dict, Any, List
import anthropic

class ResponseGenerator:
    """
    Generates human-friendly responses about employee availability using an LLM.
    Acts as a resource manager helping to find the right employees.
    """
    
    def __init__(self, anthropic_api_key: str):
        """
        Initialize the ResponseGenerator.
        
        Args:
            anthropic_api_key: API key for Anthropic's Claude
        """
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
    
    def generate(self, results: List[Dict[str, Any]], query: Dict[str, Any], original_question: str) -> str:
        """
        Generate a human-friendly response based on the query results.
        
        Args:
            results: List of matching employees with their details
            query: Dictionary containing the structured query parameters
            original_question: The original natural language question asked by the user
            
        Returns:
            A human-friendly response string
        """
        # Prepare the system prompt
        system_prompt = """You are a helpful resource manager assistant who helps find and suggest the right employees for projects.
Your task is to analyze the search results and original question, then provide a clear, human-friendly response that:
1. Summarizes what was found (or not found)
2. Provides relevant details about each employee
3. Highlights availability if specified
4. Makes helpful suggestions when appropriate
5. Suggests relevant follow-up questions

Remember to:
- Be professional but conversational
- Focus on the most relevant information
- Group similar employees together
- Highlight key skills and experience
- Note any availability constraints
- Suggest alternatives or broader searches if no exact matches
- Propose logical follow-up questions based on the context

Format the response in a clear, readable way using sections and bullet points where appropriate."""

        # Prepare the context about the query and results
        query_context = self._format_query_context(query)
        results_context = self._format_results_context(results)
        
        # Prepare the message for the LLM
        messages = [
            {
                "role": "user",
                "content": f"""Original question: {original_question}

Query details:
{query_context}

Search results:
{results_context}

Please provide a helpful response that addresses the original question and provides relevant suggestions."""
            }
        ]
        
        # Get response from Claude
        response = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            system=system_prompt,
            messages=messages
        )
        
        return response.content[0].text
    
    def _format_query_context(self, query: Dict[str, Any]) -> str:
        """Format the query parameters into a readable string."""
        context_parts = []
        
        if query.get('locations'):
            context_parts.append(f"Locations: {', '.join(query['locations'])}")
        
        if query.get('skills'):
            context_parts.append(f"Skills: {', '.join(query['skills'])}")
        
        if query.get('ranks'):
            context_parts.append(f"Ranks: {', '.join(query['ranks'])}")
        
        if query.get('weeks'):
            context_parts.append(f"Weeks: {', '.join(map(str, query['weeks']))}")
        
        if query.get('availability_status'):
            context_parts.append(f"Availability status: {', '.join(query['availability_status'])}")
        
        if query.get('min_hours') is not None:
            context_parts.append(f"Minimum hours: {query['min_hours']}")
        
        return "\n".join(context_parts) if context_parts else "No specific filters applied"
    
    def _format_results_context(self, results: List[Dict[str, Any]]) -> str:
        """Format the search results into a readable string."""
        if not results:
            return "No matching employees found"
        
        context_parts = [f"Found {len(results)} matching employee(s):"]
        
        for result in results:
            employee_details = [
                f"\nEmployee: {result.get('name', 'Unknown')}",
                f"Employee Number: {result.get('employee_number', 'Unknown')}",
                f"Location: {result.get('location', 'Unknown')}",
                f"Rank: {result.get('rank', {}).get('official_name', 'Unknown')}",
                f"Skills: {', '.join(result.get('skills', []))}"
            ]
            
            # Add availability information if present
            if 'availability' in result and result['availability']:
                avail_info = []
                for week in result['availability']:
                    avail_info.append(
                        f"Week {week.get('week_number', week.get('week', 'Unknown'))}: {week.get('status', 'Unknown')} "
                        f"({week.get('hours', 0)} hours)"
                    )
                    if week.get('notes'):
                        avail_info[-1] += f" - Note: {week.get('notes')}"
                
                if avail_info:
                    employee_details.append("Availability:\n" + "\n".join(avail_info))
            
            context_parts.append("\n".join(employee_details))
        
        return "\n".join(context_parts)
