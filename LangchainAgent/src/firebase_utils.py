"""
Firebase utility module for handling Firebase operations.
"""

import os
from typing import Optional, Dict, Any, List
from firebase_admin import credentials, initialize_app, firestore, get_app
import firebase_admin
import json
import datetime
import streamlit as st
import warnings
import uuid

class FirebaseClient:
    """
    Firebase client utility for managing Firebase operations.
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Firebase client.
        
        Args:
            credentials_path: Path to Firebase credentials JSON file.
                            If None, will try to:
                            1. Use Streamlit secrets in production
                            2. Use FIREBASE_CREDENTIALS_PATH env var
                            3. Look in common locations
        """
        self.client = None
        self.is_demo_mode = False
        self.is_connected = False
        self.app = None
        
        try:
            # Get the absolute path to the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Try different paths for credentials
            possible_paths = [
                credentials_path,  # Explicitly provided path
                os.getenv("FIREBASE_CREDENTIALS_PATH"),  # Environment variable
                os.path.join(project_root, "firebase_credentials.json"),  # Project root
                os.path.join(os.path.dirname(project_root), "firebase_credentials.json"),  # Parent directory
                os.path.join(os.path.dirname(project_root), 
                            "resgenie-e8ab5-firebase-adminsdk-fbsvc-eb9f384590.json"),  # Known filename
                "firebase_credentials.json"  # Current directory
            ]
            
            # First try to use Streamlit secrets if available (for production)
            used_streamlit_secrets = False
            cred = None
            
            # Try to get credentials from Streamlit secrets
            # Use a context manager to suppress StreamlitAPIException about missing secrets
            try:
                # Check if we're in Streamlit context before attempting to access secrets
                in_streamlit_context = False
                try:
                    # This will fail if we're not in a Streamlit script
                    _ = st.runtime.exists()
                    in_streamlit_context = True
                except:
                    pass  # Not in a Streamlit context
                
                if in_streamlit_context:
                    # Try to access secrets, suppressing warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        if hasattr(st, 'secrets') and 'firebase' in st.secrets and 'my_project_settings' in st.secrets['firebase']:
                            print("🔄 Using Streamlit secrets for Firebase configuration...")
                            firebase_config = st.secrets["firebase"]["my_project_settings"]
                            
                            # Convert config to dictionary and validate
                            config_dict = dict(firebase_config)
                            
                            # Validate required fields
                            required_fields = ["type", "project_id", "private_key_id", "private_key",
                                            "client_email", "client_id", "auth_uri", "token_uri",
                                            "auth_provider_x509_cert_url", "client_x509_cert_url"]
                            
                            if all(field in config_dict for field in required_fields):
                                print("✅ Using Firebase configuration from Streamlit secrets")
                                cred = credentials.Certificate(config_dict)
                                used_streamlit_secrets = True
                            else:
                                missing_fields = [field for field in required_fields if field not in config_dict]
                                print(f"⚠️ Missing required Firebase fields in Streamlit secrets: {', '.join(missing_fields)}")
                                print("⚠️ Falling back to file-based credentials")
            except Exception as e:
                print(f"⚠️ Unable to access Streamlit secrets: {str(e)}")
                print("⚠️ Falling back to file-based credentials")
            
            # Only look for credentials file if Streamlit secrets weren't used
            if not used_streamlit_secrets:
                print("⚠️ No Streamlit secrets found or not in a Streamlit context. Using file-based credentials.")
                # Filter out None values and check each path
                creds_path = None
                for path in filter(None, possible_paths):
                    print(f"🔍 Checking for credentials at: {path}")
                    if os.path.exists(path):
                        creds_path = path
                        print(f"✅ Found credentials at: {path}")
                        break
                
                if not creds_path:
                    raise ValueError("Firebase credentials file not found in any location and Streamlit secrets not available")
                
                # Load and validate credentials
                print(f"📖 Loading credentials from: {creds_path}")
                with open(creds_path, 'r') as f:
                    creds_data = json.load(f)
                    required_fields = ['type', 'project_id', 'private_key', 'client_email']
                    missing_fields = [field for field in required_fields if field not in creds_data]
                    if missing_fields:
                        raise ValueError(f"Missing required fields in credentials: {', '.join(missing_fields)}")
                
                cred = credentials.Certificate(creds_path)
            
            # Initialize Firebase
            print("🔄 Initializing Firebase...")
            try:
                self.app = get_app()
                print("✅ Using existing Firebase app")
            except ValueError:
                self.app = initialize_app(cred)
                print("✅ Created new Firebase app")
            
            self.client = firestore.client()
            self.is_connected = True
            print("✅ Firebase initialized successfully")
            
            # Test connection to both collections
            try:
                # Check employees collection
                self.client.collection('employees').limit(1).get()
                
                # Check availability collection
                self.client.collection('availability').limit(1).get()
                
                print("✅ Successfully connected to Firestore and verified collections")
            except Exception as e:
                raise Exception(f"Failed to connect to Firestore collections: {str(e)}")
            
        except Exception as e:
            print(f"❌ Firebase initialization failed: {str(e)}")
            # Print environment info for debugging
            print("\n🔧 Debug Information:")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Project root directory: {project_root}")
            print(f"FIREBASE_CREDENTIALS_PATH: {os.getenv('FIREBASE_CREDENTIALS_PATH')}")
            # Raise error instead of enabling demo mode
            raise Exception(f"Firebase initialization failed: {str(e)}")
    
    def query_resources(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query resources based on filters, using employees and availability collections.
        
        Args:
            filters: Dictionary of filters to apply
                    {
                        'locations': List[str],
                        'skills': List[str],
                        'ranks': List[str],
                        'weeks': List[int]
                    }
        
        Returns:
            List of matching resources
        """
        if self.is_demo_mode:
            # Since we're enforcing real Firebase connection, this should never happen
            raise ValueError("Demo mode is disabled. Real Firebase connection is required.")
        
        try:
            # Build employee filters
            employee_filters = {}
            
            # Handle location filter
            if filters.get('locations'):
                employee_filters['location_in'] = filters['locations']
            
            # Handle rank filter
            if filters.get('ranks'):
                employee_filters['rank.official_name_in'] = filters['ranks']
            
            # Handle skills filter - need special handling for array fields
            if filters.get('skills') and len(filters['skills']) > 0:
                # For multiple skills, we'll filter post-query because Firestore 
                # only supports one array-contains or array-contains-any per query
                employee_filters['skills'] = filters['skills'][0] if len(filters['skills']) == 1 else filters['skills']
            
            print(f"Debug: Querying employees with filters: {employee_filters}")
            
            # Step 1: Query employees collection
            query = self.client.collection('employees')
            
            # Apply filters optimally
            for field, value in employee_filters.items():
                if field.endswith('_in'):
                    field_name = field[:-3]  # Remove '_in' suffix
                    query = query.filter(field_name, "in", value)
                elif field == 'skills':
                    # For multiple skills, use array_contains_any if possible
                    if isinstance(value, list):
                        query = query.filter(field, "array_contains_any", 
                                          value[:10])  # Firestore limit: max 10 values
                    else:
                        query = query.filter(field, "array_contains", value)
                else:
                    query = query.filter(field, "==", value)
            
            # Execute query
            docs = list(query.stream())
            employee_results = []
            employee_numbers = []
            
            for doc in docs:
                employee = doc.to_dict()
                employee['id'] = doc.id
                
                # Post-query filter for skills if we have multiple skills
                # and we used array_contains_any for the first 10
                if filters.get('skills') and len(filters['skills']) > 1:
                    employee_skills = set(employee.get('skills', []))
                    filter_skills = set(filters['skills'])
                    # Check if the employee has any of the skills
                    if not employee_skills.intersection(filter_skills):
                        continue
                
                employee_results.append(employee)
                employee_number = employee.get('employee_number')
                if employee_number:  # Make sure employee_number exists
                    employee_numbers.append(employee_number)
            
            print(f"Debug: Found {len(employee_results)} matching employees")
            
            # Step 2: If weeks are specified, fetch availability data
            if filters.get('weeks') and employee_numbers:
                print(f"Debug: Fetching availability for {len(employee_numbers)} employees in weeks {filters['weeks']}")
                
                # Process employees in batches to avoid Firestore limitations
                batch_size = 10
                all_availability = {}
                
                for i in range(0, len(employee_numbers), batch_size):
                    batch_employees = employee_numbers[i:i + batch_size]
                    
                    for emp_num in batch_employees:
                        # Get availability document
                        avail_doc = self.client.collection('availability').document(emp_num).get()
                        if not avail_doc.exists:
                            continue
                        
                        # Get weeks subcollection
                        weeks_ref = avail_doc.reference.collection('weeks')
                        employee_availability = []
                        
                        # Convert weeks list to a set for faster lookup
                        target_weeks = set(filters['weeks']) if filters.get('weeks') else set()
                        
                        try:
                            # Get all weeks without any filtering
                            all_weeks_query = weeks_ref.stream()
                            
                            for week_doc in all_weeks_query:
                                week_data = week_doc.to_dict()
                                if not week_data:
                                    continue
                                    
                                week_num = week_data.get('week_number')
                                # Only include weeks we're interested in
                                if not target_weeks or week_num in target_weeks:
                                    employee_availability.append({
                                        'week': week_num,
                                        'status': week_data.get('status', 'Unknown'),
                                        'notes': week_data.get('notes', ''),
                                        'hours': week_data.get('hours', 0)
                                    })
                        except Exception as e:
                            print(f"Error fetching weeks for employee {emp_num}: {str(e)}")
                            continue
                        
                        # Sort the availability data by week number in memory
                        employee_availability.sort(key=lambda x: x.get('week', 0))
                        
                        # Only add to results if we found availability data
                        if employee_availability:
                            all_availability[emp_num] = employee_availability
                
                # Filter employees based on availability
                filtered_results = []
                for employee in employee_results:
                    emp_num = employee.get('employee_number')
                    if emp_num in all_availability:
                        employee['availability'] = all_availability[emp_num]
                        filtered_results.append(employee)
                
                print(f"Debug: After availability filtering, {len(filtered_results)} employees remain")
                return filtered_results
            
            return employee_results
            
        except Exception as e:
            print(f"❌ Firebase query failed: {str(e)}")
            raise ValueError(f"Firebase query failed: {str(e)}")
    
    def _fetch_availability_batch(self, employee_numbers: List[str], weeks: List[int]) -> Dict[str, List[Dict]]:
        """
        Fetch availability for multiple employees and weeks.
        
        Args:
            employee_numbers: List of employee numbers
            weeks: List of week numbers
        
        Returns:
            Dictionary mapping employee numbers to their availability data
        """
        results = {}
        print(f"Fetching availability for {len(employee_numbers)} employees in weeks {weeks}")
        
        try:
            # Convert weeks list to a set for faster lookup
            target_weeks = set(weeks) if weeks else set()
            print(f"Looking for weeks: {target_weeks}")
            
            # Process employees in batches
            for employee_number in employee_numbers:
                if not employee_number:
                    continue
                    
                # Get availability document
                avail_doc = self.client.collection('availability').document(employee_number).get()
                if not avail_doc.exists:
                    continue
                    
                # Get weeks subcollection
                weeks_ref = avail_doc.reference.collection('weeks')
                employee_availability = []
                
                try:
                    # Get all weeks without filtering
                    all_weeks_query = weeks_ref.stream()
                    
                    for week_doc in all_weeks_query:
                        week_data = week_doc.to_dict()
                        if not week_data:
                            continue
                        
                        week_num = week_data.get('week_number')
                        # Only include weeks we're interested in
                        if not target_weeks or week_num in target_weeks:
                            print(f"Found availability for employee {employee_number}, week {week_num}: {week_data.get('status', 'Unknown')}")
                            employee_availability.append({
                                'week': week_num,
                                'status': week_data.get('status', 'Unknown'),
                                'notes': week_data.get('notes', ''),
                                'hours': week_data.get('hours', 0)
                            })
                except Exception as e:
                    print(f"Error fetching weeks for employee {employee_number}: {str(e)}")
                
                # Sort the availability data by week number in memory
                employee_availability.sort(key=lambda x: x.get('week', 0))
                
                # Only add to results if we found availability data
                if employee_availability:
                    results[employee_number] = employee_availability
                    
            return results
        except Exception as e:
            print(f"Error fetching availability batch: {str(e)}")
            return {}
    
    def get_resource_by_id(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific employee by ID or employee_number.
        
        Args:
            resource_id: Either the document ID or employee_number
            
        Returns:
            Employee data with availability information if found
        """
        if self.is_demo_mode:
            raise ValueError("Demo mode is disabled. Real Firebase connection is required.")
        
        try:
            employee_data = None
            
            # First try direct document lookup by ID
            doc = self.client.collection('employees').document(resource_id).get()
            if doc.exists:
                employee_data = doc.to_dict()
                employee_data['id'] = doc.id
            else:
                # If not found, try to query by employee_number
                query = (self.client.collection('employees')
                        .filter("employee_number", "==", resource_id)
                        .limit(1))
                results = list(query.stream())
                if results:
                    doc = results[0]
                    employee_data = doc.to_dict()
                    employee_data['id'] = doc.id
            
            # If we found the employee, fetch availability data
            if employee_data:
                employee_number = employee_data.get('employee_number')
                if employee_number:
                    # Get current and next 3 weeks for availability data
                    current_week = datetime.datetime.now().isocalendar()[1]  # ISO week number
                    target_weeks = set(range(current_week, current_week + 4))
                    
                    # Get availability document
                    avail_doc = self.client.collection('availability').document(employee_number).get()
                    if avail_doc.exists:
                        # Get weeks subcollection
                        weeks_ref = avail_doc.reference.collection('weeks')
                        availability_data = []
                        
                        # Get current and next 3 weeks for availability data
                        current_week = datetime.datetime.now().isocalendar()[1]  # ISO week number
                        target_weeks = set(range(current_week, current_week + 4))
                        
                        try:
                            # Get all weeks without filtering
                            all_weeks_query = weeks_ref.stream()
                            
                            for week_doc in all_weeks_query:
                                week_data = week_doc.to_dict()
                                if not week_data:
                                    continue
                                
                                week_num = week_data.get('week_number')
                                # Only include recent weeks
                                if week_num and week_num >= current_week:
                                    availability_data.append({
                                        'week': week_num,
                                        'status': week_data.get('status', 'Unknown'),
                                        'notes': week_data.get('notes', ''),
                                        'hours': week_data.get('hours', 0)
                                    })
                        except Exception as e:
                            print(f"Error fetching weeks for employee {employee_number}: {str(e)}")
                        
                        # Sort the availability data by week number in memory
                        availability_data.sort(key=lambda x: x.get('week', 0))
                        
                        # Limit to 10 entries
                        availability_data = availability_data[:10]
                        
                        # Add availability data to employee
                        if availability_data:
                            employee_data['availability'] = availability_data
            
                return employee_data
            
            return None
        except Exception as e:
            print(f"❌ Error fetching employee: {str(e)}")
            raise ValueError(f"Firebase query failed: {str(e)}")
    
    def verify_firebase_setup(self) -> dict:
        """
        Verify Firebase connection and check database structure.
        
        Performs the following checks:
        1. Connection to Firebase
        2. Presence of 'employees' collection
        3. Presence of 'availability' collection
        4. Structure of documents in both collections
        5. Sample data retrieval
        
        Returns:
            A dictionary with verification results
        """
        verification = {
            'is_connected': self.is_connected,
            'employees_exist': False,
            'availability_exist': False,
            'employee_count': 0,
            'availability_count': 0,
            'structure_valid': False,
            'message': '',
            'employee_example': None,
            'availability_example': None
        }
        
        try:
            if not self.is_connected:
                verification['message'] = "Firebase client is not connected"
                return verification
            
            # Test querying the employees collection
            employees_query = self.client.collection('employees').limit(5)
            employee_docs = list(employees_query.stream())
            employee_count = len(employee_docs)
            verification['employee_count'] = employee_count
            
            # Check if employees exist
            if employee_count > 0:
                verification['employees_exist'] = True
                example_doc = employee_docs[0]
                example = example_doc.to_dict()
                example['id'] = example_doc.id
                verification['employee_example'] = example
                
                # Check for required fields in employee documents
                required_employee_fields = ['name', 'location', 'rank', 'skills', 'employee_number']
                missing_fields = [field for field in required_employee_fields if field not in example]
                
                if missing_fields:
                    verification['structure_valid'] = False
                    verification['message'] = f"Employee documents missing required fields: {missing_fields}"
                    return verification
            else:
                verification['message'] = "Connected to Firebase, but no employees found in the 'employees' collection"
                return verification
            
            # Check availability collection
            avail_query = self.client.collection('availability').limit(5)
            avail_docs = list(avail_query.stream())
            avail_count = len(avail_docs)
            verification['availability_count'] = avail_count
            
            if avail_count > 0:
                verification['availability_exist'] = True
                
                # Check for weeks subcollection in an availability document
                avail_example = avail_docs[0]
                verification['availability_example'] = {'id': avail_example.id}
                
                # Check if weeks subcollection exists
                weeks_subcoll = list(avail_example.reference.collection('weeks').limit(1).stream())
                if weeks_subcoll:
                    week_doc = weeks_subcoll[0]
                    week_data = week_doc.to_dict()
                    verification['availability_example']['week_example'] = week_data
                    
                    # Check for required fields in week documents
                    required_week_fields = ['week_number', 'status']
                    missing_week_fields = [field for field in required_week_fields if field not in week_data]
                    
                    if missing_week_fields:
                        verification['structure_valid'] = False
                        verification['message'] = f"Week documents missing required fields: {missing_week_fields}"
                        return verification
                    
                    verification['structure_valid'] = True
                else:
                    verification['message'] = "Availability documents exist, but no weeks subcollection found"
                    return verification
            else:
                verification['message'] = "Connected to Firebase, but no availability documents found"
                return verification
            
            # All checks passed
            verification['message'] = (
                f"Successfully connected to Firebase. Found {employee_count} employees and "
                f"{avail_count} availability documents. Database structure is valid."
            )
            
            return verification
            
        except Exception as e:
            verification['is_connected'] = False
            verification['message'] = f"Firebase verification failed: {str(e)}"
            return verification
    
    def get_resource_metadata(self) -> dict:
        """
        Fetches metadata about available resources including:
        - Locations
        - Skills
        - Ranks
        
        Returns:
            dict: Dictionary containing lists of available locations, skills, and ranks
        """
        try:
            if not self.is_connected:
                return {
                    'locations': [],
                    'skills': [],
                    'ranks': []
                }
            
            # Initialize empty sets for uniqueness
            locations = set()
            skills = set()
            ranks = set()
            
            # Get a reference to the employees collection
            employees_ref = self.client.collection('employees')
            employees = employees_ref.limit(100).stream()  # Limit to prevent large data loads
            
            # Collect metadata from employees
            for employee in employees:
                employee_data = employee.to_dict()
                
                # Extract location
                if 'location' in employee_data and employee_data['location']:
                    locations.add(employee_data['location'])
                
                # Extract skills
                if 'skills' in employee_data and isinstance(employee_data['skills'], list):
                    for skill in employee_data['skills']:
                        if skill:  # Ensure the skill is not empty
                            skills.add(skill)
                
                # Extract rank
                if 'rank' in employee_data and isinstance(employee_data['rank'], dict):
                    if 'official_name' in employee_data['rank'] and employee_data['rank']['official_name']:
                        ranks.add(employee_data['rank']['official_name'])
            
            return {
                'locations': list(locations),
                'skills': list(skills),
                'ranks': list(ranks)
            }
        
        except Exception as e:
            print(f"Error fetching resource metadata: {str(e)}")
            return {
                'locations': [],
                'skills': [],
                'ranks': []
            }
    
    def fetch_employees(self, locations=None, ranks=None, skills=None, weeks=None, availability_status=None, min_hours=None, limit=20, offset=0):
        """
        Fetch employees based on provided filters
        
        Args:
            locations (list): List of locations to filter by
            ranks (list): List of ranks to filter by
            skills (list): List of skills to filter by
            weeks (list): List of weeks to check availability for
            availability_status (list): List of availability statuses to filter by
            min_hours (int): Minimum available hours
            limit (int): Maximum number of results to return
            offset (int): Number of results to skip
            
        Returns:
            List of employee documents that match the criteria
        """
        try:
            print("\n===== FETCH_EMPLOYEES DEBUG =====")
            print(f"Input filters: locations={locations}, ranks={ranks}, skills={skills}, weeks={weeks}")
            
            # Start with the employees collection
            query = self.client.collection('employees')
            print("Base query created")
            
            # Apply location filter
            if locations and len(locations) > 0:
                print(f"Applying location filter: {locations}")
                try:
                    # Ensure locations is a list
                    if not isinstance(locations, list):
                        locations = [locations]
                    query = query.where('location', 'in', locations)
                    print("Location filter applied")
                except Exception as e:
                    print(f"Error applying location filter: {str(e)}")
                    raise ValueError(f"Invalid location filter: {str(e)}")
            
            # Apply rank filter
            if ranks and len(ranks) > 0:
                print(f"Applying rank filter: {ranks}")
                try:
                    # Ensure ranks is a list
                    if not isinstance(ranks, list):
                        ranks = [ranks]
                    
                    # Debug - log what we're searching for
                    print(f"Searching for ranks: {ranks}")
                    
                    # MODIFIED APPROACH: Get all employees first and filter by rank later
                    # This is because we may need to do special handling for "Partner" rank
                    # which might not exist in some locations.
                    # We'll do post-query filtering instead of adding a where clause 
                    # that might return zero results
                    
                    print("Using post-query rank filtering to avoid empty results")
                    
                except Exception as e:
                    print(f"Error applying rank filter: {str(e)}")
                    raise ValueError(f"Invalid rank filter: {str(e)}")
            else:
                print("No rank filter to apply")
            
            # Apply skills filter (requires array-contains-any)
            if skills and len(skills) > 0:
                print(f"Applying skills filter: {skills}")
                try:
                    # Ensure skills is a list
                    if not isinstance(skills, list):
                        skills = [skills]
                    
                    # Map common skill terms to their actual representation in the database
                    skill_mapping = {
                        'frontend': 'Frontend Developer',
                        'front-end': 'Frontend Developer',
                        'front end': 'Frontend Developer',
                        'ui': 'Frontend Developer',
                        'backend': 'Backend Developer',
                        'back-end': 'Backend Developer',
                        'back end': 'Backend Developer',
                        'fullstack': 'Full Stack Developer',
                        'full-stack': 'Full Stack Developer',
                        'full stack': 'Full Stack Developer',
                        'product': 'Product Manager',
                        'project': 'Project Manager',
                        'agile': 'Agile Coach',
                        'scrum': 'Scrum Master',
                        'data': 'Data Engineer',
                        'cloud': 'Cloud Engineer'
                    }
                    
                    # Transform skill queries to match database entries
                    transformed_skills = []
                    for skill in skills:
                        skill_lower = skill.lower()
                        if skill_lower in skill_mapping:
                            transformed_skills.append(skill_mapping[skill_lower])
                        else:
                            # If no mapping exists, leave it as is
                            transformed_skills.append(skill)
                    
                    print(f"Transformed skills: {transformed_skills}")
                    query = query.where('skills', 'array_contains_any', transformed_skills)
                    print("Skills filter applied")
                except Exception as e:
                    print(f"Error applying skills filter: {str(e)}")
                    raise ValueError(f"Invalid skills filter: {str(e)}")
            
            # Execute the query
            print("Executing Firestore query...")
            try:
                employees = query.get()
                print(f"Query executed, got {len(list(employees))} results")
            except Exception as e:
                print(f"Error executing query: {str(e)}")
                raise ValueError(f"Error executing Firestore query: {str(e)}")
            
            # Convert to list of dictionaries with document IDs
            employee_list = []
            for doc in employees:
                employee_data = doc.to_dict()
                employee_data['id'] = doc.id
                employee_list.append(employee_data)
            
            print(f"Converted {len(employee_list)} documents to dictionaries")
            
            # Additional filtering for ranks if specified
            if ranks and len(ranks) > 0:
                print(f"Applying post-query rank filtering for {len(ranks)} ranks")
                # Check each employee has one of the required ranks
                filtered_employees = []
                
                for employee in employee_list:
                    rank_data = employee.get('rank', {})
                    
                    if not rank_data:
                        continue
                        
                    official_name = rank_data.get('official_name', '')
                    
                    # Check if the employee's rank matches any of the requested ranks
                    if any(rank.lower() == official_name.lower() for rank in ranks):
                        filtered_employees.append(employee)
                
                print(f"After rank filtering: {len(filtered_employees)}/{len(employee_list)} employees remain")
                employee_list = filtered_employees
            
            # If no employees found, try a broader search for partners
            special_case_results = []
            looking_for_partner = ranks and any(r.lower() == 'partner' for r in ranks)
            
            if len(employee_list) == 0 and looking_for_partner and locations:
                print("No partners found with current location filter, trying to find any partners...")
                
                # Try a broader search just for partners regardless of location
                partner_query = self.client.collection('employees')
                partner_docs = list(partner_query.get())
                
                partner_list = []
                partner_locations = set()
                
                for doc in partner_docs:
                    employee_data = doc.to_dict()
                    rank_data = employee_data.get('rank', {})
                    
                    if rank_data and rank_data.get('official_name', '').lower() == 'partner':
                        employee_data['id'] = doc.id
                        employee_location = employee_data.get('location', 'Unknown')
                        partner_locations.add(employee_location)
                        partner_list.append(employee_data)
                
                if partner_list:
                    print(f"Found {len(partner_list)} partners in other locations")
                    print(f"Partner locations: {partner_locations}")
                    
                    # Create a special case result to inform the user
                    requested_locations = ', '.join(locations)
                    available_locations = ', '.join(partner_locations)
                    
                    # Add a special case result with information
                    special_case = {
                        'id': 'special_case_partner_info',
                        'name': 'Partner Information',
                        'special_case': True,
                        'message': f"No Partners found in {requested_locations}. Partners are available in {available_locations}."
                    }
                    
                    # Add sample partner data
                    special_case['sample_partners'] = []
                    for partner in partner_list[:3]:  # Show max 3 samples
                        special_case['sample_partners'].append({
                            'name': partner.get('name', 'Unknown'),
                            'location': partner.get('location', 'Unknown')
                        })
                    
                    special_case_results.append(special_case)
                    
                    # OPTION: We could also include the actual partners from other locations
                    # if we want to show them despite location mismatch
                    # special_case_results.extend(partner_list[:5])  # Show max 5 partners
            
            # Use special case results if we have them and no normal results
            if len(employee_list) == 0 and special_case_results:
                print(f"Using {len(special_case_results)} special case results")
                return special_case_results
            
            # Additional filtering for skills if more than one skill specified
            if skills and len(skills) > 1:
                print(f"Applying additional skills filtering for {len(skills)} skills")
                # Check each employee has all the required skills
                filtered_employees = []
                for employee in employee_list:
                    emp_skills = [s.lower() for s in employee.get('skills', [])]
                    all_skills_match = all(skill.lower() in emp_skills for skill in skills)
                    if all_skills_match:
                        filtered_employees.append(employee)
                print(f"After skills filtering: {len(filtered_employees)}/{len(employee_list)} employees remain")
                employee_list = filtered_employees
            
            # If availability criteria specified, filter by availability
            if (weeks and len(weeks) > 0) or availability_status or min_hours:
                print("Applying availability filtering")
                # Get availability data for these employees
                employee_numbers = [emp['employee_number'] for emp in employee_list if 'employee_number' in emp]
                print(f"Fetching availability for {len(employee_numbers)} employees")
                availability_data = self._fetch_availability_batch(employee_numbers, weeks or [])
                print(f"Found availability data for {len(availability_data)} employees")
                
                # Filter employees based on availability criteria
                filtered_employees = []
                for employee in employee_list:
                    emp_num = employee.get('employee_number')
                    if emp_num and emp_num in availability_data:
                        employee_availability = availability_data[emp_num]
                        
                        # Check if employee meets availability criteria
                        meets_criteria = True
                        
                        # Filter by availability status if specified
                        if availability_status and len(availability_status) > 0:
                            print(f"Checking availability status for employee {emp_num}. Looking for: {availability_status}")
                            
                            # Convert requested statuses to lowercase for case-insensitive comparison
                            lowercase_statuses = [status.lower() for status in availability_status]
                            
                            # Check if employee has the requested status in any of the requested weeks
                            has_status = False
                            
                            # Special handling: If looking for 'available', also accept 'partially available'
                            looking_for_available = 'available' in lowercase_statuses
                            accepting_partial = looking_for_available and not ('partially available' in lowercase_statuses or 'partial' in lowercase_statuses)
                            
                            if accepting_partial:
                                print(f"  👉 Special case: Also accepting 'partially available' as a match for 'available'")
                                
                            for week_data in employee_availability:
                                current_status = week_data.get('status', '').lower()
                                
                                status_matches = False
                                # Direct match
                                if current_status in lowercase_statuses:
                                    status_matches = True
                                # Special case: 'partially available' counts as 'available' if specified
                                elif accepting_partial and current_status == 'partially available':
                                    status_matches = True
                                    print(f"  👍 Accepting partially available as available")
                                
                                print(f"  Week {week_data.get('week')}: Status = '{current_status}' vs Requested = {lowercase_statuses} → {status_matches}")
                                
                                if status_matches:
                                    has_status = True
                                    print(f"  ✅ Status match found for week {week_data.get('week')}")
                                    break
                                    
                            if not has_status:
                                print(f"  ❌ No status match found for any week, employee {emp_num} filtered out")
                                meets_criteria = False
                        
                        # Filter by minimum hours if specified
                        if min_hours and meets_criteria:
                            # Check if employee has at least min_hours in all requested weeks
                            for week_data in employee_availability:
                                if week_data.get('hours', 0) < min_hours:
                                    meets_criteria = False
                                    break
                        
                        if meets_criteria:
                            # Add availability data to employee record
                            employee['availability'] = employee_availability
                            filtered_employees.append(employee)
                
                print(f"After availability filtering: {len(filtered_employees)}/{len(employee_list)} employees remain")
                employee_list = filtered_employees
            
            # Apply limit and offset
            total_employees = len(employee_list)
            start_idx = min(offset, total_employees)
            end_idx = min(start_idx + limit, total_employees)
            
            result = employee_list[start_idx:end_idx]
            print(f"Final result: {len(result)} employees (after limit/offset)")
            if result:
                print("Sample employee data:")
                sample = result[0]
                print(f"  Name: {sample.get('name', 'Unknown')}")
                print(f"  Employee #: {sample.get('employee_number', 'Unknown')}")
                print(f"  Location: {sample.get('location', 'Unknown')}")
                print(f"  Skills: {sample.get('skills', [])}")
            
            print("===== END FETCH_EMPLOYEES DEBUG =====\n")
            return result
            
        except Exception as e:
            print(f"Error fetching employees: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return empty list to avoid breaking the application
            return []
    
    def fetch_availability_batch(self, employee_ids, weeks=None):
        """
        Fetch availability data for multiple employees
        
        Args:
            employee_ids (list): List of employee IDs to fetch availability for
            weeks (list): Optional list of week numbers to filter by
            
        Returns:
            Dictionary mapping employee IDs to their availability data
        """
        try:
            result = {}
            
            # Return empty result if no employee IDs
            if not employee_ids:
                return result
                
            # Ensure weeks is a list
            if weeks is None:
                weeks = []
            
            for emp_id in employee_ids:
                # Skip None or empty IDs
                if not emp_id:
                    continue
                    
                # Get reference to availability document
                availability_ref = self.client.collection('availability').document(emp_id)
                
                # Query the weeks subcollection
                weeks_query = availability_ref.collection('weeks')
                
                # Apply week filter if specified
                if weeks and len(weeks) > 0:
                    # Firestore has a limit of 10 values for 'in' queries
                    # For simplicity, we'll just take the first 10 weeks if more are specified
                    filtered_weeks = weeks[:10]
                    weeks_query = weeks_query.filter("week_number", "in", filtered_weeks)
                
                # Execute query
                try:
                    availability_docs = weeks_query.get()
                    
                    # Process results
                    emp_availability = {}
                    for doc in availability_docs:
                        week_data = doc.to_dict()
                        week_num = week_data.get('week_number')
                        if week_num:
                            emp_availability[f'week{week_num}'] = week_data
                    
                    # Add to result dictionary if we found availability data
                    if emp_availability:
                        result[emp_id] = emp_availability
                except Exception as e:
                    print(f"Error fetching availability for employee {emp_id}: {str(e)}")
                    continue
            
            return result
            
        except Exception as e:
            print(f"Error fetching availability batch: {str(e)}")
            return {}
    
    def save_query_data(self, query, response, metadata=None, session_id=None):
        """
        Save user query and response data to the 'queries' collection in Firestore.
        
        Args:
            query (str): The user's query string
            response (str): The system's response to the query
            metadata (dict): Dictionary containing extracted metadata:
                - ranks (list): Ranks mentioned in the query
                - locations (list): Locations mentioned in the query
                - skills (list): Skills mentioned in the query
                - availability (dict): Availability criteria used
            session_id (str): Unique identifier for the user session
                
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.is_connected:
                print("Cannot save query data: Firebase client is not connected")
                return False
                
            # Create a new document in the queries collection
            query_ref = self.client.collection('queries').document()
            
            # Extract tags from metadata
            tags = []
            if metadata:
                # Add locations as tags
                if 'locations' in metadata and metadata['locations']:
                    tags.extend([loc.lower() for loc in metadata['locations']])
                
                # Add skills as tags
                if 'skills' in metadata and metadata['skills']:
                    tags.extend([skill.lower() for skill in metadata['skills']])
                
                # Add ranks as tags
                if 'ranks' in metadata and metadata['ranks']:
                    tags.extend([rank.lower() for rank in metadata['ranks']])
                
                # Add availability as a tag if present
                if 'availability' in metadata and metadata['availability']:
                    if 'weeks' in metadata['availability'] and metadata['availability']['weeks']:
                        tags.append('availability')
                        for week in metadata['availability']['weeks']:
                            tags.append(f"week{week}")
                    
                    if 'status' in metadata['availability'] and metadata['availability']['status']:
                        for status in metadata['availability']['status']:
                            tags.append(status.lower())
            
            # Create the document data
            doc_data = {
                'query': query,
                'response': response,
                'timestamp': datetime.datetime.now(),
                'tags': list(set(tags)),  # Remove duplicates
                'metadata': metadata or {},
                'session_id': session_id or str(uuid.uuid4())
            }
            
            # Save to Firestore
            query_ref.set(doc_data)
            print(f"✅ Query data saved to Firestore with ID: {query_ref.id}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving query data: {str(e)}")
            import traceback
            traceback.print_exc()
            return False 