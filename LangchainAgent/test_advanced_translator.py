#!/usr/bin/env python3
"""
Advanced test script for the QueryTranslator class.

This script tests the enhanced features of the QueryTranslator, including:
- Country and region inference
- Rank relationship understanding
- Skill normalization
- Follow-up query handling with accumulating availability
"""

import json
import os
import sys
from typing import Dict, Any, List

from src.query_translator import QueryTranslator

def validate_result(result: Dict[str, Any], expected_fields: List[str] = None) -> bool:
    """
    Validate that the result has the expected structure.
    
    Args:
        result: The result dictionary to validate
        expected_fields: Optional list of fields that should be present
        
    Returns:
        True if the result is valid, False otherwise
    """
    if expected_fields is None:
        expected_fields = ["location", "rank", "skill", "availability"]
    
    # Check that all expected fields are present
    for field in expected_fields:
        if field not in result:
            print(f"Error: Missing field '{field}' in result")
            return False
    
    # Validate location field
    if result["location"] is not None and not (
        isinstance(result["location"], list) or 
        isinstance(result["location"], str)
    ):
        print(f"Error: 'location' should be a list, string, or None, got {type(result['location'])}")
        return False
    
    # Validate rank field
    if result["rank"] is not None and not isinstance(result["rank"], (str, list)):
        print(f"Error: 'rank' should be a string, list, or None, got {type(result['rank'])}")
        return False
    
    # Validate skill field
    if result["skill"] is not None and not isinstance(result["skill"], (str, list)):
        print(f"Error: 'skill' should be a string, list, or None, got {type(result['skill'])}")
        return False
    
    # Validate availability field
    if not isinstance(result["availability"], list):
        print(f"Error: 'availability' should be a list, got {type(result['availability'])}")
        return False
    
    for item in result["availability"]:
        if not isinstance(item, int):
            print(f"Error: Items in 'availability' should be integers, got {type(item)}")
            return False
    
    return True

