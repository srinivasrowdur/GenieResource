"""
Integration tests for the Resource Management Agent workflow.
"""

import unittest
from unittest.mock import Mock, patch
import os
from typing import Dict, Any, List

from ..src.master_agent import MasterAgent
from ..src.query_translator import QueryTranslator
from ..src.resource_fetcher import ResourceFetcher
from ..src.response_generator import ResponseGenerator

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""
    
    def setUp(self):
        """Set up test components with mocked dependencies."""
        # Mock Firebase client
        self.firebase_mock = Mock()
        
        # Sample employee data
        self.sample_employees = [
            {
                "name": "John Doe",
                "location": "London",
                "rank": {"official_name": "Senior Consultant"},
                "skills": ["python", "machine learning"],
                "availability": [
                    {"week": 1, "status": "available", "hours": 40},
                    {"week": 2, "status": "partial", "hours": 20}
                ]
            },
            {
                "name": "Jane Smith",
                "location": "Copenhagen",
                "rank": {"official_name": "Consultant"},
                "skills": ["frontend", "react"],
                "availability": [
                    {"week": 1, "status": "unavailable", "hours": 0},
                    {"week": 2, "status": "available", "hours": 40}
                ]
            }
        ]
        
        # Initialize components
        self.query_translator = QueryTranslator(os.getenv("ANTHROPIC_API_KEY", "dummy_key"))
        self.resource_fetcher = ResourceFetcher(self.firebase_mock)
        self.response_generator = ResponseGenerator(os.getenv("ANTHROPIC_API_KEY", "dummy_key"))
        
        # Create master agent
        self.agent = MasterAgent(
            self.query_translator,
            self.resource_fetcher,
            self.response_generator
        )
        
        # Mock Firebase query responses
        self.firebase_mock.collection().where().get.return_value = self.sample_employees
    
    def test_end_to_end_resource_query(self):
        """Test complete workflow for a basic resource query."""
        query = "Find frontend developers in Copenhagen"
        response = self.agent.process_message(query)
        
        # Verify response contains relevant information
        self.assertIn("Jane Smith", response)
        self.assertIn("Copenhagen", response)
        self.assertIn("frontend", response)
    
    def test_end_to_end_availability_query(self):
        """Test complete workflow for an availability query."""
        query = "Who is available in London next week?"
        response = self.agent.process_message(query)
        
        # Verify response includes availability information
        self.assertIn("John Doe", response)
        self.assertIn("available", response)
        self.assertIn("40 hours", response)
    
    def test_end_to_end_followup_query(self):
        """Test complete workflow with follow-up queries."""
        # Initial query
        first_query = "Find developers in London"
        first_response = self.agent.process_message(first_query)
        self.assertIn("John Doe", first_response)
        
        # Follow-up query
        followup_query = "What is their availability?"
        followup_response = self.agent.process_message(followup_query)
        self.assertIn("available", followup_response)
        self.assertIn("40 hours", followup_response)
    
    def test_workflow_state_management(self):
        """Test that workflow state is properly maintained."""
        query = "Find senior consultants in London"
        response = self.agent.process_message(query)
        
        # Check session history
        self.assertEqual(len(self.agent.workflow.state["session_history"]), 1)
        last_interaction = self.agent.workflow.state["session_history"][-1]
        
        # Verify state contents
        self.assertIn("query", last_interaction)
        self.assertIn("results", last_interaction)
        self.assertIn("response", last_interaction)
    
    def test_error_handling(self):
        """Test workflow handles errors gracefully."""
        # Mock an error in the resource fetcher
        self.firebase_mock.collection().where().get.side_effect = Exception("Database error")
        
        query = "Find developers in London"
        response = self.agent.process_message(query)
        
        # Verify error is handled gracefully
        self.assertIn("unable to fetch", response.lower())
        self.assertIn("try again", response.lower())

if __name__ == '__main__':
    unittest.main() 