"""
Test script for querying "Partners in Manchester"
"""

import os
import time
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from src.langgraph_agent import ReActAgentGraph
from src.firebase_utils import FirebaseClient

# Load environment variables
load_dotenv()

print("Testing: Partners in Manchester")
print("==========================")

# Set up the model with the API key
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("❌ ANTHROPIC_API_KEY not found in environment variables")
    exit(1)

# Initialize model
model = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    anthropic_api_key=api_key,
    temperature=0
)

print("✅ Model initialized")

# Initialize Firebase client
firebase_client = FirebaseClient()
if firebase_client.is_connected:
    print("✅ Firebase connected")
else:
    print("⚠️ Using demo mode")

# Create agent
agent = ReActAgentGraph(
    model=model,
    firebase_client=firebase_client,
    use_cache=True,
    verbose=True
)

print("✅ Agent initialized")

# Specific test query
query = "Partners in Manchester"

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