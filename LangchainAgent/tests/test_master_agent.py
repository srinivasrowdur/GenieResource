import unittest
from unittest.mock import MagicMock, patch

# Import the module to be tested (will be implemented later)
# from src.master_agent import MasterAgent

class TestMasterAgent(unittest.TestCase):
    """Test cases for the MasterAgent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # We'll mock the dependencies for now
        self.query_translator = MagicMock()
        self.resource_fetcher = MagicMock()
        self.availability_checker = MagicMock()
        self.response_generator = MagicMock()
        
        # We'll implement this class later
        # self.agent = MasterAgent(
        #     query_translator=self.query_translator,
        #     resource_fetcher=self.resource_fetcher,
        #     availability_checker=self.availability_checker,
        #     response_generator=self.response_generator
        # )
    
    def test_master_agent_identifies_resource_query(self):
        """Test that the agent correctly identifies resource-related queries."""
        # Resource-related queries
        resource_queries = [
            "Find frontend developers in London",
            "Show me consultants with AWS skills",
            "Who is available in Week 2?",
            "Are there any senior consultants in Oslo?",
            "List all analysts in Manchester with Python skills"
        ]
        
        # We'll implement this method later
        # for query in resource_queries:
        #     self.assertTrue(self.agent.is_resource_query(query))
    
    def test_master_agent_rejects_non_resource_query(self):
        """Test that the agent rejects queries not related to resources."""
        # Non-resource queries
        non_resource_queries = [
            "What's the weather like today?",
            "Tell me a joke",
            "What's the capital of France?",
            "How do I cook pasta?",
            "What's the meaning of life?"
        ]
        
        # We'll implement this method later
        # for query in non_resource_queries:
        #     self.assertFalse(self.agent.is_resource_query(query))
    
    def test_master_agent_orchestrates_components(self):
        """Test that the agent correctly orchestrates the flow between components."""
        # Mock the behavior of components
        self.query_translator.translate.return_value = {
            "locations": ["London"],
            "skills": ["Frontend Developer"],
            "ranks": [],
            "weeks": []
        }
        
        self.resource_fetcher.fetch.return_value = [
            {"name": "John Doe", "location": "London", "skills": ["Frontend Developer"]}
        ]
        
        self.response_generator.generate.return_value = "I found 1 frontend developer in London: John Doe."
        
        # Test query
        query = "Find frontend developers in London"
        
        # We'll implement this method later
        # response = self.agent.process_query(query)
        
        # Verify that components were called correctly
        # self.query_translator.translate.assert_called_once_with(query, None)
        # self.resource_fetcher.fetch.assert_called_once()
        # self.availability_checker.check.assert_not_called()  # No availability requested
        # self.response_generator.generate.assert_called_once()
        
        # Verify response
        # self.assertEqual(response, "I found 1 frontend developer in London: John Doe.")
    
    def test_master_agent_handles_availability_query(self):
        """Test that the agent correctly handles availability queries."""
        # Mock the behavior of components
        self.query_translator.translate.return_value = {
            "locations": ["London"],
            "skills": ["Frontend Developer"],
            "ranks": [],
            "weeks": [2]
        }
        
        self.resource_fetcher.fetch.return_value = [
            {"name": "John Doe", "location": "London", "skills": ["Frontend Developer"]}
        ]
        
        self.availability_checker.check.return_value = [
            {"name": "John Doe", "location": "London", "skills": ["Frontend Developer"], "availability": [{"week": 2, "status": "Available"}]}
        ]
        
        self.response_generator.generate.return_value = "I found 1 frontend developer in London available in Week 2: John Doe."
        
        # Test query
        query = "Find frontend developers in London available in Week 2"
        
        # We'll implement this method later
        # response = self.agent.process_query(query)
        
        # Verify that components were called correctly
        # self.query_translator.translate.assert_called_once_with(query, None)
        # self.resource_fetcher.fetch.assert_called_once()
        # self.availability_checker.check.assert_called_once()
        # self.response_generator.generate.assert_called_once()
        
        # Verify response
        # self.assertEqual(response, "I found 1 frontend developer in London available in Week 2: John Doe.")
    
    def test_master_agent_handles_followup_query(self):
        """Test that the agent correctly handles follow-up queries."""
        # First query
        self.query_translator.translate.return_value = {
            "locations": ["London"],
            "skills": ["Frontend Developer"],
            "ranks": [],
            "weeks": []
        }
        
        self.resource_fetcher.fetch.return_value = [
            {"name": "John Doe", "location": "London", "skills": ["Frontend Developer"]},
            {"name": "Jane Smith", "location": "London", "skills": ["Frontend Developer"]}
        ]
        
        self.response_generator.generate.return_value = "I found 2 frontend developers in London: John Doe and Jane Smith."
        
        # We'll implement this method later
        # first_response = self.agent.process_query("Find frontend developers in London")
        
        # Follow-up query
        self.query_translator.translate.return_value = {
            "locations": [],
            "skills": [],
            "ranks": [],
            "weeks": [2]
        }
        
        self.availability_checker.check.return_value = [
            {"name": "John Doe", "location": "London", "skills": ["Frontend Developer"], "availability": [{"week": 2, "status": "Available"}]},
            {"name": "Jane Smith", "location": "London", "skills": ["Frontend Developer"], "availability": [{"week": 2, "status": "Not Available"}]}
        ]
        
        self.response_generator.generate.return_value = "1 out of 2 frontend developers in London is available in Week 2: John Doe."
        
        # We'll implement this method later
        # followup_response = self.agent.process_query("Are they available in Week 2?")
        
        # Verify that the follow-up query reused the previous results
        # self.resource_fetcher.fetch.assert_called_once()  # Should not be called again
        # self.availability_checker.check.assert_called_once()
        
        # Verify response
        # self.assertEqual(followup_response, "1 out of 2 frontend developers in London is available in Week 2: John Doe.")

if __name__ == '__main__':
    unittest.main() 