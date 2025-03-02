"""
Resource Genie - Streamlit UI for LangGraph Agent

This is the Streamlit UI for the Resource Genie application using the LangGraph-based agent.
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
from src.agent import ReActAgent
from src.firebase_utils import FirebaseClient
from langchain_anthropic import ChatAnthropic

# Load environment variables from .env file
load_dotenv()

# Set page config - must be the first Streamlit command
st.set_page_config(
    page_title="Resource Genie - LangGraph Implementation",
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
        background-color: #ffffff;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    div[data-testid="stHorizontalBlock"] > div.element-container:nth-child(1) div[data-testid="stVerticalBlock"] {
        background-color: #e6f7ff;
        border-radius: 8px;
        padding: 10px;
    }
    div[data-testid="stHorizontalBlock"] > div.element-container:nth-child(2) div[data-testid="stVerticalBlock"] {
        background-color: #fff2e6;
        border-radius: 8px;
        padding: 10px;
    }
    div[data-testid="stHorizontalBlock"] > div.element-container:nth-child(3) div[data-testid="stVerticalBlock"] {
        background-color: #e6ffe6;
        border-radius: 8px;
        padding: 10px;
    }
    div[data-testid="stHorizontalBlock"] > div.element-container:nth-child(4) div[data-testid="stVerticalBlock"] {
        background-color: #f0e6ff;
        border-radius: 8px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

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
# Try to get the path from Streamlit secrets if not in environment variables
if not firebase_creds_path and 'FIREBASE_CREDENTIALS_PATH' in st.secrets:
    firebase_creds_path = st.secrets['FIREBASE_CREDENTIALS_PATH']

# Function to extract metadata from the query and response
def extract_query_metadata(query, response):
    """
    Extract metadata from the query and response for analytics.
    
    Args:
        query: The user's query string
        response: The agent's response string
        
    Returns:
        Dictionary containing metadata
    """
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "locations": [],
        "ranks": [],
        "skills": [],
        "weeks": [],
        "availability_status": []
    }
    
    # Extract week numbers
    week_pattern = r"week\s+(\d+)"
    weeks = re.findall(week_pattern, query.lower())
    if weeks:
        metadata["weeks"] = [int(week) for week in weeks]
    
    # Check for availability status
    availability_keywords = {
        "available": "Available",
        "unavailable": "Unavailable",
        "partial": "Partial"
    }
    
    for keyword, status in availability_keywords.items():
        if keyword in query.lower():
            metadata["availability_status"].append(status)
    
    # Try to get reference metadata from Firebase
    if st.session_state.firebase_client and st.session_state.firebase_client.is_connected:
        try:
            ref_metadata = st.session_state.firebase_client.get_resource_metadata()
            
            # Check for locations in query
            for location in ref_metadata.get("locations", []):
                if location.lower() in query.lower():
                    metadata["locations"].append(location)
            
            # Check for ranks in query
            for rank in ref_metadata.get("ranks", []):
                if rank.lower() in query.lower():
                    metadata["ranks"].append(rank)
            
            # Check for skills in query
            for skill in ref_metadata.get("skills", []):
                if skill.lower() in query.lower():
                    metadata["skills"].append(skill)
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
        
        # Initialize the agent with caching enabled
        st.session_state.agent = ReActAgent(
            model=model, 
            firebase_client=firebase_client,
            use_cache=use_cache,
            cache_ttl=cache_ttl
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
    
    # Add date column
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    
    # Create metric cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Queries", len(df))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Unique Sessions", df['session_id'].nunique())
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Queries Today", len(df[df['date'] == datetime.now().date()]))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        avg_query_length = df['query'].str.len().mean()
        st.metric("Avg Query Length", f"{avg_query_length:.1f} chars")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Create tabs for different visualizations
    tabs = st.tabs(["Queries Over Time", "Popular Locations", "Popular Skills", "Popular Ranks"])
    
    # Queries over time visualization
    with tabs[0]:
        daily_counts = df.groupby('date').size().reset_index(name='count')
        daily_counts = daily_counts.sort_values('date')
        
        # Create line chart with Plotly
        fig = px.line(
            daily_counts,
            x='date',
            y='count',
            title='Number of Queries per Day',
            labels={'date': 'Date', 'count': 'Number of Queries'},
            markers=True
        )
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    
    # Create location distribution chart
    with tabs[1]:
        # Explode the locations list
        locations_list = df['metadata'].apply(lambda x: x.get('locations', []) if isinstance(x, dict) else [])
        locations = [item for sublist in locations_list for item in sublist]
        location_counts = Counter(locations)
        
        # Only show top 10 locations
        top_locations = dict(location_counts.most_common(10))
        
        if top_locations:
            fig = px.bar(
                x=list(top_locations.keys()),
                y=list(top_locations.values()),
                title='Top 10 Queried Locations',
                labels={'x': 'Location', 'y': 'Number of Queries'},
                color=list(top_locations.keys())
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No location data available.")
    
    # Create skills distribution chart
    with tabs[2]:
        # Explode the skills list
        skills_list = df['metadata'].apply(lambda x: x.get('skills', []) if isinstance(x, dict) else [])
        skills = [item for sublist in skills_list for item in sublist]
        skill_counts = Counter(skills)
        
        # Only show top 10 skills
        top_skills = dict(skill_counts.most_common(10))
        
        if top_skills:
            fig = px.bar(
                x=list(top_skills.keys()),
                y=list(top_skills.values()),
                title='Top 10 Queried Skills',
                labels={'x': 'Skill', 'y': 'Number of Queries'},
                color=list(top_skills.keys())
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No skill data available.")
    
    # Create ranks distribution chart
    with tabs[3]:
        # Explode the ranks list
        ranks_list = df['metadata'].apply(lambda x: x.get('ranks', []) if isinstance(x, dict) else [])
        ranks = [item for sublist in ranks_list for item in sublist]
        rank_counts = Counter(ranks)
        
        # Sort by a predefined order if necessary (higher to lower rank)
        rank_order = [
            "Partner", 
            "Associate Partner", 
            "Consulting Director", 
            "Management Consultant", 
            "Principal Consultant", 
            "Senior Consultant", 
            "Consultant", 
            "Analyst"
        ]
        
        # Filter and sort ranks
        sorted_ranks = {}
        for rank in rank_order:
            if rank in rank_counts:
                sorted_ranks[rank] = rank_counts[rank]
        
        if sorted_ranks:
            fig = px.bar(
                x=list(sorted_ranks.keys()),
                y=list(sorted_ranks.values()),
                title='Queried Ranks by Frequency',
                labels={'x': 'Rank', 'y': 'Number of Queries'},
                color=list(sorted_ranks.keys())
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No rank data available.")

# Create tabs for chat interface and trends dashboard
main_tabs = st.tabs(["Chat", "Trends"])

with main_tabs[0]:  # Chat tab
    # Display header
    st.title("🧞 Resource Genie")
    st.markdown("*Ask me about resource availability, skills, and locations.*")
    
    # Initialize agent if not already initialized
    if st.session_state.agent is None:
        agent_initialized = initialize_agent()
        if not agent_initialized:
            st.stop()

    # Display sidebar information
    with st.sidebar:
        st.title("Resource Genie 🧞")
        st.caption("LangGraph Implementation")
        
        # Session management
        st.subheader("Session")
        if st.button("Reset Session"):
            # Reset chat messages
            st.session_state.messages = [
                {"role": "assistant", "content": "Hello! I'm Resource Genie, your AI assistant for resource management. How can I help you today?"}
            ]
            # Reset the agent state
            if "agent" in st.session_state:
                st.session_state.agent.reset()
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
            if "agent" in st.session_state:
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
            if "agent" in st.session_state:
                st.session_state.agent.cache_ttl = cache_ttl
        
        # Clear cache button
        if st.button("Clear Cache"):
            if "agent" in st.session_state:
                st.session_state.agent.clear_cache()
                st.success("Cache cleared successfully!")
        
        # Cache statistics if agent is initialized
        if "agent" in st.session_state:
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
        st.warning("Firebase connection required to view trends. Currently running in demo mode.")

# Add footer
st.markdown("---")
st.markdown("Resource Genie LangGraph Implementation | Created with LangChain and Streamlit") 