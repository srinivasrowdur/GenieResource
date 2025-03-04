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
from datetime import datetime
from dotenv import load_dotenv
from src.langgraph_agent import ReActAgentGraph
from src.firebase_utils import FirebaseClient
from langchain_anthropic import ChatAnthropic

# Load environment variables from .env file
load_dotenv()

# Set page config - must be the first Streamlit command
st.set_page_config(
    page_title="Resource Genie",
    page_icon="🧞",
    layout="wide"
)

# Get API keys and credentials paths
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

# Use the local credentials file in the LangchainAgent directory
firebase_creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                 "resgenie-e8ab5-firebase-adminsdk-fbsvc-eb9f384590.json")

# Verify the file exists
if not os.path.exists(firebase_creds_path):
    # Try the project root as a fallback
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    firebase_creds_path = os.path.join(project_root, "resgenie-e8ab5-firebase-adminsdk-fbsvc-eb9f384590.json")
    if not os.path.exists(firebase_creds_path):
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

# Function to initialize the agent
def initialize_agent():
    """Initialize the agent and Firebase client."""
    if not anthropic_api_key:
        st.error("ANTHROPIC_API_KEY not found. Please add it to your .env file.")
        return False
    
    try:
        # Initialize Firebase client
        firebase_client = FirebaseClient(credentials_path=firebase_creds_path)
        st.session_state.firebase_client = firebase_client
        
        # Initialize the model
        model = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            anthropic_api_key=anthropic_api_key,
            temperature=0
        )
        
        # Initialize the agent
        st.session_state.agent = ReActAgentGraph(
            model=model, 
            firebase_client=firebase_client,
            use_cache=True,
            cache_ttl=3600,
            verbose=True
        )
        return True
    
    except Exception as e:
        st.error(f"Error initializing agent: {e}")
        return False

# Title and description
st.title("🧞 Resource Genie")

# Initialize agent if not already initialized
if st.session_state.agent is None:
    agent_initialized = initialize_agent()
    if not agent_initialized:
        st.stop()

# Add information in the sidebar
with st.sidebar:
    st.title("About Resource Genie")
    st.markdown("Resource Genie helps you find the right resources for your project.")
    
    # Sample queries in an expander
    with st.expander("📝 Sample Queries", expanded=True):
        st.markdown("""
        Try these example queries:
        - Find frontend developers in London
        - Who are the consultants available in Week 3?
        - Show me Solution Architects in Oslo
        - Find employees with rank above consultant
        """)
    
    # Add helpful resource information in expandable sections
    if st.session_state.firebase_client and st.session_state.firebase_client.is_connected:
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

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Ask about employees..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Thinking..."):
            try:
                # Process the message with the agent
                result = st.session_state.agent.process_message(
                    prompt,
                    session_id=st.session_state.session_id
                )
                
                # Store query data in Firebase
                if st.session_state.firebase_client and st.session_state.firebase_client.is_connected:
                    metadata = {
                        "timestamp": datetime.now().isoformat(),
                        "query_length": len(prompt),
                        "response_length": len(result["response"])
                    }
                    st.session_state.firebase_client.save_query_data(
                        query=prompt,
                        response=result["response"],
                        metadata=metadata,
                        session_id=st.session_state.session_id
                    )
                
                # Display the response
                message_placeholder.markdown(result["response"])
                
                # Add assistant message to chat history
                st.session_state.messages.append({"role": "assistant", "content": result["response"]})
            
            except Exception as e:
                error_message = f"Error: {str(e)}"
                message_placeholder.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message}) 