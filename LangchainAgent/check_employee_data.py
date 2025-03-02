from src.firebase_utils import FirebaseClient

def main():
    # Initialize Firebase client
    client = FirebaseClient()
    
    print("Checking employee data structure...")
    
    # Get a few employee records
    employees = client.client.collection('employees').limit(5).get()
    
    print(f"Found {len(list(employees))} sample employees")
    
    # Examine each employee's data structure
    for emp in employees:
        data = emp.to_dict()
        employee_id = emp.id
        name = data.get('name', 'Unknown')
        location = data.get('location', 'Unknown')
        rank = data.get('rank')
        
        print(f"\nEmployee ID: {employee_id}")
        print(f"Name: {name}")
        print(f"Location: {location}")
        print(f"Rank (raw): {rank}")
        print(f"Rank type: {type(rank)}")
        
        if isinstance(rank, dict):
            print("Rank fields:")
            for key, value in rank.items():
                print(f"  - {key}: {value}")
    
    # Try a specific query for Partners in London
    print("\nTesting query for Partners in London...")
    partners_query = (client.client.collection('employees')
                     .where('location', '==', 'London')
                     .where('rank.official_name', '==', 'Partner')
                     .limit(5))
    
    partners = partners_query.get()
    partners_count = len(list(partners))
    print(f"Found {partners_count} partners in London")
    
    # Check if any Partners exist anywhere
    print("\nChecking for any Partners...")
    all_partners_query = (client.client.collection('employees')
                         .where('rank.official_name', '==', 'Partner')
                         .limit(5))
    
    all_partners = all_partners_query.get()
    all_partners_count = len(list(all_partners))
    print(f"Found {all_partners_count} partners in total")
    
    if all_partners_count > 0:
        print("\nSample Partner data:")
        for partner in all_partners:
            data = partner.to_dict()
            print(f"Name: {data.get('name', 'Unknown')}")
            print(f"Location: {data.get('location', 'Unknown')}")
            print(f"Rank: {data.get('rank')}")
    
    # Check if any employees exist in London
    print("\nChecking for any employees in London...")
    london_query = (client.client.collection('employees')
                   .where('location', '==', 'London')
                   .limit(5))
    
    london_employees = london_query.get()
    london_count = len(list(london_employees))
    print(f"Found {london_count} employees in London")
    
    if london_count > 0:
        print("\nSample London employee data:")
        for emp in london_employees:
            data = emp.to_dict()
            print(f"Name: {data.get('name', 'Unknown')}")
            print(f"Rank: {data.get('rank')}")

if __name__ == "__main__":
    main() 