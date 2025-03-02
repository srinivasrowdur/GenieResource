"""
Script to run all LangGraph tests.
"""

import unittest
import os
import sys

# Add parent directory to path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.langgraph_tests.test_agent import TestReActAgent
from tests.langgraph_tests.test_resource_tools import TestResourceTools
from tests.langgraph_tests.test_query_tools import TestQueryTools
from tests.langgraph_tests.test_integration import TestLangGraphIntegration

def create_test_suite():
    """Create a test suite with all LangGraph tests."""
    test_suite = unittest.TestSuite()
    
    # Add all test cases
    test_suite.addTest(unittest.makeSuite(TestReActAgent))
    test_suite.addTest(unittest.makeSuite(TestResourceTools))
    test_suite.addTest(unittest.makeSuite(TestQueryTools))
    test_suite.addTest(unittest.makeSuite(TestLangGraphIntegration))
    
    return test_suite

if __name__ == "__main__":
    # Create test suite
    suite = create_test_suite()
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate status code
    sys.exit(not result.wasSuccessful()) 