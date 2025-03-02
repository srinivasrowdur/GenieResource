"""
Tests for the QueryTools implementation.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import json

# Add parent directory to path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.tools.query_tools import QueryTools

class TestQueryTools(unittest.TestCase):
    """Test cases for the QueryTools class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock model
        self.mock_model = MagicMock()
        
        # Set up mock response for translate_query
        translate_response = MagicMock()
        translate_response.content = json.dumps({
            "locations": ["London"],
            "ranks": ["Senior Consultant"],
            "skills": ["Python"],
            "weeks": [1, 2],
            "availability_status": ["Available"]
        })
        
        # Set up mock response for generate_response
        generate_response = MagicMock()
        generate_response.content = "I found 2 Python developers in London."
        
        # Configure the mock model to return different responses based on prompt content
        def mock_invoke(prompt):
            if isinstance(prompt, list) and len(prompt) >= 2:
                if "Translate this query" in prompt[1]["content"]:
                    return translate_response
                elif "Generate a helpful response" in prompt[1]["content"]:
                    return generate_response
            return MagicMock(content="Default mock response")
            
        self.mock_model.invoke = mock_invoke
        
        # Create QueryTools instance with mock model
        self.query_tools = QueryTools(model=self.mock_model)
    
    def test_translate_query_success(self):
        """Test successful query translation."""
        # Call the method under test
        result = self.query_tools._translate_query_impl(query="Find Python developers in London")
        
        # Check the result
        self.assertEqual(result["locations"], ["London"])
        self.assertEqual(result["ranks"], ["Senior Consultant"])
        self.assertEqual(result["skills"], ["Python"])
        self.assertEqual(result["weeks"], [1, 2])
        self.assertEqual(result["availability_status"], ["Available"])
        
        # Check that last_context was set
        self.assertIsNotNone(self.query_tools.last_context)
        self.assertEqual(self.query_tools.last_context["query"], "Find Python developers in London")
    
    def test_translate_query_with_context(self):
        """Test query translation with context."""
        # Set up test context
        context = {
            "query": "Find Python developers",
            "structured_query": {
                "locations": [],
                "ranks": [],
                "skills": ["Python"],
                "weeks": [],
                "availability_status": []
            }
        }
        
        # Call the method under test
        self.query_tools._translate_query_impl(
            query="Are there any in London?",
            context=context
        )
        
        # Check that model was called with context included
        for call in self.mock_model.mock_calls:
            name, args, kwargs = call
            if args and isinstance(args[0], list) and len(args[0]) >= 2:
                if "Previous query context" in args[0][1]["content"]:
                    # Test passes if context was included in the prompt
                    break
        else:
            self.fail("Context was not included in the prompt")
    
    def test_translate_query_error(self):
        """Test query translation when model raises an exception."""
        # Set up mock to raise an exception
        self.mock_model.invoke = MagicMock(side_effect=Exception("Test error"))
        
        # Call the method under test
        result = self.query_tools._translate_query_impl(query="This should fail")
        
        # Check the result
        self.assertIn("error", result)
        self.assertEqual(result["locations"], [])
        self.assertEqual(result["ranks"], [])
        self.assertEqual(result["skills"], [])
    
    def test_generate_response_success(self):
        """Test successful response generation."""
        # Set up test data
        results = [
            {"name": "John Doe", "location": "London", "skills": ["Python", "Java"]},
            {"name": "Jane Smith", "location": "London", "skills": ["Python", "React"]}
        ]
        query = {"locations": ["London"], "skills": ["Python"]}
        original_question = "Find Python developers in London"
        
        # Call the method under test
        result = self.query_tools._generate_response_impl(
            results=results,
            query=query,
            original_question=original_question
        )
        
        # Check the result
        self.assertEqual(result, "I found 2 Python developers in London.")
    
    def test_generate_response_error(self):
        """Test response generation when model raises an exception."""
        # Set up mock to raise an exception
        self.mock_model.invoke = MagicMock(side_effect=Exception("Test error"))
        
        # Set up test data
        results = [
            {"name": "John Doe", "location": "London", "skills": ["Python", "Java"]},
            {"name": "Jane Smith", "location": "London", "skills": ["Python", "React"]}
        ]
        query = {"locations": ["London"], "skills": ["Python"]}
        original_question = "Find Python developers in London"
        
        # Call the method under test
        result = self.query_tools._generate_response_impl(
            results=results,
            query=query,
            original_question=original_question
        )
        
        # Check that a fallback response was generated
        self.assertIn("I found 2 resources", result)
    
    def test_generate_response_empty_results(self):
        """Test response generation with empty results."""
        # Set up mock to raise an exception
        self.mock_model.invoke = MagicMock(side_effect=Exception("Test error"))
        
        # Call the method under test with empty results
        result = self.query_tools._generate_response_impl(
            results=[],
            query={},
            original_question="Find something that doesn't exist"
        )
        
        # Check that an appropriate response was generated
        self.assertEqual(result, "I couldn't find any resources matching your query.")
    
    def test_parse_translation_response_clean_json(self):
        """Test parsing a clean JSON response."""
        # Set up clean JSON response
        response_text = '{"locations": ["London"], "skills": ["Python"]}'
        
        # Call the method
        result = self.query_tools._parse_translation_response(response_text)
        
        # Check result
        self.assertEqual(result["locations"], ["London"])
        self.assertEqual(result["skills"], ["Python"])
        
        # Check that missing keys are added with empty lists
        self.assertEqual(result["weeks"], [])
        self.assertEqual(result["ranks"], [])
        self.assertEqual(result["availability_status"], [])
    
    def test_parse_translation_response_code_block(self):
        """Test parsing a response with code blocks."""
        # Set up response with code blocks
        response_text = """
Here's the structured query:

```json
{
  "locations": ["London"], 
  "skills": ["Python"]
}
```
"""
        
        # Call the method
        result = self.query_tools._parse_translation_response(response_text)
        
        # Check result
        self.assertEqual(result["locations"], ["London"])
        self.assertEqual(result["skills"], ["Python"])
    
    def test_parse_translation_response_invalid_json(self):
        """Test parsing an invalid JSON response."""
        # Set up invalid JSON response
        response_text = "This is not a valid JSON response."
        
        # Call the method
        result = self.query_tools._parse_translation_response(response_text)
        
        # Check result contains error and empty data
        self.assertIn("error", result)
        self.assertEqual(result["locations"], [])
        self.assertEqual(result["skills"], [])

if __name__ == "__main__":
    unittest.main() 