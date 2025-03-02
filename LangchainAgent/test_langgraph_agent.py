"""
Test script for the LangGraph Agent implementation.

This script provides a simple way to test the LangGraph agent without the Streamlit UI.
"""

import os
import time
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from src.langgraph_agent import ReActAgentGraph
from src.firebase_utils import FirebaseClient

# Load environment variables
load_dotenv()

# Get API keys and credentials paths
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

print("Starting LangGraph agent test...")

# Initialize Firebase client
firebase_client = None
if firebase_creds_path:
    try:
        firebase_client = FirebaseClient(credentials_path=firebase_creds_path)
        if firebase_client.is_connected:
            print("✅ Firebase connection successful!")
        else:
            print("⚠️ Firebase connection failed, running in demo mode.")
    except Exception as e:
        print(f"❌ Error initializing Firebase: {e}")
        firebase_client = None
else:
    print("⚠️ No Firebase credentials path provided, running in demo mode.")

# Initialize the model
if anthropic_api_key:
    try:
        model = ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            anthropic_api_key=anthropic_api_key,
            temperature=0
        )
        print("✅ Model initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing model: {e}")
        exit(1)
else:
    print("❌ No Anthropic API key provided. Exiting.")
    exit(1)

# Initialize the agent
try:
    agent = ReActAgentGraph(
        model=model, 
        firebase_client=firebase_client,
        use_cache=True,
        cache_ttl=3600,
        verbose=True
    )
    print("✅ Agent initialized successfully!")
except Exception as e:
    print(f"❌ Error initializing agent: {e}")
    exit(1)

# Test queries
test_queries = [
    "Find Python developers in London",
    "Are there any frontend developers in Manchester?",
    "Show me senior consultants with Java skills"
]

# Process each query and measure performance
for idx, query in enumerate(test_queries):
    print(f"\n🔄 Testing query {idx+1}/{len(test_queries)}: '{query}'")
    
    start_time = time.time()
    
    try:
        # Process the query
        result = agent.process_message(query)
        
        # Check if it was cached
        if result.get("cached", False):
            print(f"⚡ Response served from cache ({time.time() - start_time:.2f}s)")
        else:
            print(f"⏱️ Response generated in {result.get('execution_time', 0):.2f}s")
        
        # Print the response
        print(f"\nResponse:\n{result['response']}\n")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error processing query: {e}")

# Test cache stats
cache_stats = agent.get_cache_stats()
print("\n📊 Cache Statistics:")
print(f"Hits: {cache_stats['hits']}")
print(f"Misses: {cache_stats['misses']}")
print(f"Hit Rate: {cache_stats['hit_rate']:.1%}")
print(f"Cache Size: {cache_stats['size']}")

# Run the same query again to test caching
if test_queries:
    print("\n🔄 Testing cache with first query again...")
    start_time = time.time()
    result = agent.process_message(test_queries[0])
    elapsed = time.time() - start_time
    
    if result.get("cached", False):
        print(f"✅ Cache working properly! Response served in {elapsed:.2f}s")
    else:
        print(f"❌ Cache not working as expected. Response generated in {elapsed:.2f}s")

print("\n✅ LangGraph agent test completed!") 