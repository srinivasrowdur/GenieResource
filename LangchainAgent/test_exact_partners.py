"""
Test script to find exact Partners (not Associate Partners) in Manchester.
This script will NOT modify any data in the database.
"""

import os
from dotenv import load_dotenv
from src.firebase_utils import FirebaseClient

# Load environment variables
load_dotenv()

print("TESTING EXACT PARTNER SEARCH (READ-ONLY)")
print("======================================")
print("⚠️ This script will NOT modify any data in the database")

# Initialize the Firebase client
firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
firebase_client = FirebaseClient(credentials_path=firebase_creds_path)

# Verify connection
if not firebase_client.is_connected:
    print("❌ Failed to connect to Firebase. Cannot examine data.")
    exit(1)

print("✅ Successfully connected to Firebase!")

# Test query with exact "Partner" rank
try:
    # Get resources with exact "Partner" rank in Manchester
    results = firebase_client.get_resources(
        locations=["Manchester"],
        skills=[],
        ranks=["Partner"],
        collection='employees',
        nested_ranks=True
    )
    
    print(f"\nFound {len(results)} exact Partners in Manchester")
    
    # Display the results
    if results:
        print("\nPartners in Manchester:")
        for i, resource in enumerate(results):
            name = resource.get('name', 'Unknown')
            rank_obj = resource.get('rank', {})
            rank_name = rank_obj.get('official_name', 'Unknown') if isinstance(rank_obj, dict) else rank_obj
            level = rank_obj.get('level', 'Unknown') if isinstance(rank_obj, dict) else 'N/A'
            
            print(f"{i+1}. {name} - {rank_name} (Level {level})")
            
            # Show skills if available
            skills = resource.get('skills', [])
            if skills:
                print(f"   Skills: {', '.join(skills) if isinstance(skills, list) else skills}")
    else:
        print("No exact Partners found in Manchester")
    
    # For comparison, also search for Associate Partners
    assoc_results = firebase_client.get_resources(
        locations=["Manchester"],
        skills=[],
        ranks=["Associate Partner"],
        collection='employees',
        nested_ranks=True
    )
    
    print(f"\nFound {len(assoc_results)} Associate Partners in Manchester")
    
    if assoc_results:
        print("\nAssociate Partners in Manchester:")
        for i, resource in enumerate(assoc_results):
            name = resource.get('name', 'Unknown')
            rank_obj = resource.get('rank', {})
            rank_name = rank_obj.get('official_name', 'Unknown') if isinstance(rank_obj, dict) else rank_obj
            level = rank_obj.get('level', 'Unknown') if isinstance(rank_obj, dict) else 'N/A'
            
            print(f"{i+1}. {name} - {rank_name} (Level {level})")
            
            # Show skills if available
            skills = resource.get('skills', [])
            if skills:
                print(f"   Skills: {', '.join(skills) if isinstance(skills, list) else skills}")
    
except Exception as e:
    print(f"❌ Error querying data: {e}")

print("\nTest completed. No data was modified.") 