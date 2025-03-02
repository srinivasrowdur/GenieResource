"""
Script to populate the Firebase database with sample resources.
"""

import os
from dotenv import load_dotenv
from src.firebase_utils import FirebaseClient

# Load environment variables
load_dotenv()

print("Populating Firebase database with sample resources")
print("=================================================")

# Get Firebase credentials path from environment variable
firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
print(f"Firebase credentials path from env: {firebase_creds_path or 'Not set'}")

# Initialize the Firebase client with the credentials path
firebase_client = FirebaseClient(credentials_path=firebase_creds_path)

# Check connection status
if not firebase_client.is_connected:
    print("❌ Failed to connect to Firebase. Cannot populate database.")
    exit(1)

print("✅ Successfully connected to Firebase!")

# Sample resources to add to the database
sample_resources = [
    {
        "name": "John Smith",
        "location": "London",
        "skills": ["Python", "JavaScript", "Cloud"],
        "rank": "Senior Consultant",
        "availability": "Available"
    },
    {
        "name": "Sarah Johnson",
        "location": "Manchester",
        "skills": ["Java", "DevOps", "AI"],
        "rank": "Consultant",
        "availability": "Available Next Month"
    },
    {
        "name": "David Williams",
        "location": "Edinburgh",
        "skills": ["Python", "ML", "Frontend"],
        "rank": "Manager",
        "availability": "Available"
    },
    {
        "name": "Emily Brown",
        "location": "London",
        "skills": ["JavaScript", "Frontend", "UX"],
        "rank": "Analyst",
        "availability": "Available"
    },
    {
        "name": "Michael Taylor",
        "location": "Manchester",
        "skills": ["Java", "Backend", "Cloud"],
        "rank": "Principal Consultant",
        "availability": "Available"
    },
    {
        "name": "Richard Johnson",
        "location": "Manchester",
        "skills": ["Strategy", "Leadership", "Finance"],
        "rank": "Partner",
        "availability": "Limited Availability"
    }
]

# Determine which collection to use
collection_name = 'resources'

try:
    # Check if 'resources' collection exists and is accessible
    firebase_client.db.collection(collection_name).limit(1).get()
    print(f"Using '{collection_name}' collection")
except Exception:
    # Fall back to 'employees' collection
    collection_name = 'employees'
    print(f"Falling back to '{collection_name}' collection")

# Add each resource to the database
for resource in sample_resources:
    try:
        # Add the resource to the collection
        doc_ref = firebase_client.db.collection(collection_name).add(resource)
        
        # Get the document ID
        doc_id = doc_ref[1].id
        
        print(f"✅ Added {resource['name']} ({resource['rank']}) with ID: {doc_id}")
    except Exception as e:
        print(f"❌ Error adding {resource['name']}: {e}")

print("\nDatabase population completed!") 