"""
Tests for the ResourceTools implementation.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add parent directory to path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.tools.resource_tools import ResourceTools
from src.firebase_utils import FirebaseClient

class TestResourceTools(unittest.TestCase):
    """Test cases for the ResourceTools class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock Firebase client
        self.mock_firebase = MagicMock(spec=FirebaseClient)
        self.mock_firebase.is_connected = True
        
        # Sample resources for testing
        self.sample_resources = [
            {
                "employeeNumber": "E001",
                "name": "John Doe",
                "location": "London",
                "rank": "Senior Consultant",
                "skills": ["Python", "Java", "AI"]
            },
            {
                "employeeNumber": "E002",
                "name": "Jane Smith",
                "location": "Manchester",
                "rank": "Consultant",
                "skills": ["Frontend", "JavaScript", "React"]
            }
        ]
        
        # Set up mock return value for get_resources
        self.mock_firebase.get_resources.return_value = self.sample_resources
        
        # Set up mock return value for get_resource_metadata
        self.mock_firebase.get_resource_metadata.return_value = {
            "locations": ["London", "Manchester", "Edinburgh"],
            "ranks": ["Analyst", "Consultant", "Senior Consultant"],
            "skills": ["Python", "Java", "Frontend", "JavaScript", "React", "AI"]
        }
        
        # Set up mock return value for save_query_data
        self.mock_firebase.save_query_data.return_value = True
        
        # Create ResourceTools instance with mock Firebase client
        self.resource_tools = ResourceTools(firebase_client=self.mock_firebase)
    
    def test_query_resources_success(self):
        """Test successful resource query."""
        # Call the method under test
        result = self.resource_tools._query_resources_impl(
            locations=["London"],
            skills=["Python"],
            limit=10
        )
        
        # Check that Firebase client was called with correct params
        self.mock_firebase.get_resources.assert_called_once_with(
            locations=["London"],
            ranks=None,
            skills=["Python"],
            weeks=None,
            availability_status=None,
            min_hours=None,
            limit=10
        )
        
        # Check the result
        self.assertEqual(result["results"], self.sample_resources)
        self.assertEqual(result["total"], len(self.sample_resources))
        self.assertEqual(result["query"]["locations"], ["London"])
        self.assertEqual(result["query"]["skills"], ["Python"])
    
    def test_query_resources_no_connection(self):
        """Test resource query with no Firebase connection."""
        # Set is_connected to False
        self.mock_firebase.is_connected = False
        
        # Call the method under test
        result = self.resource_tools._query_resources_impl(
            locations=["London"],
            skills=["Python"]
        )
        
        # Check that Firebase client was not called
        self.mock_firebase.get_resources.assert_not_called()
        
        # Check the result
        self.assertEqual(result["results"], [])
        self.assertEqual(result["total"], 0)
        self.assertIn("error", result)
    
    def test_query_resources_error(self):
        """Test resource query when Firebase client raises an exception."""
        # Set up mock to raise an exception
        self.mock_firebase.get_resources.side_effect = Exception("Test error")
        
        # Call the method under test
        result = self.resource_tools._query_resources_impl(
            locations=["London"],
            skills=["Python"]
        )
        
        # Check the result
        self.assertEqual(result["results"], [])
        self.assertEqual(result["total"], 0)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Test error")
    
    def test_get_resource_metadata_success(self):
        """Test successful metadata retrieval."""
        # Call the method under test
        result = self.resource_tools._get_resource_metadata_impl()
        
        # Check that Firebase client was called
        self.mock_firebase.get_resource_metadata.assert_called_once()
        
        # Check the result
        self.assertEqual(result["locations"], ["London", "Manchester", "Edinburgh"])
        self.assertEqual(result["ranks"], ["Analyst", "Consultant", "Senior Consultant"])
        self.assertEqual(result["skills"], ["Python", "Java", "Frontend", "JavaScript", "React", "AI"])
    
    def test_get_resource_metadata_no_connection(self):
        """Test metadata retrieval with no Firebase connection."""
        # Set is_connected to False
        self.mock_firebase.is_connected = False
        
        # Call the method under test
        result = self.resource_tools._get_resource_metadata_impl()
        
        # Check that Firebase client was not called
        self.mock_firebase.get_resource_metadata.assert_not_called()
        
        # Check the result
        self.assertEqual(result["locations"], [])
        self.assertEqual(result["ranks"], [])
        self.assertEqual(result["skills"], [])
        self.assertIn("error", result)
    
    def test_save_query_success(self):
        """Test successful query saving."""
        # Call the method under test
        result = self.resource_tools._save_query_impl(
            query="Test query",
            response="Test response",
            metadata={"locations": ["London"]},
            session_id="test_session"
        )
        
        # Check that Firebase client was called with correct params
        self.mock_firebase.save_query_data.assert_called_once_with(
            query="Test query",
            response="Test response",
            metadata={"locations": ["London"]},
            session_id="test_session"
        )
        
        # Check the result
        self.assertTrue(result)
    
    def test_save_query_no_connection(self):
        """Test query saving with no Firebase connection."""
        # Set is_connected to False
        self.mock_firebase.is_connected = False
        
        # Call the method under test
        result = self.resource_tools._save_query_impl(
            query="Test query",
            response="Test response",
            metadata={"locations": ["London"]},
            session_id="test_session"
        )
        
        # Check that Firebase client was not called
        self.mock_firebase.save_query_data.assert_not_called()
        
        # Check the result
        self.assertFalse(result)
    
    def test_save_query_error(self):
        """Test query saving when Firebase client raises an exception."""
        # Set up mock to raise an exception
        self.mock_firebase.save_query_data.side_effect = Exception("Test error")
        
        # Call the method under test
        result = self.resource_tools._save_query_impl(
            query="Test query",
            response="Test response",
            metadata={"locations": ["London"]},
            session_id="test_session"
        )
        
        # Check the result
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main() 