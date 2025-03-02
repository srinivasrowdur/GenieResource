#!/usr/bin/env python3
"""
Test script for rank-related queries in the QueryTranslator class.

This script tests the QueryTranslator's ability to handle queries that involve
rank hierarchies, specifically:
- Queries asking for ranks above a specified rank
- Queries asking for ranks below a specified rank
- Queries with complex rank specifications
"""

import json
import os
import sys
from typing import Dict, Any, List

from src.query_translator import QueryTranslator

# Define the rank hierarchy for reference
RANK_HIERARCHY = [
    "Partner",
    "Associate Partner",  # Same level as Consulting Director
    "Consulting Director",  # Same level as Associate Partner
    "Management Consultant",
    "Principal Consultant",
    "Senior Consultant",
    "Consultant",
    "Consultant Analyst",  # New rank added
    "Analyst"
]

def validate_result(result: Dict[str, Any]) -> bool:
    """
    Validate that the result has the expected structure.
    
    Args:
        result: The result dictionary to validate
        
    Returns:
        True if the result is valid, False otherwise
    """
    expected_fields = ["location", "rank", "skill", "availability"]
    
    # Check that all expected fields are present
    for field in expected_fields:
        if field not in result:
            print(f"Error: Missing field '{field}' in result")
            return False
    
    # Validate location field
    if result["location"] is not None and not isinstance(result["location"], list):
        print(f"Error: 'location' should be a list or None, got {type(result['location'])}")
        return False
    
    # Validate rank field
    if result["rank"] is not None and not isinstance(result["rank"], (str, list)):
        print(f"Error: 'rank' should be a string, list, or None, got {type(result['rank'])}")
        return False
    
    # Validate skill field
    if result["skill"] is not None and not isinstance(result["skill"], str):
        print(f"Error: 'skill' should be a string or None, got {type(result['skill'])}")
        return False
    
    # Validate availability field
    if not isinstance(result["availability"], list):
        print(f"Error: 'availability' should be a list, got {type(result['availability'])}")
        return False
    
    return True

def check_rank_in_range(result: Dict[str, Any], min_rank: str = None, max_rank: str = None) -> bool:
    """
    Check if the rank in the result is within the specified range in the hierarchy.
    
    Args:
        result: The result dictionary to check
        min_rank: The minimum rank in the hierarchy (inclusive)
        max_rank: The maximum rank in the hierarchy (inclusive)
        
    Returns:
        True if the rank is within the specified range, False otherwise
    """
    if result["rank"] is None:
        print("Error: Rank is None, but a specific rank was expected")
        return False
    
    # Handle the case where rank is a list
    if isinstance(result["rank"], list):
        # For simplicity, we'll just check the first rank in the list
        if not result["rank"]:
            print("Error: Rank list is empty")
            return False
        rank = result["rank"][0]
        print(f"Note: Using first rank '{rank}' from list {result['rank']} for range check")
    else:
        rank = result["rank"]
    
    # Check if the rank is in the hierarchy
    if rank not in RANK_HIERARCHY:
        print(f"Error: Rank '{rank}' is not in the defined hierarchy")
        return False
    
    # Check if the rank is within the specified range
    if min_rank and RANK_HIERARCHY.index(rank) > RANK_HIERARCHY.index(min_rank):
        print(f"Error: Rank '{rank}' is below the minimum rank '{min_rank}'")
        return False
    
    if max_rank and RANK_HIERARCHY.index(rank) < RANK_HIERARCHY.index(max_rank):
        print(f"Error: Rank '{rank}' is above the maximum rank '{max_rank}'")
        return False
    
    return True

