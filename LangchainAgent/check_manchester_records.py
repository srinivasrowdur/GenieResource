"""
Read-only script to examine the Manchester records and find out how partners are stored.
This script will NOT modify any data in the database.
"""

import os
from dotenv import load_dotenv
from src.firebase_utils import FirebaseClient

# Load environment variables
load_dotenv()

print("EXAMINING MANCHESTER RECORDS (READ-ONLY)")
print("=======================================")
print("⚠️ This script will NOT modify any data in the database")

# Initialize the Firebase client
firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
firebase_client = FirebaseClient(credentials_path=firebase_creds_path)

# Verify connection
if not firebase_client.is_connected:
    print("❌ Failed to connect to Firebase. Cannot examine data.")
    exit(1)

print("✅ Successfully connected to Firebase!")

# Query for all Manchester records
try:
    # Get all documents from employees collection where location is Manchester
    query = firebase_client.db.collection('employees').where('location', '==', 'Manchester')
    docs = query.get()
    
    print(f"\nFound {len(docs)} employees in Manchester")
    
    # First, let's see all available ranks
    print("\nExamining the rank field for Manchester employees:")
    
    # Dictionary to count different rank types
    rank_types = {}
    rank_values = {}
    
    # Examine each document
    for i, doc in enumerate(docs):
        data = doc.to_dict()
        name = data.get('name', 'Unknown')
        
        # Check how rank is stored
        rank = data.get('rank')
        rank_type = type(rank).__name__
        
        # Update counts
        rank_types[rank_type] = rank_types.get(rank_type, 0) + 1
        
        # Store actual values
        if rank_type not in rank_values:
            rank_values[rank_type] = []
        
        if rank not in rank_values[rank_type]:
            rank_values[rank_type].append(rank)
        
        print(f"\nRecord #{i+1}: {name}")
        print(f"  Rank: {rank} (Type: {rank_type})")
        
        # If rank is a dictionary, let's see what fields it has
        if rank_type == 'dict':
            print(f"  Rank fields: {list(rank.keys())}")
            print(f"  Rank values: {list(rank.values())}")
            
            # Check for common fields that might contain "partner"
            for field in ['name', 'title', 'value', 'level', 'position']:
                if field in rank and "partner" in str(rank[field]).lower():
                    print(f"  ✅ Found 'partner' in rank.{field}: {rank[field]}")
                    
        # Check for partner in any field 
        for field, value in data.items():
            if "partner" in str(value).lower() and field != 'rank':
                print(f"  🔍 Found 'partner' in field '{field}': {value}")
        
    # Print summary
    print("\nSUMMARY OF RANK FIELD TYPES:")
    for rank_type, count in rank_types.items():
        print(f"- {rank_type}: {count} records")
        if rank_values[rank_type]:
            print(f"  Values: {rank_values[rank_type][:5]}{' ...' if len(rank_values[rank_type]) > 5 else ''}")
            
    # If dictionaries are used for rank, let's analyze their structure
    if 'dict' in rank_types and rank_types['dict'] > 0:
        print("\nANALYSIS OF RANK DICTIONARY STRUCTURE:")
        
        # Fields found in rank dictionaries
        rank_fields = {}
        
        for doc in docs:
            data = doc.to_dict()
            rank = data.get('rank')
            
            if isinstance(rank, dict):
                for field in rank.keys():
                    rank_fields[field] = rank_fields.get(field, 0) + 1
        
        print("Fields found in rank dictionaries:")
        for field, count in rank_fields.items():
            print(f"- '{field}': found in {count} records")
    
    # Now let's explicitly look for anyone who might be a partner, regardless of how it's stored
    print("\nSEARCHING FOR POTENTIAL PARTNERS:")
    
    potential_partners = []
    
    for doc in docs:
        data = doc.to_dict()
        name = data.get('name', 'Unknown')
        found = False
        partner_field = None
        partner_value = None
        
        # Convert entire document to string and search for "partner"
        doc_str = str(data).lower()
        if "partner" in doc_str:
            # Look for the specific field containing "partner"
            for field, value in data.items():
                if "partner" in str(value).lower():
                    found = True
                    partner_field = field
                    partner_value = value
                    break
            
            if found:
                potential_partners.append({
                    "name": name,
                    "field": partner_field,
                    "value": partner_value
                })
    
    # Print potential partners
    if potential_partners:
        print(f"Found {len(potential_partners)} potential partners:")
        for partner in potential_partners:
            print(f"- {partner['name']}: {partner['field']} = {partner['value']}")
    else:
        print("No potential partners found in the data.")
    
except Exception as e:
    print(f"❌ Error examining data: {e}")

print("\nExamination completed. No data was modified.") 