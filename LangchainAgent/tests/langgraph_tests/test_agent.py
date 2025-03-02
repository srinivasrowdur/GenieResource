"""
Tests for the LangGraph ReActAgent implementation.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import json

# Add parent directory to path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import ReActAgent
from src.firebase_utils import FirebaseClient

class TestReActAgent(unittest.TestCase):
    """Test cases for the ReActAgent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the model
        self.mock_model = MagicMock()
        self.mock_model.invoke.return_value = MagicMock(content="Test response")
        
        # Mock Firebase client
        self.mock_firebase = MagicMock(spec=FirebaseClient)
        self.mock_firebase.is_connected = True
        self.mock_firebase.get_resource_metadata.return_value = {
            "locations": ["London", "Manchester", "Edinburgh"],
            "ranks": ["Analyst", "Consultant", "Senior Consultant"],
            "skills": ["Python", "Java", "Frontend"]
        }
        
        # Create agent instance with mocked dependencies
        self.agent = ReActAgent(
            model=self.mock_model,
            firebase_client=self.mock_firebase
        )
    
    def test_agent_initialization(self):
        """Test that the agent initializes correctly."""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.model, self.mock_model)
        self.assertEqual(self.agent.firebase_client, self.mock_firebase)
        self.assertIsNotNone(self.agent.query_tools)
        self.assertIsNotNone(self.agent.resource_tools)
        
    def test_process_message_success(self):
        """Test that process_message returns a response when successful."""
        # Set up the mock agent's invoke method to return a valid result
        self.agent.agent.invoke = MagicMock(return_value={"output": "Successful response"})
        
        # Call the method under test
        result = self.agent.process_message("Find Python developers in London")
        
        # Check the result
        self.assertTrue(result["success"])
        self.assertEqual(result["response"], "Successful response")
        self.assertEqual(len(self.agent.session_history), 2)  # Should add user and assistant message
    
    def test_process_message_failure(self):
        """Test that process_message handles errors correctly."""
        # Set up the mock agent's invoke method to raise an exception
        self.agent.agent.invoke = MagicMock(side_effect=Exception("Test error"))
        
        # Call the method under test
        result = self.agent.process_message("This should fail")
        
        # Check the result
        self.assertFalse(result["success"])
        self.assertIn("Test error", result["response"])
        self.assertIn("error", result)
    
    def test_reset(self):
        """Test that reset clears the agent's state."""
        # Add some test history
        self.agent.session_history = ["test1", "test2"]
        self.agent.thread_id = "old_thread_id"
        
        # Reset the agent
        self.agent.reset()
        
        # Check that state is reset
        self.assertEqual(len(self.agent.session_history), 0)
        self.assertNotEqual(self.agent.thread_id, "old_thread_id")

    @patch('uuid.uuid4')
    def test_session_id_handling(self, mock_uuid):
        """Test that session_id is handled correctly."""
        mock_uuid.return_value = "test_uuid"
        
        # Create new agent to trigger UUID generation
        agent = ReActAgent(model=self.mock_model, firebase_client=self.mock_firebase)
        self.assertEqual(agent.thread_id, "test_uuid")
        
        # Test custom session ID
        result = agent.process_message("Test", session_id="custom_session_id")
        self.assertEqual(agent.thread_id, "custom_session_id")

if __name__ == "__main__":
    unittest.main() 