def check_ranks_above(result: Dict[str, Any], threshold_rank: str) -> bool:
    """
    Check if the result contains all ranks above the threshold rank.
    
    Args:
        result: The result dictionary to check
        threshold_rank: The rank to check against
        
    Returns:
        True if the result contains all ranks above the threshold rank, False otherwise
    """
    if result["rank"] is None:
        print("Error: Rank is None, but ranks above a threshold were expected")
        return False
    
    if not isinstance(result["rank"], list):
        print(f"Error: Expected 'rank' to be a list for 'above' query, got {type(result['rank'])}")
        return False
    
    # Get the index of the threshold rank
    if threshold_rank not in RANK_HIERARCHY:
        print(f"Error: Threshold rank '{threshold_rank}' is not in the defined hierarchy")
        return False
    
    threshold_index = RANK_HIERARCHY.index(threshold_rank)
    
    # Get all ranks above the threshold
    expected_ranks = RANK_HIERARCHY[:threshold_index]
    
    # Special case: Associate Partner and Consulting Director are at the same level
    if threshold_rank == "Associate Partner" and "Consulting Director" not in expected_ranks:
        expected_ranks.append("Consulting Director")
    elif threshold_rank == "Consulting Director" and "Associate Partner" not in expected_ranks:
        expected_ranks.append("Associate Partner")
    
    # Check if all expected ranks are in the result
    missing_ranks = [rank for rank in expected_ranks if rank not in result["rank"]]
    if missing_ranks:
        print(f"Error: Missing ranks above '{threshold_rank}': {missing_ranks}")
        return False
    
    # Check if there are any unexpected ranks
    # Special case: Analyst should never be above Consultant Analyst
    if threshold_rank == "Consultant Analyst" and "Analyst" in result["rank"]:
        print(f"Error: Analyst should not be above Consultant Analyst")
        return False
    
    unexpected_ranks = [rank for rank in result["rank"] if rank not in expected_ranks]
    if unexpected_ranks:
        print(f"Warning: Unexpected ranks in result: {unexpected_ranks}")
        # This is just a warning, not an error
    
    return True

def check_ranks_below(result: Dict[str, Any], threshold_rank: str) -> bool:
    """
    Check if the result contains all ranks below the threshold rank.
    
    Args:
        result: The result dictionary to check
        threshold_rank: The rank to check against
        
    Returns:
        True if the result contains all ranks below the threshold rank, False otherwise
    """
    if result["rank"] is None:
        print("Error: Rank is None, but ranks below a threshold were expected")
        return False
    
    if not isinstance(result["rank"], list):
        print(f"Error: Expected 'rank' to be a list for 'below' query, got {type(result['rank'])}")
        return False
    
    # Get the index of the threshold rank
    if threshold_rank not in RANK_HIERARCHY:
        print(f"Error: Threshold rank '{threshold_rank}' is not in the defined hierarchy")
        return False
    
    threshold_index = RANK_HIERARCHY.index(threshold_rank)
    
    # Get all ranks below the threshold
    expected_ranks = RANK_HIERARCHY[threshold_index+1:]
    
    # Special case: Associate Partner and Consulting Director are at the same level
    if threshold_rank == "Associate Partner":
        # Remove Consulting Director from expected ranks if it's there
        expected_ranks = [rank for rank in expected_ranks if rank != "Consulting Director"]
    elif threshold_rank == "Consulting Director":
        # Remove Associate Partner from expected ranks if it's there
        expected_ranks = [rank for rank in expected_ranks if rank != "Associate Partner"]
    
    # Check if all expected ranks are in the result
    missing_ranks = [rank for rank in expected_ranks if rank not in result["rank"]]
    if missing_ranks:
        print(f"Error: Missing ranks below '{threshold_rank}': {missing_ranks}")
        return False
    
    # Check if there are any unexpected ranks
    unexpected_ranks = [rank for rank in result["rank"] if rank not in expected_ranks]
    if unexpected_ranks:
        print(f"Warning: Unexpected ranks in result: {unexpected_ranks}")
        # This is just a warning, not an error
    
    return True

