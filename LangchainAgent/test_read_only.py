"""
Read-only test script to verify connection to the real Firebase database.
This script will NOT modify any data in the database.
"""

import os
from dotenv import load_dotenv
from src.firebase_utils import FirebaseClient

# Load environment variables
load_dotenv()

print("TESTING FIREBASE CONNECTION (READ-ONLY)")
print("======================================")
print("⚠️ This script will NOT modify any data in the database")

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

# Try a simple query to count records without modifying anything
try:
    # Determine which collection to use (resources or employees)
    collection_name = 'resources'
    
    try:
        # Check if 'resources' collection exists
        resources_docs = list(firebase_client.db.collection(collection_name).limit(1).get())
        if not resources_docs:
            # If no documents, try the employees collection
            collection_name = 'employees'
            print(f"No documents found in 'resources', trying '{collection_name}' collection")
    except Exception:
        # Fall back to 'employees' collection
        collection_name = 'employees'
        print(f"Falling back to '{collection_name}' collection")
    
    # Count total records (without retrieving all data)
    count_query = firebase_client.db.collection(collection_name).limit(1000).count()
    count_result = count_query.get()
    total_count = count_result[0][0].value
    
    print(f"✅ Total records in '{collection_name}' collection: {total_count}")
    
    # Count resources by location (just summary data, not retrieving documents)
    print("\nLocation breakdown (sample, limited to first 20 records):")
    locations = {}
    location_docs = list(firebase_client.db.collection(collection_name).limit(20).get())
    
    for doc in location_docs:
        resource = doc.to_dict()
        location = resource.get('location', 'Unknown')
        locations[location] = locations.get(location, 0) + 1
    
    for location, count in locations.items():
        print(f"- {location}: {count} records (sample)")
    
    # Count resources by rank (just summary data, not retrieving documents)
    print("\nRank breakdown (sample, limited to first 20 records):")
    ranks = {}
    rank_docs = list(firebase_client.db.collection(collection_name).limit(20).get())
    
    for doc in rank_docs:
        resource = doc.to_dict()
        rank = resource.get('rank', 'Unknown')
        ranks[rank] = ranks.get(rank, 0) + 1
    
    for rank, count in ranks.items():
        print(f"- {rank}: {count} records (sample)")
    
except Exception as e:
    print(f"❌ Error during test query: {e}")

print("\nRead-only test completed. No data was modified.") 