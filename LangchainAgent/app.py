"""
Resource Management Agent - Streamlit UI
"""

import streamlit as st
import os
from dotenv import load_dotenv
from src.master_agent import MasterAgent
from src.query_translator import QueryTranslator
from src.resource_fetcher import ResourceFetcher
from src.response_generator import ResponseGenerator
from src.firebase_utils import FirebaseClient

# Load environment variables from .env file
load_dotenv()

# Set page config - must be the first Streamlit command
st.set_page_config(
    page_title="ResGenie - Resource Management Agent",
    page_icon="🧞",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = None
if "firebase_client" not in st.session_state:
    st.session_state.firebase_client = None

# Check for required environment variables
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
# Try to get the API key from Streamlit secrets if not in environment variables
if not anthropic_api_key and 'ANTHROPIC_API_KEY' in st.secrets:
    anthropic_api_key = st.secrets['ANTHROPIC_API_KEY']

firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
# Try to get the credentials path from Streamlit secrets if not in environment variables
if not firebase_creds_path and 'FIREBASE_CREDENTIALS_PATH' in st.secrets:
    firebase_creds_path = st.secrets['FIREBASE_CREDENTIALS_PATH']

if not anthropic_api_key:
    st.error("⚠️ ANTHROPIC_API_KEY not found in environment variables or Streamlit secrets.")
    st.info("Please set your ANTHROPIC_API_KEY environment variable or add it to your Streamlit secrets.")
    st.stop()

# Initialize Firebase only once if not already initialized
if st.session_state.firebase_client is None:
    try:
        st.session_state.firebase_client = FirebaseClient()
        
        # Verify Firebase setup
        verification = st.session_state.firebase_client.verify_firebase_setup()
        
        if verification['employees_exist'] and verification['availability_exist']:
            pass  # Success message removed
        elif verification['employees_exist']:
            st.warning(f"⚠️ {verification['message']}")
            st.info("""
            Your Firebase connection is working, and you have employees, but the availability data is missing or not structured correctly.
            
            You need to ensure proper availability data in your Firestore database for the application to work correctly.
            """)
        else:
            st.warning(f"⚠️ {verification['message']}")
            st.info("""
            Your Firebase connection is working, but there are no employees in the 'employees' collection.
            
            You need to add employee documents to your Firestore database for the application to work correctly.
            """)
            
            with st.expander("How to Add Employee Data to Firebase", expanded=True):
                st.markdown("""
                ## Adding Employee Data to Firebase
                
                1. Go to your [Firebase Console](https://console.firebase.google.com/)
                2. Navigate to your project > Firestore Database
                3. Create a collection named `employees`
                4. Add employee documents with the following structure:
                
                ```json
                {
                  "name": "John Doe",
                  "employee_number": "EMP123",
                  "location": "London", 
                  "rank": {
                    "official_name": "Senior Consultant"
                  },
                  "skills": ["python", "machine learning", "aws"]
                }
                ```
                
                5. Create a separate collection named `availability`
                6. Add availability documents with employee numbers as document IDs
                7. For each availability document, create a subcollection named `weeks`
                8. In each `weeks` subcollection, add documents for different weeks with the following structure:
                
                ```json
                {
                  "week_number": 1,
                  "status": "available",
                  "hours": 40,
                  "notes": "Working on Project X"
                }
                ```
                
                For more details, see the Firebase Setup Guide.
                """)
                
                st.warning("The application will not work correctly without proper employee and availability data in your database.")
            
    except Exception as e:
        st.error(f"⚠️ Firebase connection failed: {str(e)}")
        st.info("""
        To connect to Firebase:
        1. Make sure you have a valid Firebase project set up with Firestore.
        2. Create a service account key JSON file in the Firebase console.
        3. Save this file as 'firebase_credentials.json' in the project directory.
        4. Or set the FIREBASE_CREDENTIALS_PATH environment variable to point to your credentials file.
        
        For detailed instructions, please refer to the FIREBASE_SETUP.md file.
        """)
        # Display the contents of the setup guide
        try:
            with open("FIREBASE_SETUP.md", "r") as f:
                setup_guide = f.read()
        except FileNotFoundError:
            # Try alternative paths
            try:
                import os
                project_root = os.path.dirname(os.path.abspath(__file__))
                with open(os.path.join(project_root, "FIREBASE_SETUP.md"), "r") as f:
                    setup_guide = f.read()
            except FileNotFoundError:
                setup_guide = """
                # Firebase Setup Guide
                
                Please create a firebase_credentials.json file with your Firebase service account credentials.
                
                1. Go to Firebase Console > Project Settings > Service Accounts
                2. Click "Generate New Private Key"
                3. Save as firebase_credentials.json in the project directory
                """
        
        with st.expander("Firebase Setup Guide", expanded=True):
            st.markdown(setup_guide)
        st.stop()  # Stop execution until Firebase is properly configured

def initialize_agent():
    """Initialize the agent with all required components."""
    try:
        # Get API key from environment variables or Streamlit secrets
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key and 'ANTHROPIC_API_KEY' in st.secrets:
            anthropic_api_key = st.secrets['ANTHROPIC_API_KEY']
            
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables or Streamlit secrets")
        
        # Check Firebase connection
        if not st.session_state.firebase_client or not st.session_state.firebase_client.is_connected:
            raise ValueError("Firebase client is not connected")

        # Initialize components
        query_translator = QueryTranslator()
        resource_fetcher = ResourceFetcher(st.session_state.firebase_client)
        response_generator = ResponseGenerator(anthropic_api_key=anthropic_api_key)
        
        # Create master agent
        return MasterAgent(query_translator, resource_fetcher, response_generator)
    except Exception as e:
        st.error(f"Error initializing components: {str(e)}")
        return None

# Initialize agent if not already done
if st.session_state.agent is None:
    # Check Firebase connection first
    if not st.session_state.firebase_client or not st.session_state.firebase_client.is_connected:
        st.error("Cannot initialize agent: Firebase is not connected")
        st.info("Please set up your Firebase connection first")
    else:
        # Check if resources exist
        verification = st.session_state.firebase_client.verify_firebase_setup()
        if not verification['employees_exist']:
            st.error("Cannot initialize agent: No employees found in Firebase")
            st.info("Please add employees to your Firebase database first")
        else:
            st.session_state.agent = initialize_agent()

# Title and description
st.title("🧞 ResGenie")

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Ask about employees..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                if st.session_state.agent:
                    response = st.session_state.agent.process_message(prompt)
                else:
                    response = "Sorry, the agent is not properly initialized. Please check the system status in the sidebar."
                st.markdown(response)
            except Exception as e:
                error_msg = f"Error processing query: {str(e)}"
                st.error(error_msg)
                response = f"I encountered an error: {str(e)}"
                st.markdown(response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

# Sample queries in an expander
with st.expander("📝 Sample Queries", expanded=False):
    st.markdown("""
    Try these example queries:
    - "Find frontend developers in London"
    - "Who are the consultants available in Week 3?"
    - "Show me Solution Architects in Oslo"
    - "Find employees with rank above consultant"
    """)

# Add information in the sidebar
with st.sidebar:
    st.title("About ResGenie")
    st.markdown("""
    ResGenie helps you find the right resources for your project.
    
    You can ask questions like:
    - Find frontend developers in London
    - Show me Senior Consultants with Python skills
    - Who is available in Week 3?
    - Find employees with React skills who are available next week
    """)
    