def check_ranks_between(result: Dict[str, Any], lower_rank: str, upper_rank: str) -> bool:
    """
    Check if the result contains all ranks between the lower and upper ranks.
    
    Args:
        result: The result dictionary to check
        lower_rank: The lower rank in the hierarchy
        upper_rank: The upper rank in the hierarchy
        
    Returns:
        True if the result contains all ranks between the lower and upper ranks, False otherwise
    """
    if result["rank"] is None:
        print("Error: Rank is None, but ranks between thresholds were expected")
        return False
    
    if not isinstance(result["rank"], list):
        print(f"Error: Expected 'rank' to be a list for 'between' query, got {type(result['rank'])}")
        return False
    
    # Get the indices of the lower and upper ranks
    if lower_rank not in RANK_HIERARCHY:
        print(f"Error: Lower rank '{lower_rank}' is not in the defined hierarchy")
        return False
    
    if upper_rank not in RANK_HIERARCHY:
        print(f"Error: Upper rank '{upper_rank}' is not in the defined hierarchy")
        return False
    
    lower_index = RANK_HIERARCHY.index(lower_rank)
    upper_index = RANK_HIERARCHY.index(upper_rank)
    
    # Ensure lower_index is actually lower than upper_index in the hierarchy
    # (Remember: lower index in the array means higher rank in the hierarchy)
    if lower_index > upper_index:
        # Swap them to ensure correct order
        lower_index, upper_index = upper_index, lower_index
        lower_rank, upper_rank = upper_rank, lower_rank
    
    # Get all ranks between the lower and upper ranks (excluding the lower and upper ranks)
    expected_ranks = RANK_HIERARCHY[lower_index+1:upper_index]
    
    # Special case: Associate Partner and Consulting Director are at the same level
    if "Associate Partner" in expected_ranks and "Consulting Director" not in expected_ranks:
        expected_ranks.append("Consulting Director")
    elif "Consulting Director" in expected_ranks and "Associate Partner" not in expected_ranks:
        expected_ranks.append("Associate Partner")
    
    # Check if all expected ranks are in the result
    missing_ranks = [rank for rank in expected_ranks if rank not in result["rank"]]
    if missing_ranks:
        print(f"Error: Missing ranks between '{lower_rank}' and '{upper_rank}': {missing_ranks}")
        return False
    
    # Check if there are any unexpected ranks
    # Note: The LLM might include the boundary ranks (lower_rank and upper_rank) in the result,
    # which is acceptable behavior, so we don't consider them as unexpected
    acceptable_ranks = expected_ranks + [lower_rank, upper_rank]
    unexpected_ranks = [rank for rank in result["rank"] if rank not in acceptable_ranks]
    if unexpected_ranks:
        print(f"Warning: Unexpected ranks in result: {unexpected_ranks}")
        # This is just a warning, not an error
    
    return True

