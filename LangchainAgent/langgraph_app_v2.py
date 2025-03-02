"""
Resource Genie - Streamlit UI for LangGraph Agent (v2)

This is the Streamlit UI for the Resource Genie application using the proper LangGraph-based agent.

Installation requirements:
- pip install langgraph>=0.0.15
- pip install streamlit
- pip install langchain-anthropic
- pip install python-dotenv
- pip install altair
- pip install plotly
- pip install pandas
- pip install firebase-admin
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
from src.langgraph_agent import ReActAgentGraph
from src.firebase_utils import FirebaseClient
from langchain_anthropic import ChatAnthropic

# Load environment variables from .env file
load_dotenv()

# Set page config - must be the first Streamlit command
st.set_page_config(
    page_title="Resource Genie - LangGraph V2",
    page_icon="🧞",
    layout="wide"
)

# Page styling
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        font-size: 16px;
    }
    .reportview-container .main .block-container {
        padding-top: 2rem;
    }
    .metric-card {
        background-color: #FFFFFF;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
    }
    .metric-label {
        font-size: 14px;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# Get API keys and credentials paths
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

# Use the local credentials file in the LangchainAgent directory
firebase_creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                 "resgenie-e8ab5-firebase-adminsdk-fbsvc-eb9f384590.json")

# Verify the file exists
if os.path.exists(firebase_creds_path):
    st.sidebar.success(f"Found Firebase credentials at: {firebase_creds_path}")
else:
    st.sidebar.error(f"Firebase credentials file not found at: {firebase_creds_path}")
    # Try the project root as a fallback
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    firebase_creds_path = os.path.join(project_root, "resgenie-e8ab5-firebase-adminsdk-fbsvc-eb9f384590.json")
    if os.path.exists(firebase_creds_path):
        st.sidebar.success(f"Found Firebase credentials at project root: {firebase_creds_path}")
    else:
        st.sidebar.error(f"Firebase credentials not found in project root either")
        firebase_creds_path = None

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm Resource Genie, your AI assistant for resource management. How can I help you today?"}
    ]

if "agent" not in st.session_state:
    st.session_state.agent = None

if "firebase_client" not in st.session_state:
    st.session_state.firebase_client = None

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "use_cache" not in st.session_state:
    st.session_state.use_cache = True

if "cache_ttl" not in st.session_state:
    st.session_state.cache_ttl = 3600

# Function to extract metadata from query
def extract_query_metadata(query, response):
    """
    Extract metadata from a query for analytics.
    
    Args:
        query: The original query text
        response: The generated response
        
    Returns:
        Dictionary of extracted metadata
    """
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "query_length": len(query),
        "response_length": len(response),
        "locations": [],
        "skills": [],
        "ranks": []
    }
    
    # Extract locations (simple keyword matching for demo purposes)
    locations = ["London", "Manchester", "Edinburgh", "Glasgow", "Birmingham", "Leeds"]
    for location in locations:
        if re.search(r'\b' + location + r'\b', query, re.IGNORECASE):
            metadata["locations"].append(location)
    
    # Extract skills (simple keyword matching)
    skills = ["Python", "Java", "JavaScript", "Frontend", "Backend", "AI", "ML", "DevOps", "Cloud"]
    for skill in skills:
        if re.search(r'\b' + skill + r'\b', query, re.IGNORECASE):
            metadata["skills"].append(skill)
    
    # Extract ranks (simple keyword matching)
    ranks = ["Analyst", "Consultant", "Senior Consultant", "Principal Consultant", "Manager", "Partner"]
    for rank in ranks:
        if re.search(r'\b' + rank + r'\b', query, re.IGNORECASE):
            metadata["ranks"].append(rank)
    
    return metadata

# Function to get reference metadata
def get_reference_metadata():
    """Get reference metadata for locations, skills, and ranks."""
    metadata = {
        "locations": ["London", "Manchester", "Edinburgh", "Glasgow", "Birmingham", "Leeds"],
        "skills": ["Python", "Java", "JavaScript", "Frontend", "Backend", "AI", "ML", "DevOps", "Cloud"],
        "ranks": ["Analyst", "Consultant", "Senior Consultant", "Principal Consultant", "Manager", "Partner"]
    }
    
    # If Firebase client is available, get real metadata
    if st.session_state.firebase_client and st.session_state.firebase_client.is_connected:
        try:
            firebase_metadata = st.session_state.firebase_client.get_resource_metadata()
            # Update metadata with values from Firebase
            for key in metadata:
                if key in firebase_metadata and firebase_metadata[key]:
                    metadata[key] = firebase_metadata[key]
        except Exception as e:
            st.error(f"Error fetching reference metadata: {e}")
    
    return metadata

# Function to initialize the agent
def initialize_agent():
    """Initialize the agent and Firebase client."""
    # Check if we have the required API keys
    if not anthropic_api_key:
        st.sidebar.error("ANTHROPIC_API_KEY not found. Please add it to your .env file or Streamlit secrets.")
        return False
    
    try:
        # Initialize Firebase client
        firebase_client = FirebaseClient(credentials_path=firebase_creds_path)
        st.session_state.firebase_client = firebase_client
        
        if firebase_client.is_connected:
            st.sidebar.success("Connected to Firebase successfully!")
            st.sidebar.info("Using the employees collection with nested rank objects.")
        else:
            st.sidebar.warning("Running in demo mode without Firebase connection.")
        
        # Initialize the model
        model = ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            anthropic_api_key=anthropic_api_key,
            temperature=0
        )
        
        # Get caching settings from session state or use defaults
        use_cache = st.session_state.get("use_cache", True)
        cache_ttl = st.session_state.get("cache_ttl", 3600)
        
        # Initialize the agent with caching enabled and correct configuration for the database structure
        st.session_state.agent = ReActAgentGraph(
            model=model, 
            firebase_client=firebase_client,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
            verbose=True
        )
        return True
    
    except Exception as e:
        st.sidebar.error(f"Error initializing agent: {e}")
        return False

# Function to get query data for trends
def get_query_data():
    """Get query data from Firebase for the trends dashboard."""
    if not st.session_state.firebase_client or not st.session_state.firebase_client.is_connected:
        return None
    
    try:
        # Get query data from Firebase
        query_data = st.session_state.firebase_client.get_all_queries()
        return query_data
    except Exception as e:
        st.error(f"Error fetching query data: {e}")
        return None

# Function to create trend visualizations
def create_trend_visualizations(query_data):
    """Create visualizations for the trends dashboard."""
    if not query_data:
        st.warning("No query data available. Please ensure Firebase connection is working.")
        return
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(query_data)
    
    # Add error handling for missing fields
    required_fields = ['timestamp', 'query_length', 'response_length', 'session_id', 'locations', 'skills', 'ranks']
    missing_fields = [field for field in required_fields if field not in df.columns]
    
    if missing_fields:
        st.error(f"Missing required data fields: {', '.join(missing_fields)}. Some visualizations may not be displayed.")
        # Add default values for missing fields
        for field in missing_fields:
            if field == 'timestamp':
                df['timestamp'] = [datetime.now().isoformat() for _ in range(len(df))]
            elif field in ['query_length', 'response_length']:
                df[field] = [0 for _ in range(len(df))]
            elif field == 'session_id':
                df['session_id'] = [f"session_{i}" for i in range(len(df))]
            elif field in ['locations', 'skills', 'ranks']:
                df[field] = [[] for _ in range(len(df))]
    
    # Ensure timestamp is in datetime format
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    # Create date for grouping
    df['date'] = df['timestamp'].dt.date
    
    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{len(df)}</div>", unsafe_allow_html=True)
        st.markdown("<div class='metric-label'>Total Queries</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col2:
        try:
            avg_query_length = int(df['query_length'].mean())
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{avg_query_length}</div>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Avg Query Length</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>N/A</div>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Avg Query Length</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
    with col3:
        try:
            avg_response_length = int(df['response_length'].mean())
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{avg_response_length}</div>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Avg Response Length</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>N/A</div>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Avg Response Length</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
    with col4:
        try:
            unique_sessions = df['session_id'].nunique()
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{unique_sessions}</div>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Unique Sessions</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>N/A</div>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Unique Sessions</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Daily query count chart
    st.subheader("Query Volume Over Time")
    daily_counts = df.groupby('date').size().reset_index(name='count')
    daily_chart = px.line(
        daily_counts, 
        x='date', 
        y='count',
        labels={'count': 'Number of Queries', 'date': 'Date'},
        markers=True
    )
    daily_chart.update_layout(height=300)
    st.plotly_chart(daily_chart, use_container_width=True)
    
    # Create two columns for the next two charts
    col1, col2 = st.columns(2)
    
    # Location distribution
    with col1:
        st.subheader("Top Locations")
        # Flatten the locations lists
        all_locations = []
        for locations in df['locations']:
            if isinstance(locations, list) and locations:
                all_locations.extend(locations)
        
        if all_locations:
            location_counts = Counter(all_locations).most_common(5)
            location_df = pd.DataFrame(location_counts, columns=['Location', 'Count'])
            
            location_chart = px.bar(
                location_df,
                x='Location',
                y='Count',
                color='Count',
                color_continuous_scale='Blues'
            )
            location_chart.update_layout(height=300)
            st.plotly_chart(location_chart, use_container_width=True)
        else:
            st.info("No location data available.")
    
    # Skills distribution
    with col2:
        st.subheader("Top Skills")
        # Flatten the skills lists
        all_skills = []
        for skills in df['skills']:
            if isinstance(skills, list) and skills:
                all_skills.extend(skills)
        
        if all_skills:
            skill_counts = Counter(all_skills).most_common(5)
            skill_df = pd.DataFrame(skill_counts, columns=['Skill', 'Count'])
            
            skill_chart = px.bar(
                skill_df,
                x='Skill',
                y='Count',
                color='Count',
                color_continuous_scale='Greens'
            )
            skill_chart.update_layout(height=300)
            st.plotly_chart(skill_chart, use_container_width=True)
        else:
            st.info("No skill data available.")
    
    # Rank distribution
    st.subheader("Rank Distribution")
    # Flatten the ranks lists
    all_ranks = []
    for ranks in df['ranks']:
        if isinstance(ranks, list) and ranks:
            all_ranks.extend(ranks)
    
    if all_ranks:
        rank_counts = Counter(all_ranks).most_common()
        rank_df = pd.DataFrame(rank_counts, columns=['Rank', 'Count'])
        
        rank_chart = px.pie(
            rank_df,
            values='Count',
            names='Rank',
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Plasma
        )
        rank_chart.update_layout(height=400)
        st.plotly_chart(rank_chart, use_container_width=True)
    else:
        st.info("No rank data available.")

# Create tabs for main content
main_tabs = st.tabs(["💬 Chat", "📊 Trends"])

with main_tabs[0]:  # Chat tab
    st.title("Resource Genie 🧞")
    st.markdown("*Ask me about available resources, skills, locations, and more!*")
    
    # Initialize agent if not already initialized
    if st.session_state.agent is None:
        agent_initialized = initialize_agent()
        if not agent_initialized:
            st.stop()

    # Display sidebar information
    with st.sidebar:
        st.title("Resource Genie 🧞")
        st.caption("LangGraph Implementation V2")
        
        # Session management
        st.subheader("Session")
        if st.button("Reset Session"):
            # Reset chat messages
            st.session_state.messages = [
                {"role": "assistant", "content": "Hello! I'm Resource Genie, your AI assistant for resource management. How can I help you today?"}
            ]
            # Reset the agent state
            if "agent" in st.session_state and st.session_state.agent:
                st.session_state.agent.reset(session_id=st.session_state.session_id)
            # Generate a new session ID
            st.session_state.session_id = str(uuid.uuid4())
            st.success(f"Session reset! New session ID: {st.session_state.session_id}")
        
        st.write(f"Session ID: {st.session_state.session_id}")
        
        # Cache configuration
        st.subheader("Cache Settings")
        
        # Cache toggle
        use_cache = st.toggle("Enable Response Caching", 
                             value=st.session_state.get("use_cache", True),
                             help="Toggle caching of responses for improved performance")
        
        # Update session state and agent if toggle changes
        if "use_cache" not in st.session_state or st.session_state.use_cache != use_cache:
            st.session_state.use_cache = use_cache
            if "agent" in st.session_state and st.session_state.agent:
                st.session_state.agent.use_cache = use_cache
        
        # Cache TTL slider
        cache_ttl = st.slider("Cache TTL (seconds)", 
                             min_value=60, 
                             max_value=24*3600, 
                             value=st.session_state.get("cache_ttl", 3600),
                             step=60,
                             help="Time to live for cached responses")
        
        # Update session state and agent if TTL changes
        if "cache_ttl" not in st.session_state or st.session_state.cache_ttl != cache_ttl:
            st.session_state.cache_ttl = cache_ttl
            if "agent" in st.session_state and st.session_state.agent:
                st.session_state.agent.cache_ttl = cache_ttl
        
        # Clear cache button
        if st.button("Clear Cache"):
            if "agent" in st.session_state and st.session_state.agent:
                st.session_state.agent.clear_cache()
                st.success("Cache cleared successfully!")
        
        # Cache statistics if agent is initialized
        if "agent" in st.session_state and st.session_state.agent:
            st.subheader("Cache Statistics")
            cache_stats = st.session_state.agent.get_cache_stats()
            
            # Create metrics for cache statistics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Hit Rate", f"{cache_stats['hit_rate']:.1%}")
                st.metric("Cache Size", cache_stats['size'])
            with col2:
                st.metric("Hits", cache_stats['hits'])
                st.metric("Misses", cache_stats['misses'])
        
        # Resource metadata section
        if st.session_state.firebase_client and st.session_state.firebase_client.is_connected:
            st.subheader("Resource Information")
            try:
                metadata = st.session_state.firebase_client.get_resource_metadata()
                with st.expander("Locations"):
                    locations = metadata.get("locations", [])
                    if locations:
                        st.write(", ".join(locations))
                    else:
                        st.write("No location data available.")
                
                with st.expander("Skills"):
                    skills = metadata.get("skills", [])
                    if skills:
                        st.write(", ".join(skills))
                    else:
                        st.write("No skill data available.")
                
                with st.expander("Ranks"):
                    ranks = metadata.get("ranks", [])
                    if ranks:
                        st.write(", ".join(ranks))
                    else:
                        st.write("No rank data available.")
            except Exception as e:
                st.error(f"Error fetching metadata: {e}")
        else:
            st.info("Running in demo mode. Resource metadata not available.")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("How can I help you with resource management?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message in chat
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Display assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🧞 Thinking...")
            
            try:
                # Process the message with the agent
                result = st.session_state.agent.process_message(
                    prompt,
                    session_id=st.session_state.session_id
                )
                
                # Extract metadata from the query and store in Firebase
                if st.session_state.firebase_client and st.session_state.firebase_client.is_connected:
                    metadata = extract_query_metadata(prompt, result["response"])
                    st.session_state.firebase_client.save_query_data(
                        query=prompt,
                        response=result["response"],
                        metadata=metadata,
                        session_id=st.session_state.session_id
                    )
                
                # Display the response
                message_placeholder.markdown(result["response"])
                
                # Show performance information
                if "cached" in result:
                    if result["cached"]:
                        st.caption(f"⚡ Response served from cache")
                    else:
                        st.caption(f"⏱️ Response time: {result.get('execution_time', 0):.2f} seconds")
                
                # Add assistant message to chat history
                st.session_state.messages.append({"role": "assistant", "content": result["response"]})
            
            except Exception as e:
                error_message = f"Error: {str(e)}"
                message_placeholder.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

with main_tabs[1]:  # Trends tab
    st.title("📊 Query Trends Dashboard")
    st.markdown("*Analytics and insights from user queries.*")
    
    # Initialize agent if not already initialized
    if st.session_state.agent is None:
        agent_initialized = initialize_agent()
        if not agent_initialized:
            st.stop()
    
    # Only show trends if Firebase is connected
    if st.session_state.firebase_client and st.session_state.firebase_client.is_connected:
        query_data = get_query_data()
        create_trend_visualizations(query_data)
    else:
        st.warning("Firebase connection is required to display trends. Currently running in demo mode.")
        # Show sample data for demo purposes
        st.info("Showing sample data for demonstration purposes.")
        # Generate some sample data
        sample_data = []
        for i in range(20):
            day = datetime.now() - timedelta(days=i)
            # Make sure all required fields are included in the sample data
            sample_data.append({
                "query": f"Sample query {i}",
                "response": f"Sample response {i}",
                "query_length": 20 + (i % 10),  # This field is needed
                "response_length": 100 + (i % 50),  # This field is needed
                "timestamp": day.isoformat(),
                "session_id": f"session_{i % 5}",
                "locations": [["London", "Manchester"][i % 2]],
                "skills": [["Python", "Java", "Frontend"][i % 3]],
                "ranks": [["Analyst", "Consultant", "Senior Consultant"][i % 3]]
            })
        create_trend_visualizations(sample_data) 