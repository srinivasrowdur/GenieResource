#!/usr/bin/env python
import os
import random
import json
from dotenv import load_dotenv
from collections import Counter
import pandas as pd
from src.firebase_utils import FirebaseClient

def initialize_firebase():
    """Initialize Firebase client"""
    try:
        firebase_client = FirebaseClient()
        print("Firebase initialized successfully.")
        return firebase_client
    except Exception as e:
        print(f"Error initializing Firebase: {str(e)}")
        return None

def create_sample_resources(db, count=20):
    """
    Create sample employee documents in the 'employees' collection
    and their availability data in the 'availability' collection.
    
    Args:
        db: Initialized Firebase client
        count: Number of employee resources to create
    
    Returns:
        List of created employee resources
    """
    # Define possible values for fields
    locations = ["London", "Manchester", "Edinburgh", "Dublin", "Glasgow", "Leeds", "Bristol", "Birmingham"]
    
    ranks = [
        {"official_name": "Partner", "level": 7},
        {"official_name": "Associate Partner", "level": 6},
        {"official_name": "Consulting Director", "level": 6},
        {"official_name": "Management Consultant", "level": 5},
        {"official_name": "Principal Consultant", "level": 4},
        {"official_name": "Senior Consultant", "level": 3},
        {"official_name": "Consultant", "level": 2},
        {"official_name": "Analyst", "level": 1}
    ]
    
    skills_pool = [
        "python", "java", "javascript", "react", "angular", "vue", 
        "node.js", "aws", "azure", "gcp", "docker", "kubernetes",
        "machine learning", "data science", "natural language processing",
        "frontend", "backend", "fullstack", "devops", "project management",
        "agile", "scrum", "product management", "ux design", "ui design",
        "database", "sql", "nosql", "mongodb", "postgresql", "oracle",
        "cybersecurity", "blockchain", "cloud architecture", "microservices",
        "api design", "mobile development", "ios", "android", "flutter"
    ]
    
    statuses = ["available", "partial", "unavailable"]
    
    created_resources = []
    employee_numbers = []
    
    # Delete all existing employees and availability documents
    try:
        # Delete employees
        employees_ref = db.db.collection('employees')
        employees = employees_ref.get()
        for employee in employees:
            employee.reference.delete()
            
        # Delete availability
        availability_ref = db.db.collection('availability')
        availability_docs = availability_ref.get()
        for doc in availability_docs:
            weeks_subcoll = doc.reference.collection('weeks')
            weeks = weeks_subcoll.get()
            for week in weeks:
                week.reference.delete()
            doc.reference.delete()
            
        print(f"Deleted existing employees and availability data")
    except Exception as e:
        print(f"Error clearing existing data: {str(e)}")
    
    # Create new employees
    for i in range(count):
        employee_number = f"EMP{i+1000}"
        employee_numbers.append(employee_number)
        
        # Create random employee data
        employee = {
            "name": f"Employee {i+1}",
            "employee_number": employee_number,
            "location": random.choice(locations),
            "rank": random.choice(ranks),
            "skills": random.sample(skills_pool, random.randint(3, 7))
        }
        
        # Add employee to Firestore
        try:
            db.db.collection('employees').document(employee_number).set(employee)
            created_resources.append(employee)
        except Exception as e:
            print(f"Error adding employee {employee_number}: {str(e)}")
    
    # Create availability data for each employee
    for employee_number in employee_numbers:
        # Create availability document
        availability_ref = db.db.collection('availability').document(employee_number)
        availability_ref.set({})  # Create empty document
        
        # Create 4 weeks of availability data
        for week in range(1, 5):
            status = random.choice(statuses)
            hours = 0
            if status == "available":
                hours = 40
            elif status == "partial":
                hours = random.choice([10, 15, 20, 25, 30])
            
            week_data = {
                "week_number": week,
                "status": status,
                "hours": hours,
                "notes": f"Week {week} - {status.capitalize()}"
            }
            
            # Add availability data to weeks subcollection
            try:
                availability_ref.collection('weeks').document(f"week{week}").set(week_data)
            except Exception as e:
                print(f"Error adding availability for {employee_number}, week {week}: {str(e)}")
    
    print(f"Successfully created {len(created_resources)} employees with availability data")
    
    # Print some sample resources for debugging
    if created_resources:
        print("\nSample employees:")
        for i in range(min(3, len(created_resources))):
            print(json.dumps(created_resources[i], indent=2))
    
    # Print distribution statistics
    employee_locations = Counter([r['location'] for r in created_resources])
    print("\nLocation distribution:")
    for location, count in employee_locations.items():
        print(f"{location}: {count} employees")
    
    employee_ranks = Counter([r['rank']['official_name'] for r in created_resources])
    print("\nRank distribution:")
    for rank, count in employee_ranks.items():
        print(f"{rank}: {count} employees")
    
    return created_resources

def main():
    """Main function to set up Firebase and create sample resources"""
    load_dotenv()  # Load environment variables from .env file
    
    # Parse command-line arguments
    import sys
    auto_confirm = False
    default_count = 20
    
    if len(sys.argv) > 1:
        try:
            default_count = int(sys.argv[1])
            auto_confirm = True
        except ValueError:
            if sys.argv[1].lower() == 'y':
                auto_confirm = True
    
    # Initialize Firebase
    db = initialize_firebase()
    if not db:
        print("Failed to initialize Firebase. Exiting.")
        return
    
    # Check if employees already exist
    try:
        verification = db.verify_firebase_setup()
        if verification['employees_exist']:
            print(f"Found {verification['employee_count']} existing employees in the database.")
            if not auto_confirm:
                create_new = input("Do you want to delete existing data and create new sample employees? (y/n): ")
                if create_new.lower() != 'y':
                    print("Exiting without making changes.")
                    return
        else:
            print("No existing employees found in the database.")
    except Exception as e:
        print(f"Error checking existing data: {str(e)}")
    
    # Ask for the number of employees to create if not specified via command line
    count = default_count
    if not auto_confirm:
        try:
            count_input = input(f"How many employees do you want to create? (default: {default_count}): ")
            if count_input.strip():
                count = int(count_input)
        except ValueError:
            print(f"Invalid input. Using default count of {default_count} employees.")
    
    print(f"Creating {count} employees...")
    
    # Create sample resources
    create_sample_resources(db, count)
    
    print("\nFirebase database has been populated with sample employees and availability data.")
    print("You can now run the application to query this data.")

if __name__ == "__main__":
    main() 