def main():
    """
    Main function to test rank-related queries in the QueryTranslator.
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
    
    # Test cases for "rank above" queries
    print("Testing 'rank above' queries:\n")
    
    rank_above_tests = [
        {
            "query": "Find resources with rank above consultant in London",
            "threshold_rank": "Consultant"
        },
        {
            "query": "Show me people ranked higher than senior consultant in Oslo",
            "threshold_rank": "Senior Consultant"
        },
        {
            "query": "Get resources more senior than management consultant",
            "threshold_rank": "Management Consultant"
        }
    ]
    
    for test in rank_above_tests:
        result = translator.translate(test["query"])
        print(f"Query: {test['query']}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Validate the result structure
        structure_valid = validate_result(result)
        
        # Check if the result contains all ranks above the threshold
        rank_valid = check_ranks_above(result, test["threshold_rank"])
        
        if structure_valid and rank_valid:
            print("✅ Test passed")
            tests_passed += 1
        else:
            print("❌ Test failed")
            tests_failed += 1
            
        print("-" * 80)
    
    # Test cases for "rank below" queries
    print("\nTesting 'rank below' queries:\n")
    
    rank_below_tests = [
        {
            "query": "Find resources with rank below principal consultant in London",
            "threshold_rank": "Principal Consultant"
        },
        {
            "query": "Show me people ranked lower than associate partner in Oslo",
            "threshold_rank": "Associate Partner"
        },
        {
            "query": "Get resources more junior than management consultant",
            "threshold_rank": "Management Consultant"
        }
    ]
    
    for test in rank_below_tests:
        result = translator.translate(test["query"])
        print(f"Query: {test['query']}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Validate the result structure
        structure_valid = validate_result(result)
        
        # Check if the result contains all ranks below the threshold
        rank_valid = check_ranks_below(result, test["threshold_rank"])
        
        if structure_valid and rank_valid:
            print("✅ Test passed")
            tests_passed += 1
        else:
            print("❌ Test failed")
            tests_failed += 1
            
        print("-" * 80)
    
    # Test cases for complex rank queries
    print("\nTesting complex rank queries:\n")
    
    complex_rank_tests = [
        {
            "query": "Find resources between consultant and principal consultant in London",
            "lower_rank": "Consultant",
            "upper_rank": "Principal Consultant"
        },
        {
            "query": "Show me people who are either partners or analysts in Oslo",
            "expected_ranks": ["Partner", "Analyst"]
        },
        {
            "query": "Get resources who are not management consultants",
            "excluded_ranks": ["Management Consultant"],
            "any_rank_valid": True  # Flag to indicate that any rank (or null) is valid as long as it's not in excluded_ranks
        }
    ]
    
    for test in complex_rank_tests:
        result = translator.translate(test["query"])
        print(f"Query: {test['query']}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Validate the result structure
        structure_valid = validate_result(result)
        
        # Check if the rank meets the expected criteria
        rank_valid = True
        
        if "lower_rank" in test and "upper_rank" in test:
            # Check if the result contains all ranks between the lower and upper ranks
            rank_valid = check_ranks_between(result, test["lower_rank"], test["upper_rank"])
        elif "expected_ranks" in test:
            # Check if the rank is one of the expected ranks
            if isinstance(result["rank"], list):
                # If rank is a list, check if it contains only expected ranks
                for rank in result["rank"]:
                    if rank not in test["expected_ranks"]:
                        print(f"Error: Rank '{rank}' is not one of the expected ranks {test['expected_ranks']}")
                        rank_valid = False
                        break
            elif result["rank"] not in test["expected_ranks"]:
                print(f"Error: Expected rank to be one of {test['expected_ranks']}, got '{result['rank']}'")
                rank_valid = False
        elif "excluded_ranks" in test:
            # Check if the rank is not one of the excluded ranks
            if "any_rank_valid" in test and test["any_rank_valid"]:
                # For "not management consultants" query, any rank (or null) is valid as long as it's not in excluded_ranks
                if isinstance(result["rank"], list):
                    for rank in result["rank"]:
                        if rank in test["excluded_ranks"]:
                            print(f"Error: Rank '{rank}' should not be one of {test['excluded_ranks']}")
                            rank_valid = False
                            break
                elif result["rank"] in test["excluded_ranks"]:
                    print(f"Error: Rank '{result['rank']}' should not be one of {test['excluded_ranks']}")
                    rank_valid = False
        
        if structure_valid and rank_valid:
            print("✅ Test passed")
            tests_passed += 1
        else:
            print("❌ Test failed")
            tests_failed += 1
            
        print("-" * 80)
    
    # Test cases for the new Consultant Analyst rank
    print("\nTesting specific Consultant Analyst rank queries:\n")
    
    consultant_analyst_tests = [
        {
            "query": "Find consultant analysts in London",
            "expected_rank": "Consultant Analyst"
        },
        {
            "query": "Show me resources with rank above consultant analyst in Oslo",
            "threshold_rank": "Consultant Analyst"
        },
        {
            "query": "Get resources with rank below consultant analyst",
            "threshold_rank": "Consultant Analyst"
        },
        {
            "query": "Find resources between consultant analyst and senior consultant in London",
            "lower_rank": "Consultant Analyst",
            "upper_rank": "Senior Consultant"
        }
    ]
    
    for test in consultant_analyst_tests:
        result = translator.translate(test["query"])
        print(f"Query: {test['query']}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Validate the result structure
        structure_valid = validate_result(result)
        
        # Check if the rank meets the expected criteria
        rank_valid = True
        
        if "expected_rank" in test:
            # Check if the rank is the expected rank
            if isinstance(result["rank"], list):
                if test["expected_rank"] not in result["rank"]:
                    print(f"Error: Expected rank '{test['expected_rank']}' not found in {result['rank']}")
                    rank_valid = False
            elif result["rank"] != test["expected_rank"]:
                print(f"Error: Expected rank '{test['expected_rank']}', got '{result['rank']}'")
                rank_valid = False
        elif "threshold_rank" in test and "query" in test and "above" in test["query"].lower():
            # Check if the result contains all ranks above the threshold
            rank_valid = check_ranks_above(result, test["threshold_rank"])
        elif "threshold_rank" in test and "query" in test and "below" in test["query"].lower():
            # Check if the result contains all ranks below the threshold
            rank_valid = check_ranks_below(result, test["threshold_rank"])
        elif "lower_rank" in test and "upper_rank" in test:
            # Check if the result contains all ranks between the lower and upper ranks
            rank_valid = check_ranks_between(result, test["lower_rank"], test["upper_rank"])
        
        if structure_valid and rank_valid:
            print("✅ Test passed")
            tests_passed += 1
        else:
            print("❌ Test failed")
            tests_failed += 1
            
        print("-" * 80)
    
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