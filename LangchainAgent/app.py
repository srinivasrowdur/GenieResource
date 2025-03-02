"""
Resource Management Agent - Streamlit UI
"""

import streamlit as st
import os
import uuid
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from datetime import datetime, timedelta
import altair as alt
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
    page_title="Resource Genie - Resource Management Agent",
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

# Create or restore a session ID
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

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

def extract_query_metadata(query, response):
    """
    Extract metadata from the query string and response.
    
    Args:
        query (str): The user's query
        response (str): The system's response
        
    Returns:
        dict: Dictionary containing extracted metadata
    """
    metadata = {
        'locations': [],
        'ranks': [],
        'skills': [],
        'availability': {
            'weeks': [],
            'status': []
        }
    }
    
    # Get available metadata for reference
    try:
        if st.session_state.firebase_client and st.session_state.firebase_client.is_connected:
            reference_metadata = st.session_state.firebase_client.get_resource_metadata()
            
            # Match locations in query
            if 'locations' in reference_metadata and reference_metadata['locations']:
                for location in reference_metadata['locations']:
                    if location.lower() in query.lower():
                        metadata['locations'].append(location)
            
            # Match ranks in query
            if 'ranks' in reference_metadata and reference_metadata['ranks']:
                for rank in reference_metadata['ranks']:
                    if rank.lower() in query.lower():
                        metadata['ranks'].append(rank)
            
            # Match skills in query
            if 'skills' in reference_metadata and reference_metadata['skills']:
                for skill in reference_metadata['skills']:
                    if skill.lower() in query.lower():
                        metadata['skills'].append(skill)
    except Exception as e:
        print(f"Error extracting metadata from reference: {str(e)}")
    
    # Extract availability information
    week_pattern = r'week\s*(\d+)'
    week_matches = re.findall(week_pattern, query.lower())
    if week_matches:
        metadata['availability']['weeks'] = [int(week) for week in week_matches]
    
    # Extract availability status
    status_keywords = ['available', 'unavailable', 'partially available']
    for status in status_keywords:
        if status.lower() in query.lower():
            metadata['availability']['status'].append(status)
    
    return metadata

def get_query_trends_data():
    """
    Fetch query trend data from Firebase
    
    Returns:
        dict: Dictionary containing trend data
    """
    if not st.session_state.firebase_client or not st.session_state.firebase_client.is_connected:
        return None
        
    try:
        # Get queries collection
        queries_ref = st.session_state.firebase_client.client.collection('queries')
        
        # Get all documents - in a real app with many queries, you'd want to limit this
        # and implement pagination or filtering by date range
        queries = list(queries_ref.order_by('timestamp', direction='DESCENDING').limit(100).stream())
        
        if not queries:
            return {
                'total_queries': 0,
                'queries': [],
                'dates': [],
                'locations': [],
                'skills': [],
                'ranks': [],
                'availability_status': [],
                'availability_weeks': []
            }
        
        # Process query data
        processed_data = {
            'total_queries': len(queries),
            'queries': [],
            'dates': [],
            'locations': [],
            'skills': [],
            'ranks': [],
            'availability_status': [],
            'availability_weeks': []
        }
        
        for query_doc in queries:
            query_data = query_doc.to_dict()
            
            # Add the query text and response
            processed_data['queries'].append({
                'query': query_data.get('query', ''),
                'response': query_data.get('response', ''),
                'timestamp': query_data.get('timestamp', datetime.now()),
                'session_id': query_data.get('session_id', '')
            })
            
            # Add the timestamp for time-based analysis
            timestamp = query_data.get('timestamp')
            if timestamp:
                processed_data['dates'].append(timestamp)
            
            # Extract metadata
            metadata = query_data.get('metadata', {})
            
            # Add locations
            locations = metadata.get('locations', [])
            if locations:
                processed_data['locations'].extend(locations)
            
            # Add skills
            skills = metadata.get('skills', [])
            if skills:
                processed_data['skills'].extend(skills)
            
            # Add ranks
            ranks = metadata.get('ranks', [])
            if ranks:
                processed_data['ranks'].extend(ranks)
            
            # Add availability info
            availability = metadata.get('availability', {})
            
            # Add availability status
            status_list = availability.get('status', [])
            if status_list:
                processed_data['availability_status'].extend(status_list)
            
            # Add availability weeks
            weeks_list = availability.get('weeks', [])
            if weeks_list:
                processed_data['availability_weeks'].extend(weeks_list)
        
        return processed_data
    
    except Exception as e:
        print(f"Error fetching query trends: {str(e)}")
        return None