def check_expected_values(result: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    """
    Check if the result contains the expected values.
    
    Args:
        result: The result dictionary to check
        expected: Dictionary with expected values
        
    Returns:
        True if the result contains the expected values, False otherwise
    """
    for key, expected_value in expected.items():
        if key not in result:
            print(f"Error: Missing key '{key}' in result")
            return False
        
        actual_value = result[key]
        
        # Handle location specially since it's always an array
        if key == "location" and expected_value is not None:
            if not isinstance(actual_value, list):
                print(f"Error: 'location' should be a list, got {type(actual_value)}")
                return False
            
            # Convert expected_value to list if it's not already
            expected_locations = expected_value if isinstance(expected_value, list) else [expected_value]
            
            # Check if all expected locations are in the actual locations
            for location in expected_locations:
                if location not in actual_value:
                    print(f"Error: Expected location '{location}' not found in {actual_value}")
                    return False
            
            # Check if the number of locations matches
            if len(expected_locations) != len(actual_value):
                print(f"Warning: Number of locations doesn't match. Expected {len(expected_locations)}, got {len(actual_value)}")
                # This is just a warning, not an error
        
        # Handle availability specially
        elif key == "availability":
            if not isinstance(actual_value, list):
                print(f"Error: 'availability' should be a list, got {type(actual_value)}")
                return False
            
            # Check if all expected weeks are in the actual weeks
            for week in expected_value:
                if week not in actual_value:
                    print(f"Error: Expected week {week} not found in {actual_value}")
                    return False
            
            # Check if the number of weeks matches
            if len(expected_value) != len(actual_value):
                print(f"Warning: Number of weeks doesn't match. Expected {len(expected_value)}, got {len(actual_value)}")
                # This is just a warning, not an error
        
        # Handle other fields
        elif actual_value != expected_value:
            print(f"Error: Expected '{key}' to be '{expected_value}', got '{actual_value}'")
            return False
    
    return True

def main():
    """
    Main function to test the advanced features of the QueryTranslator.
    """
    # Track test results
    tests_passed = 0
    tests_failed = 0
    
    # Check if ANTHROPIC_API_KEY is set
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in environment variables.")
        print("This is required for the QueryTranslator to function.")
        sys.exit(1)
    
    # Create translator
    try:
        translator = QueryTranslator()
        print("Successfully initialized QueryTranslator with Anthropic API key.\n")
    except ValueError as e:
        print(f"Error initializing QueryTranslator: {e}")
        sys.exit(1)
    
    # Test cases for country and region inference
    print("Testing country and region inference:\n")
    
    country_tests = [
        {
            "query": "Find frontend developers in UK",
            "expected": {
                "location": ["London", "Bristol", "Manchester", "Belfast"],
                "rank": None,
                "skill": "Frontend Developer",
                "availability": []
            }
        },
        {
            "query": "Show me consultants in Nordic countries",
            "expected": {
                "location": ["Oslo", "Stockholm", "Copenhagen"],
                "rank": "Consultant",
                "skill": None,
                "availability": []
            }
        },
        {
            "query": "Any partners in Scandinavia?",
            "expected": {
                "location": ["Oslo", "Stockholm", "Copenhagen"],
                "rank": "Partner",
                "skill": None,
                "availability": []
            }
        }
    ]
    
    for test in country_tests:
        result = translator.translate(test["query"])
        print(f"Query: {test['query']}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Validate the result structure
        structure_valid = validate_result(result)
        
        # Check if the result contains the expected values
        values_valid = check_expected_values(result, test["expected"])
        
        if structure_valid and values_valid:
            print("✅ Test passed")
            tests_passed += 1
        else:
            print("❌ Test failed")
            tests_failed += 1
            
        print("-" * 80)
    
    # Test cases for rank relationships
    print("\nTesting rank relationships:\n")
    
    rank_tests = [
        {
            "query": "Find associate partners or consulting directors in London",
            "expected": {
                "location": ["London"],
                "rank": "Associate Partner",  # Either AP or CD is acceptable
                "skill": None,
                "availability": []
            }
        },
        {
            "query": "Show me senior people in Bristol",
            "expected": {
                "location": ["Bristol"],
                "rank": "Senior Consultant",
                "skill": None,
                "availability": []
            }
        }
    ]
    
    for test in rank_tests:
        result = translator.translate(test["query"])
        print(f"Query: {test['query']}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Validate the result structure
        structure_valid = validate_result(result)
        
        # For rank tests, we need special handling since either AP or CD is acceptable
        if test["query"] == "Find associate partners or consulting directors in London":
            if result["rank"] not in ["Associate Partner", "Consulting Director"]:
                print(f"Error: Expected rank to be either 'Associate Partner' or 'Consulting Director', got '{result['rank']}'")
                values_valid = False
            else:
                # Override the expected rank to match what was returned
                test["expected"]["rank"] = result["rank"]
                values_valid = check_expected_values(result, test["expected"])
        else:
            values_valid = check_expected_values(result, test["expected"])
        
        if structure_valid and values_valid:
            print("✅ Test passed")
            tests_passed += 1
        else:
            print("❌ Test failed")
            tests_failed += 1
            
        print("-" * 80)
    
    # Test cases for skill normalization
    print("\nTesting skill normalization:\n")
    
    skill_tests = [
        {
            "query": "Find front-end devs in London",
            "expected": {
                "location": ["London"],
                "rank": None,
                "skill": "Frontend Developer",
                "availability": []
            }
        },
        {
            "query": "Show me AWS experts in Oslo",
            "expected": {
                "location": ["Oslo"],
                "rank": None,
                "skill": "AWS Engineer",
                "availability": []
            }
        }
    ]
    
    for test in skill_tests:
        result = translator.translate(test["query"])
        print(f"Query: {test['query']}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Validate the result structure
        structure_valid = validate_result(result)
        
        # Check if the result contains the expected values
        values_valid = check_expected_values(result, test["expected"])
        
        if structure_valid and values_valid:
            print("✅ Test passed")
            tests_passed += 1
        else:
            print("❌ Test failed")
            tests_failed += 1
            
        print("-" * 80)
    
    # Test cases for follow-up query handling with accumulating availability
    print("\nTesting follow-up query handling with accumulating availability:\n")
    
    # Initial query
    initial_query = "Find frontend developers in London available in Week 1"
    initial_result = translator.translate(initial_query)
    
    print(f"Initial Query: {initial_query}")
    print(f"Initial Result: {json.dumps(initial_result, indent=2)}")
    
    # Validate the initial result
    initial_structure_valid = validate_result(initial_result)
    initial_values_valid = check_expected_values(initial_result, {
        "location": ["London"],
        "rank": None,
        "skill": "Frontend Developer",
        "availability": [1]
    })
    
    if initial_structure_valid and initial_values_valid:
        print("✅ Test passed")
        tests_passed += 1
    else:
        print("❌ Test failed")
        tests_failed += 1
        
    print("-" * 80)
    
    # First follow-up query
    followup_query = "What about Week 3?"
    followup_result = translator.translate(followup_query, initial_result)
    
    print(f"Follow-up Query: {followup_query}")
    print(f"Follow-up Result: {json.dumps(followup_result, indent=2)}")
    
    # Validate the follow-up result
    followup_structure_valid = validate_result(followup_result)
    followup_values_valid = check_expected_values(followup_result, {
        "location": ["London"],
        "rank": None,
        "skill": "Frontend Developer",
        "availability": [1, 3]  # Should include both weeks
    })
    
    if followup_structure_valid and followup_values_valid:
        print("✅ Test passed")
        tests_passed += 1
    else:
        print("❌ Test failed")
        tests_failed += 1
        
    print("-" * 80)
    
    # Second follow-up query
    another_followup_query = "And Week 5 as well"
    another_followup_result = translator.translate(another_followup_query, followup_result)
    
    print(f"Another Follow-up Query: {another_followup_query}")
    print(f"Another Follow-up Result: {json.dumps(another_followup_result, indent=2)}")
    
    # Validate the second follow-up result
    another_followup_structure_valid = validate_result(another_followup_result)
    another_followup_values_valid = check_expected_values(another_followup_result, {
        "location": ["London"],
        "rank": None,
        "skill": "Frontend Developer",
        "availability": [1, 3, 5]  # Should include all three weeks
    })
    
    if another_followup_structure_valid and another_followup_values_valid:
        print("✅ Test passed")
        tests_passed += 1
    else:
        print("❌ Test failed")
        tests_failed += 1
    
    # Print test summary
    print("\n" + "=" * 40)
    print(f"Test Summary: {tests_passed} passed, {tests_failed} failed")
    print("=" * 40)
    
    if tests_failed > 0:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All tests passed successfully!")

if __name__ == "__main__":
    main() 