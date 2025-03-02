#!/usr/bin/env python
from src.firebase_utils import FirebaseClient

def main():
    print("Connecting to Firebase...")
    client = FirebaseClient()
    
    # Check if there are employees
    print("\nChecking for employees...")
    employees = client.client.collection('employees').limit(5).get()
    employee_list = list(employees)
    print(f"Found {len(employee_list)} employees")
    
    # Print details of each employee
    for doc in employee_list:
        emp = doc.to_dict()
        print(f"\nEmployee: {emp.get('name')}")
        print(f"Employee Number: {emp.get('employee_number')}")
        print(f"Location: {emp.get('location')}")
        print(f"Skills: {emp.get('skills', [])}")
        print(f"Rank: {emp.get('rank', {}).get('official_name') if emp.get('rank') else 'Unknown'}")
    
    # Check if there are any employees in London
    print("\nChecking for employees in London...")
    london_employees = client.client.collection('employees').where('location', '==', 'London').get()
    london_list = list(london_employees)
    print(f"Found {len(london_list)} employees in London")
    
    # Check for employees with frontend-related skills using different potential variations
    print("\nChecking for employees with frontend-related skills...")
    frontend_variations = ['frontend', 'front-end', 'front end', 'frontend developer', 'ui developer', 'front-end developer']
    
    all_employees = client.client.collection('employees').get()
    frontend_employees = []
    
    for doc in all_employees:
        emp = doc.to_dict()
        skills = [s.lower() for s in emp.get('skills', [])]
        
        # Check if any of the skill variations is in the skills list
        matched_skills = []
        for variation in frontend_variations:
            for skill in skills:
                if variation in skill:
                    matched_skills.append(skill)
        
        if matched_skills:
            emp['matched_skills'] = matched_skills
            frontend_employees.append(emp)
    
    print(f"Found {len(frontend_employees)} employees with frontend-related skills")
    
    # Print details of employees with frontend skills
    for emp in frontend_employees:
        print(f"\nEmployee: {emp.get('name')}")
        print(f"Location: {emp.get('location')}")
        print(f"Skills: {emp.get('skills', [])}")
        print(f"Matched skills: {emp.get('matched_skills', [])}")
    
    # Check specifically for employees in London with frontend-related skills
    print("\nChecking for employees in London with frontend-related skills...")
    london_frontend_employees = [emp for emp in frontend_employees if emp.get('location') == 'London']
    print(f"Found {len(london_frontend_employees)} employees in London with frontend-related skills")
    
    for emp in london_frontend_employees:
        print(f"\nEmployee: {emp.get('name')}")
        print(f"Location: {emp.get('location')}")
        print(f"Skills: {emp.get('skills', [])}")
        print(f"Matched skills: {emp.get('matched_skills', [])}")

if __name__ == "__main__":
    main() 