#!/usr/bin/env python
"""
Script to initialize the 'queries' collection in Firebase Firestore.
This will set up the collection and add some sample data for testing.
"""

import os
import sys
import json
import datetime
from dotenv import load_dotenv
from src.firebase_utils import FirebaseClient
import uuid

# Load environment variables
load_dotenv()

def initialize_queries_collection():
    """Initialize the queries collection in Firestore."""
    print("🔄 Initializing 'queries' collection in Firebase...")
    
    try:
        # Connect to Firebase
        firebase_client = FirebaseClient()
        
        if not firebase_client.is_connected:
            print("❌ Failed to connect to Firebase")
            return False
        
        # Check if queries collection already exists
        queries_ref = firebase_client.client.collection('queries')
        sample_query = list(queries_ref.limit(1).stream())
        
        if sample_query:
            print("✅ 'queries' collection already exists")
            print(f"   Collection has {len(list(queries_ref.stream()))} documents")
            
            if input("Do you want to add sample data anyway? (y/n): ").lower() != 'y':
                print("Operation canceled by user.")
                return True
        
        # Add sample data
        sample_queries = [
            {
                "query": "Find frontend developers in London",
                "response": "I found 3 frontend developers in London who match your criteria...",
                "timestamp": datetime.datetime.now(),
                "tags": ["frontend", "london", "search"],
                "metadata": {
                    "ranks": [],
                    "locations": ["London"],
                    "skills": ["frontend"],
                    "availability": {
                        "weeks": [],
                        "status": []
                    }
                },
                "session_id": str(uuid.uuid4())
            },
            {
                "query": "Who are the consultants available in Week 3?",
                "response": "Here are the consultants available in Week 3...",
                "timestamp": datetime.datetime.now(),
                "tags": ["consultant", "availability", "week3"],
                "metadata": {
                    "ranks": ["Consultant"],
                    "locations": [],
                    "skills": [],
                    "availability": {
                        "weeks": [3],
                        "status": ["available"]
                    }
                },
                "session_id": str(uuid.uuid4())
            },
            {
                "query": "Show me Solution Architects with Python skills",
                "response": "I found the following Solution Architects with Python skills...",
                "timestamp": datetime.datetime.now(),
                "tags": ["solution architect", "python", "skills"],
                "metadata": {
                    "ranks": ["Solution Architect"],
                    "locations": [],
                    "skills": ["python"],
                    "availability": {
                        "weeks": [],
                        "status": []
                    }
                },
                "session_id": str(uuid.uuid4())
            }
        ]
        
        # Add sample data to Firestore
        for sample in sample_queries:
            doc_ref = firebase_client.client.collection('queries').document()
            doc_ref.set(sample)
            print(f"✅ Added sample query: '{sample['query']}'")
        
        print("\n✅ 'queries' collection initialization complete")
        print(f"Added {len(sample_queries)} sample documents")
        
        # Create indexes if needed (for complex queries)
        print("\nℹ️ Note: If you plan to run complex queries on this collection,")
        print("   you may need to create custom indexes in the Firebase console.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing queries collection: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Resource Genie: Queries Collection Setup ===\n")
    
    success = initialize_queries_collection()
    
    if success:
        print("\n🎉 Setup completed successfully!")
    else:
        print("\n❌ Setup failed. Please check the error messages above.")
        sys.exit(1) 