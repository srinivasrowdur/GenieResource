"""
Simple test script for the LangGraph Agent.

This script tests the agent with minimal dependencies.
"""

import os
import json
import time
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from src.langgraph_agent import ReActAgentGraph

# Load environment variables
load_dotenv()

print("Simple LangGraph Agent Test")
print("==========================")

# Set up the model with the API key
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ ANTHROPIC_API_KEY not found in environment variables")
    exit(1)

model = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    anthropic_api_key=api_key,
    temperature=0
)

print("✅ Model initialized")

# Create a simple agent without Firebase
agent = ReActAgentGraph(
    model=model,
    firebase_client=None,  # No Firebase
    use_cache=True,
    verbose=True
)

print("✅ Agent initialized")

# Test query
query = "What can you help me with?"

print(f"\nSending query: '{query}'")
start_time = time.time()

try:
    result = agent.process_message(query)
    elapsed = time.time() - start_time
    
    print(f"✅ Response received in {elapsed:.2f} seconds")
    print("\nResponse:")
    print("=========")
    print(result["response"])
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\nTest completed") 