"""
Performance testing script for the LangGraph implementation.
"""

import time
import os
import sys
import statistics
import argparse
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Add parent directory to path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import ReActAgent
from src.firebase_utils import FirebaseClient
from langchain_anthropic import ChatAnthropic

# Load environment variables
load_dotenv()

# Test queries to benchmark
TEST_QUERIES = [
    "Find Python developers in London",
    "Who is available in Week 3?",
    "Show me Senior Consultants with Java skills",
    "Are there any Frontend developers in Manchester?",
    "Find resources with rank above Consultant"
]

def run_performance_test(use_firebase=False, num_runs=3, verbose=True):
    """
    Run performance tests on the LangGraph agent.
    
    Args:
        use_firebase: Whether to use real Firebase or mock it
        num_runs: Number of times to run each test
        verbose: Whether to print detailed results
        
    Returns:
        Dictionary of performance metrics
    """
    print(f"Running performance tests with {'real' if use_firebase else 'mocked'} Firebase...")
    
    # Initialize the model
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return None
    
    model = ChatAnthropic(
        model="claude-3-5-sonnet-20240620",
        anthropic_api_key=anthropic_api_key,
        temperature=0
    )
    
    # Initialize Firebase client if needed
    firebase_client = None
    if use_firebase:
        firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if not firebase_creds_path:
            print("Warning: FIREBASE_CREDENTIALS_PATH not set, using default paths")
        
        # Initialize Firebase client
        firebase_client = FirebaseClient(credentials_path=firebase_creds_path)
        
        if not firebase_client.is_connected:
            print("Warning: Firebase connection failed, falling back to mocked Firebase")
            use_firebase = False
    
    if not use_firebase:
        # Create mock Firebase client
        firebase_client = MagicMock(spec=FirebaseClient)
        firebase_client.is_connected = True
        firebase_client.get_resources.return_value = [
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
        firebase_client.get_resource_metadata.return_value = {
            "locations": ["London", "Manchester", "Edinburgh"],
            "ranks": ["Analyst", "Consultant", "Senior Consultant", "Principal Consultant", "Manager"],
            "skills": ["Python", "Java", "AI", "Frontend", "JavaScript", "React"]
        }
        firebase_client.save_query_data.return_value = True
    
    # Initialize the agent
    agent = ReActAgent(model=model, firebase_client=firebase_client)
    
    # Dictionary to store results
    results = {
        "setup_time": 0,
        "query_times": [],
        "average_time": 0,
        "min_time": 0,
        "max_time": 0,
        "std_dev": 0,
        "successful_queries": 0,
        "total_queries": len(TEST_QUERIES) * num_runs
    }
    
    # Measure setup time
    setup_start = time.time()
    agent = ReActAgent(model=model, firebase_client=firebase_client)
    results["setup_time"] = time.time() - setup_start
    
    print(f"Setup time: {results['setup_time']:.3f} seconds")
    print(f"Running {len(TEST_QUERIES)} queries {num_runs} times each...")
    
    # Run each query multiple times
    for i, query in enumerate(TEST_QUERIES):
        print(f"\nQuery {i+1}: {query}")
        
        for run in range(num_runs):
            # Reset the agent for each run
            agent.reset()
            
            # Process the query and measure time
            start_time = time.time()
            result = agent.process_message(query)
            end_time = time.time()
            
            # Calculate time taken
            time_taken = end_time - start_time
            results["query_times"].append(time_taken)
            
            # Check if query was successful
            if result["success"]:
                results["successful_queries"] += 1
            
            if verbose:
                print(f"  Run {run+1}: {time_taken:.3f} seconds {'✓' if result['success'] else '✗'}")
    
    # Calculate statistics
    results["average_time"] = statistics.mean(results["query_times"])
    results["min_time"] = min(results["query_times"])
    results["max_time"] = max(results["query_times"])
    results["std_dev"] = statistics.stdev(results["query_times"]) if len(results["query_times"]) > 1 else 0
    
    # Print summary
    print("\nPerformance Summary:")
    print(f"Setup time: {results['setup_time']:.3f} seconds")
    print(f"Average query time: {results['average_time']:.3f} seconds")
    print(f"Min query time: {results['min_time']:.3f} seconds")
    print(f"Max query time: {results['max_time']:.3f} seconds")
    print(f"Standard deviation: {results['std_dev']:.3f} seconds")
    print(f"Success rate: {results['successful_queries']}/{results['total_queries']} " 
          f"({results['successful_queries']/results['total_queries']*100:.1f}%)")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run performance tests on the LangGraph implementation")
    parser.add_argument("--firebase", action="store_true", help="Use real Firebase instead of mocks")
    parser.add_argument("--runs", type=int, default=3, help="Number of times to run each test")
    parser.add_argument("--verbose", action="store_true", help="Print detailed results")
    args = parser.parse_args()
    
    run_performance_test(use_firebase=args.firebase, num_runs=args.runs, verbose=args.verbose) 