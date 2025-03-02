import unittest
from unittest.mock import MagicMock, patch

# Import the module to be tested
from src.query_translator import QueryTranslator

class TestQueryTranslator(unittest.TestCase):
    """Test cases for the QueryTranslator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.translator = QueryTranslator()
    
    def test_query_translator_extracts_location(self):
        """Test that the translator extracts location information."""
        # Test queries with location information
        location_queries = [
            ("Find developers in London", ["London"]),
            ("Show me consultants in Oslo", ["Oslo"]),
            ("Are there any analysts in Manchester?", ["Manchester"]),
            ("Find resources in London and Bristol", ["Bristol", "London"]),
            ("Who works in the UK?", ["Belfast", "Bristol", "London", "Manchester"])
        ]
        
        for query, expected_locations in location_queries:
            result = self.translator.translate(query)
            self.assertEqual(result["location"], expected_locations)
    
    def test_query_translator_extracts_skills(self):
        """Test that the translator extracts skills information."""
        # Test queries with skills information
        skill_queries = [
            ("Find frontend developers", "Frontend Developer"),
            ("Show me consultants with AWS skills", "AWS Engineer"),
            ("Are there any Python developers?", None),  # Python is not in our skill list
            ("Find resources with frontend and backend skills", "Frontend Developer"),  # First skill found
            ("Who knows cloud engineering?", "Cloud Engineer")
        ]
        
        for query, expected_skill in skill_queries:
            result = self.translator.translate(query)
            self.assertEqual(result["skill"], expected_skill)
    
    def test_query_translator_extracts_rank(self):
        """Test that the translator extracts rank information."""
        # Test queries with rank information
        rank_queries = [
            ("Find senior consultants", "Senior Consultant"),
            ("Show me analysts", "Analyst"),
            ("Are there any partners?", "Partner"),
            ("Find resources who are consultants or senior consultants", "Consultant"),  # First rank found
            ("Who is a principal consultant?", "Principal Consultant")
        ]
        
        for query, expected_rank in rank_queries:
            result = self.translator.translate(query)
            self.assertEqual(result["rank"], expected_rank)
    
    def test_query_translator_extracts_availability(self):
        """Test that the translator extracts availability information."""
        # Test queries with availability information
        availability_queries = [
            ("Who is available in Week 2?", [2]),
            ("Find developers available next week", [1]),
            ("Show me consultants available in Weeks 3 and 4", [3, 4]),
            ("Are there any analysts available in Week 5?", [5]),
            ("Find resources available in the next month", [1, 2, 3, 4])
        ]
        
        for query, expected_weeks in availability_queries:
            result = self.translator.translate(query)
            self.assertEqual(result["availability"], expected_weeks)
    
    def test_query_translator_handles_followup_queries(self):
        """Test that the translator maintains context for follow-up queries."""
        # Initial query
        initial_query = "Find frontend developers in London"
        initial_context = None
        
        initial_result = self.translator.translate(initial_query, initial_context)
        self.assertEqual(initial_result["location"], ["London"])
        self.assertEqual(initial_result["skill"], "Frontend Developer")
        self.assertEqual(initial_result["rank"], None)
        self.assertEqual(initial_result["availability"], [])
        
        # Follow-up query about availability
        followup_query = "Are any of them available in Week 2?"
        followup_context = {
            "locations": ["London"],
            "skills": ["Frontend Developer"],
            "ranks": [],
            "weeks": []
        }
        
        followup_result = self.translator.translate(followup_query, followup_context)
        self.assertEqual(followup_result["location"], ["London"])  # Should maintain location
        self.assertEqual(followup_result["skill"], "Frontend Developer")  # Should maintain skills
        self.assertEqual(followup_result["rank"], None)
        self.assertEqual(followup_result["availability"], [2])  # Should extract week
        
        # Another follow-up query about a different week
        another_followup_query = "What about Week 3?"
        another_followup_context = {
            "locations": ["London"],
            "skills": ["Frontend Developer"],
            "ranks": [],
            "weeks": [2]
        }
        
        another_followup_result = self.translator.translate(another_followup_query, another_followup_context)
        self.assertEqual(another_followup_result["location"], ["London"])  # Should maintain location
        self.assertEqual(another_followup_result["skill"], "Frontend Developer")  # Should maintain skills
        self.assertEqual(another_followup_result["rank"], None)
        self.assertEqual(another_followup_result["availability"], [3])  # Should update week
    
    def test_query_translator_handles_complex_queries(self):
        """Test that the translator handles complex queries with multiple criteria."""
        # Complex query with multiple criteria
        complex_query = "Find senior frontend developers in London available in Week 2"
        
        result = self.translator.translate(complex_query)
        self.assertEqual(result["location"], ["London"])
        self.assertEqual(result["skill"], "Frontend Developer")
        self.assertEqual(result["rank"], "Senior Consultant")
        self.assertEqual(result["availability"], [2])

if __name__ == '__main__':
    unittest.main() 