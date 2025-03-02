"""
Test script to verify connection to the real Firebase database.
"""

import os
import time
from dotenv import load_dotenv
from src.firebase_utils import FirebaseClient

# Load environment variables
load_dotenv()

print("Testing connection to real Firebase")
print("==================================")

# Get Firebase credentials path from environment variable
firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
print(f"Firebase credentials path from env: {firebase_creds_path or 'Not set'}")

# Initialize the Firebase client with the credentials path
firebase_client = FirebaseClient(credentials_path=firebase_creds_path)

# Check connection status
if firebase_client.is_connected:
    print("✅ Successfully connected to Firebase!")
    print(f"App: {firebase_client.app}")
    print(f"DB: {firebase_client.db}")
else:
    print("❌ Failed to connect to Firebase.")
    print(f"Demo mode: {firebase_client.is_demo_mode}")

# Try a simple query to test the connection
try:
    print("\nTesting query with no filters:")
    results = firebase_client.get_resources(locations=[], skills=[], ranks=[])
    print(f"Query returned {len(results)} resources")
    
    # Print a few resources to verify
    for i, resource in enumerate(results[:3]):
        print(f"Resource {i+1}: {resource.get('name', 'Unknown')} - {resource.get('rank', 'Unknown')} in {resource.get('location', 'Unknown')}")
    
    if len(results) > 3:
        print(f"...and {len(results) - 3} more resources")
        
    # Test query with filters
    print("\nTesting query with filters:")
    filtered_results = firebase_client.get_resources(
        locations=["Manchester"],
        skills=[],
        ranks=["Partner"]
    )
    print(f"Query for Partners in Manchester returned {len(filtered_results)} resources")
    
    # Print filtered resources
    for i, resource in enumerate(filtered_results):
        print(f"Resource {i+1}: {resource.get('name', 'Unknown')} - {resource.get('rank', 'Unknown')} in {resource.get('location', 'Unknown')}")
        print(f"  Skills: {', '.join(resource.get('skills', []))}")
        print(f"  Availability: {resource.get('availability', 'Unknown')}")
        
    # Try different filter combinations
    print("\nTesting additional filter combinations:")
    
    # London resources
    london_results = firebase_client.get_resources(
        locations=["London"],
        skills=[],
        ranks=[]
    )
    print(f"Resources in London: {len(london_results)}")
    
    # Python skills
    python_results = firebase_client.get_resources(
        locations=[],
        skills=["Python"],
        ranks=[]
    )
    print(f"Resources with Python skills: {len(python_results)}")
    
    # Consultants
    consultant_results = firebase_client.get_resources(
        locations=[],
        skills=[],
        ranks=["Consultant"]
    )
    print(f"Consultants: {len(consultant_results)}")
    
except Exception as e:
    print(f"❌ Error during test query: {e}")

print("\nTest completed") 