def display_trends_dashboard():
    """Display the trends dashboard with visualizations"""
    st.title("📊 Query Trends Dashboard")
    
    with st.spinner("Loading trend data..."):
        trends_data = get_query_trends_data()
    
    if not trends_data or trends_data['total_queries'] == 0:
        st.info("No query data available yet. Start using the chat to generate trend data!")
        return
    
    # Display key metrics in a nice layout
    total_queries = trends_data['total_queries']
    unique_sessions = len(set(q['session_id'] for q in trends_data['queries'] if q['session_id']))
    unique_locations = len(set(trends_data['locations']))
    unique_skills = len(set(trends_data['skills']))
    
    # Create an attractive metrics display with emojis and cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""
            <div style="padding: 20px; background-color: #f0f7ff; border-radius: 10px; text-align: center;">
                <h1 style="font-size: 40px;">🔍</h1>
                <h2>{total_queries}</h2>
                <p>Total Queries</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f"""
            <div style="padding: 20px; background-color: #fff0f7; border-radius: 10px; text-align: center;">
                <h1 style="font-size: 40px;">👥</h1>
                <h2>{unique_sessions}</h2>
                <p>Unique Sessions</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    with col3:
        st.markdown(
            f"""
            <div style="padding: 20px; background-color: #f0fff7; border-radius: 10px; text-align: center;">
                <h1 style="font-size: 40px;">📍</h1>
                <h2>{unique_locations}</h2>
                <p>Locations Searched</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    with col4:
        st.markdown(
            f"""
            <div style="padding: 20px; background-color: #f7f0ff; border-radius: 10px; text-align: center;">
                <h1 style="font-size: 40px;">🔧</h1>
                <h2>{unique_skills}</h2>
                <p>Skills Searched</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # Create visualizations for different types of data
    col1, col2 = st.columns(2)
    
    with col1:
        # Top locations chart
        if trends_data['locations']:
            st.subheader("📍 Top Searched Locations")
            location_counts = Counter(trends_data['locations'])
            locations_df = pd.DataFrame({
                'Location': list(location_counts.keys()),
                'Count': list(location_counts.values())
            }).sort_values('Count', ascending=False).head(8)
            
            fig = px.bar(
                locations_df, 
                x='Count', 
                y='Location',
                orientation='h',
                color='Count',
                color_continuous_scale=px.colors.sequential.Viridis,
                title="Most Requested Locations"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No location data available yet.")
    
    with col2:
        # Top skills chart
        if trends_data['skills']:
            st.subheader("🔧 Top Requested Skills")
            skill_counts = Counter(trends_data['skills'])
            skills_df = pd.DataFrame({
                'Skill': list(skill_counts.keys()),
                'Count': list(skill_counts.values())
            }).sort_values('Count', ascending=False).head(8)
            
            fig = px.pie(
                skills_df, 
                values='Count', 
                names='Skill',
                color_discrete_sequence=px.colors.sequential.RdBu,
                title="Most Requested Skills",
                hole=0.4
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No skills data available yet.")
    
    # Time-series analysis
    if trends_data['dates']:
        st.subheader("📅 Query Volume Over Time")
        
        # Group by date
        date_counts = Counter(d.date() for d in trends_data['dates'])
        dates_df = pd.DataFrame({
            'Date': list(date_counts.keys()),
            'Count': list(date_counts.values())
        }).sort_values('Date')
        
        # Fill in missing dates
        if len(dates_df) > 1:
            date_range = pd.date_range(start=min(dates_df['Date']), end=max(dates_df['Date']))
            full_df = pd.DataFrame({'Date': date_range})
            dates_df = full_df.merge(dates_df, on='Date', how='left').fillna(0)
        
        fig = px.line(
            dates_df, 
            x='Date', 
            y='Count',
            markers=True,
            line_shape='spline',
            color_discrete_sequence=['#6200EA'],
            title="Daily Query Volume"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Additional visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Top ranks chart
        if trends_data['ranks']:
            st.subheader("🏅 Most Searched Ranks")
            rank_counts = Counter(trends_data['ranks'])
            ranks_df = pd.DataFrame({
                'Rank': list(rank_counts.keys()),
                'Count': list(rank_counts.values())
            }).sort_values('Count', ascending=False)
            
            fig = px.bar(
                ranks_df,
                x='Rank',
                y='Count',
                color='Count',
                color_continuous_scale=px.colors.sequential.Plasma,
                title="Rank Distribution in Queries"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No rank data available yet.")
    
    with col2:
        # Availability status chart
        if trends_data['availability_status']:
            st.subheader("📆 Availability Search Patterns")
            status_counts = Counter(trends_data['availability_status'])
            status_df = pd.DataFrame({
                'Status': list(status_counts.keys()),
                'Count': list(status_counts.values())
            })
            
            fig = px.bar(
                status_df,
                x='Status',
                y='Count',
                color='Status',
                title="Availability Status in Queries"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No availability status data yet.")
    
    # Week popularity chart
    if trends_data['availability_weeks']:
        st.subheader("📊 Popular Weeks Searched")
        week_counts = Counter(trends_data['availability_weeks'])
        weeks_df = pd.DataFrame({
            'Week': list(week_counts.keys()),
            'Count': list(week_counts.values())
        }).sort_values('Week')
        
        fig = px.line(
            weeks_df,
            x='Week',
            y='Count',
            markers=True,
            title="Week Number Popularity",
            color_discrete_sequence=['#FF6F00']
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent queries section with nice formatting
    if trends_data['queries']:
        st.markdown("---")
        st.subheader("🕒 Recent Queries")
        
        # Show the 5 most recent queries
        recent_queries = trends_data['queries'][:5]
        
        for i, query_data in enumerate(recent_queries):
            query = query_data.get('query', '')
            timestamp = query_data.get('timestamp', datetime.now())
            
            # Format the timestamp nicely
            if hasattr(timestamp, 'strftime'):
                time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = str(timestamp)
            
            # Create an attractive card for each query
            st.markdown(
                f"""
                <div style="padding: 15px; background-color: #f8f9fa; border-radius: 10px; margin-bottom: 10px;">
                    <p style="color: #6c757d; margin-bottom: 5px; font-size: 0.8em;">{time_str}</p>
                    <p style="font-weight: bold; margin-bottom: 0;">"{query}"</p>
                </div>
                """, 
                unsafe_allow_html=True
            )

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

# Title and tabs
st.title("🧞 Resource Genie")

# Create tabs for Chat and Trends
chat_tab, trends_tab = st.tabs(["💬 Chat", "📈 Trends"])

with chat_tab:
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
                        
                        # Extract metadata from the query and response for storage
                        query_metadata = extract_query_metadata(prompt, response)
                        
                        # Store query and response data in Firebase
                        if st.session_state.firebase_client and st.session_state.firebase_client.is_connected:
                            # Save query data in the background (don't block the UI)
                            st.session_state.firebase_client.save_query_data(
                                query=prompt,
                                response=response,
                                metadata=query_metadata,
                                session_id=st.session_state.session_id
                            )
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

with trends_tab:
    # Display the trends dashboard
    display_trends_dashboard()

# Add information in the sidebar
with st.sidebar:
    st.title("About Resource Genie")
    st.markdown("""
    Resource Genie helps you find the right resources for your project.
    
    You can ask questions like:
    - Find frontend developers in London
    - Show me Senior Consultants with Python skills
    - Who is available in Week 3?
    - Find employees with React skills who are available next week
    """)
    
    # Add helpful resource information in expandable sections
    if st.session_state.firebase_client and st.session_state.firebase_client.is_connected:
        # Get resource metadata if available
        try:
            metadata = st.session_state.firebase_client.get_resource_metadata()
            
            # Show locations in an expander
            with st.expander("📍 Available Locations", expanded=False):
                if metadata and 'locations' in metadata and metadata['locations']:
                    st.markdown("You can search for employees in these locations:")
                    for location in sorted(metadata['locations']):
                        st.markdown(f"- {location}")
                else:
                    st.markdown("Location data is currently unavailable.")
            
            # Show skills in an expander
            with st.expander("🔧 Common Skills", expanded=False):
                if metadata and 'skills' in metadata and metadata['skills']:
                    st.markdown("You can search for employees with these skills:")
                    # Display top skills (limit to prevent overwhelming)
                    skills_to_show = sorted(metadata['skills'])[:15]
                    for skill in skills_to_show:
                        st.markdown(f"- {skill}")
                    if len(metadata['skills']) > 15:
                        st.markdown("*(and more...)*")
                else:
                    st.markdown("Skills data is currently unavailable.")
            
            # Show ranks in an expander
            with st.expander("🏅 Employee Ranks", expanded=False):
                if metadata and 'ranks' in metadata and metadata['ranks']:
                    st.markdown("You can search for employees by these ranks:")
                    for rank in sorted(metadata['ranks']):
                        st.markdown(f"- {rank}")
                else:
                    st.markdown("Rank data is currently unavailable.")
                    
        except Exception as e:
            st.warning("Resource metadata could not be loaded.")
            # Don't show the full error to users
    