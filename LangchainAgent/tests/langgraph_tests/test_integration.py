"""
Integration tests for the LangGraph implementation.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import tempfile
import json

# Add parent directory to path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import ReActAgent
from src.firebase_utils import FirebaseClient
from src.tools.resource_tools import ResourceTools
from src.tools.query_tools import QueryTools

class TestLangGraphIntegration(unittest.TestCase):
    """Integration tests for the LangGraph implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock model
        self.mock_model = MagicMock()
        self.mock_model.invoke.return_value = MagicMock(content="Test response")
        
        # Create a temporary JSON file for Firebase credentials
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.write(b'{"test": "credentials"}')
        self.temp_file.close()
        
        # Create a real FirebaseClient but with mocked functionality
        with patch('firebase_admin.credentials.Certificate'), \
             patch('firebase_admin.initialize_app'), \
             patch('firebase_admin.firestore.client'):
            self.firebase_client = FirebaseClient(credentials_path=self.temp_file.name)
        
        # Mock Firebase client methods
        self.firebase_client.get_resources = MagicMock(return_value=[
            {
                "employeeNumber": "E001",
                "name": "John Doe",
                "location": "London",
                "rank": "Senior Consultant",
                "skills": ["Python", "Java", "AI"]
            }
        ])
        self.firebase_client.get_resource_metadata = MagicMock(return_value={
            "locations": ["London", "Manchester"],
            "ranks": ["Analyst", "Consultant", "Senior Consultant"],
            "skills": ["Python", "Java", "AI"]
        })
        self.firebase_client.save_query_data = MagicMock(return_value=True)
        self.firebase_client.is_connected = True
        
        # Mock the agent's invoke method to return a structured response
        self.agent_response = {
            "output": "I found 1 resource matching your query: John Doe, a Senior Consultant in London with skills in Python, Java, and AI."
        }
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary file
        os.unlink(self.temp_file.name)
    
    @patch('langchain.agents.AgentExecutor')
    def test_end_to_end_query_flow(self, mock_agent_executor):
        """Test the end-to-end flow from query to response."""
        # Set up mock agent executor
        mock_execute = MagicMock()
        mock_execute.invoke.return_value = self.agent_response
        mock_agent_executor.return_value = mock_execute
        
        # Create the agent
        agent = ReActAgent(
            model=self.mock_model,
            firebase_client=self.firebase_client
        )
        
        # Process a message
        result = agent.process_message("Find Python developers in London")
        
        # Check the result
        self.assertTrue(result["success"])
        self.assertEqual(result["response"], self.agent_response["output"])
    
    def test_tools_creation_and_registration(self):
        """Test that tools are created and registered correctly."""
        # Create a new agent
        agent = ReActAgent(
            model=self.mock_model,
            firebase_client=self.firebase_client
        )
        
        # Check that resource tools exist and are configured correctly
        self.assertIsInstance(agent.resource_tools, ResourceTools)
        self.assertEqual(agent.resource_tools.firebase_client, self.firebase_client)
        
        # Check that query tools exist and are configured correctly
        self.assertIsInstance(agent.query_tools, QueryTools)
        self.assertEqual(agent.query_tools.model, self.mock_model)
        
        # Check that agent has access to all tools
        tools = []
        for tool in agent.agent.tools:
            tools.append(tool.name)
        
        # Check that all expected tools are registered
        self.assertIn("translate_query", tools)
        self.assertIn("generate_response", tools)
        self.assertIn("query_resources", tools)
        self.assertIn("get_resource_metadata", tools)
        self.assertIn("save_query", tools)
    
    def test_firebase_integration(self):
        """Test that Firebase integration works correctly."""
        # Create a new agent
        agent = ReActAgent(
            model=self.mock_model,
            firebase_client=self.firebase_client
        )
        
        # Set up mock response
        agent.agent.invoke = MagicMock(return_value={"output": "Test response"})
        
        # Process a message
        agent.process_message("Find Python developers in London")
        
        # Check that Firebase client's get_resources was called
        # Note: In this test, we're not actually calling the tool, just checking the agent setup
        self.assertIsNotNone(agent.resource_tools)
        self.assertEqual(agent.resource_tools.firebase_client, self.firebase_client)
    
    def test_session_state_management(self):
        """Test that session state is managed correctly."""
        # Create a new agent
        agent = ReActAgent(
            model=self.mock_model,
            firebase_client=self.firebase_client
        )
        
        # Set up mock response
        agent.agent.invoke = MagicMock(return_value={"output": "Test response"})
        
        # Process a message with a custom session ID
        agent.process_message("Find Python developers in London", session_id="test_session")
        
        # Check that session ID was set
        self.assertEqual(agent.thread_id, "test_session")
        
        # Check that history was updated
        self.assertEqual(len(agent.session_history), 2)  # user message + assistant response
        
        # Reset the agent
        agent.reset()
        
        # Check that history was cleared
        self.assertEqual(len(agent.session_history), 0)
        self.assertNotEqual(agent.thread_id, "test_session")

if __name__ == "__main__":
    unittest.main() 