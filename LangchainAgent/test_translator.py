#!/usr/bin/env python3
"""
Test script for the QueryTranslator class.

This script tests the QueryTranslator's ability to translate natural language queries
into structured data. It includes validation of the JSON structure and content.
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
        expected_fields = ["locations", "ranks", "skills", "weeks", "availability_status", "min_hours"]
    
    # Check that at least one of the expected fields is present
    fields_found = False
    for field in expected_fields:
        if field in result:
            fields_found = True
            break
    
    if not fields_found:
        print(f"Error: None of the expected fields {expected_fields} found in result")
        return False
    
    # Validate locations field
    if "locations" in result and result["locations"] is not None and not (
        isinstance(result["locations"], list)
    ):
        print(f"Error: 'locations' should be a list or None, got {type(result['locations'])}")
        return False
    
    # Validate ranks field
    if "ranks" in result and result["ranks"] is not None and not isinstance(result["ranks"], list):
        print(f"Error: 'ranks' should be a list or None, got {type(result['ranks'])}")
        return False
    
    # Validate skills field
    if "skills" in result and result["skills"] is not None and not isinstance(result["skills"], list):
        print(f"Error: 'skills' should be a list or None, got {type(result['skills'])}")
        return False
    
    # Validate weeks field
    if "weeks" in result and not isinstance(result["weeks"], list):
        print(f"Error: 'weeks' should be a list, got {type(result['weeks'])}")
        return False
    
    if "weeks" in result:
        for item in result["weeks"]:
            if not isinstance(item, int):
                print(f"Error: Items in 'weeks' should be integers, got {type(item)}")
                return False
    
    # Simplified validation for our updated structure
    return True

def main():
    """
    Main function to test the QueryTranslator.
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
    
    # Test queries with standard phrasing
    standard_queries = [
        "Find frontend developers in London",
        "Show me consultants with AWS skills in Oslo",
        "Are there any partners in Manchester?",
        "Find senior consultants in Bristol available in Week 2",
        "Who are the analysts in Copenhagen?"
    ]
    
    # Test queries with typos and unconventional phrasing
    challenging_queries = [
        "Find frntend devs in Londn",  # Typos
        "Show me ppl who know AWS in Osloo",  # Typos and slang
        "Any1 who is a partner in Manchestr?",  # Shorthand and typo
        "Senior ppl in Bristl who can work in wk 2",  # Abbreviations and typos
        "Analysts in Copenhagn pls"  # Typo and informal language
    ]
    
    # Process standard queries
    print("Testing QueryTranslator with standard queries:\n")
    for query in standard_queries:
        result = translator.translate(query)
        print(f"Query: {query}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Validate the result
        if validate_result(result):
            print("✅ Validation passed")
            tests_passed += 1
        else:
            print("❌ Validation failed")
            tests_failed += 1
            
        print("-" * 80)
    
    # Process challenging queries
    print("\nTesting QueryTranslator with challenging queries:\n")
    for query in challenging_queries:
        result = translator.translate(query)
        print(f"Query: {query}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Validate the result
        if validate_result(result):
            print("✅ Validation passed")
            tests_passed += 1
        else:
            print("❌ Validation failed")
            tests_failed += 1
            
        print("-" * 80)
    
    # Test specifically for "partners in nordics" case that was fixed
    print("\nTesting QueryTranslator with the 'partners in nordics' case:\n")
    nordics_query = "partners in nordics"
    nordics_result = translator.translate(nordics_query)
    print(f"Query: {nordics_query}")
    print(f"Result: {json.dumps(nordics_result, indent=2)}")
    
    # Check for the specific expectation
    if "locations" in nordics_result and "ranks" in nordics_result:
        locations_match = False
        if "Nordics" in nordics_result["locations"] or set(["Oslo", "Stockholm", "Copenhagen"]).issubset(set(nordics_result["locations"])):
            locations_match = True
        
        ranks_match = "Partner" in nordics_result["ranks"]
        
        if locations_match and ranks_match:
            print("✅ 'partners in nordics' test passed")
            tests_passed += 1
        else:
            print(f"❌ 'partners in nordics' test failed - expected locations (Nordics or [Oslo, Stockholm, Copenhagen]) and ranks [Partner]")
            tests_failed += 1
    else:
        print("❌ 'partners in nordics' test failed - missing locations or ranks fields")
        tests_failed += 1
    
    print("-" * 80)
    
    # Test follow-up queries
    print("\nTesting QueryTranslator with follow-up queries:\n")
    
    initial_query = "Find frontend developers in London"
    initial_result = translator.translate(initial_query)
    
    print(f"Initial Query: {initial_query}")
    print(f"Initial Result: {json.dumps(initial_result, indent=2)}")
    
    # Validate the initial result
    if validate_result(initial_result):
        print("✅ Validation passed")
        tests_passed += 1
    else:
        print("❌ Validation failed")
        tests_failed += 1
        
    print("-" * 80)
    
    followup_query = "Are any of them available in Week 2?"
    followup_result = translator.translate(followup_query, initial_result)
    
    print(f"Follow-up Query: {followup_query}")
    print(f"Follow-up Result: {json.dumps(followup_result, indent=2)}")
    
    # Validate the follow-up result
    if validate_result(followup_result):
        print("✅ Validation passed")
        tests_passed += 1
    else:
        print("❌ Validation failed")
        tests_failed += 1
        
    print("-" * 80)
    
    another_followup_query = "What about Week 3?"
    another_followup_result = translator.translate(another_followup_query, followup_result)
    
    print(f"Another Follow-up Query: {another_followup_query}")
    print(f"Another Follow-up Result: {json.dumps(another_followup_result, indent=2)}")
    
    # Validate the second follow-up result
    if validate_result(another_followup_result):
        print("✅ Validation passed")
        tests_passed += 1
    else:
        print("❌ Validation failed")
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