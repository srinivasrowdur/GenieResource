"""
Resource Tools for LangGraph

This module contains tools for querying and managing resources in Firebase.
These tools are designed to be used with a LangGraph ReAct agent.
"""

from typing import Dict, List, Optional, Any, Union
from langchain_core.tools import BaseTool, Tool
from pydantic import BaseModel, Field

from src.firebase_utils import FirebaseClient

# Define input schemas for our tools
class QueryResourcesInput(BaseModel):
    locations: Optional[List[str]] = Field(None, description="List of locations to filter by")
    ranks: Optional[List[str]] = Field(None, description="List of ranks to filter by")
    skills: Optional[List[str]] = Field(None, description="List of skills to filter by")
    weeks: Optional[List[int]] = Field(None, description="List of week numbers to check availability for")
    availability_status: Optional[List[str]] = Field(None, description="List of availability statuses")
    min_hours: Optional[int] = Field(None, description="Minimum available hours required")
    limit: int = Field(20, description="Maximum number of results to return")

class SaveQueryInput(BaseModel):
    query: str = Field(..., description="The original user query")
    response: str = Field(..., description="The generated response")
    metadata: Dict[str, Any] = Field(..., description="Dictionary of metadata extracted from the query")
    session_id: str = Field(..., description="Unique session identifier")

class ResourceTools:
    """
    Tools for querying resources from Firebase and extracting metadata.
    These are wrapped as LangGraph tools to be used by the ReAct agent.
    """

    def __init__(self, firebase_client: FirebaseClient):
        """
        Initialize the ResourceTools.

        Args:
            firebase_client: A Firebase client instance
        """
        self.firebase_client = firebase_client
        self.cached_results = None
        self.last_query = None
        
        # Create tool objects using simpler Tool approach
        self.query_resources = Tool(
            name="query_resources",
            description="Query resources (employees) based on specified filters.",
            func=self._query_resources_impl
        )
        
        self.get_resource_metadata = Tool(
            name="get_resource_metadata",
            description="Get available metadata about resources, including locations, skills, and ranks.",
            func=self._get_resource_metadata_impl
        )
        
        self.save_query = Tool(
            name="save_query",
            description="Save a query and its response to Firebase for analytics.",
            func=self._save_query_impl
        )

    def _query_resources_impl(
        self, 
        locations: Optional[List[str]] = None,
        ranks: Optional[List[str]] = None,
        skills: Optional[List[str]] = None,
        weeks: Optional[List[int]] = None,
        availability_status: Optional[List[str]] = None,
        min_hours: Optional[int] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Implementation of query_resources tool.
        """
        # Store the query for caching purposes
        self.last_query = {
            "locations": locations,
            "ranks": ranks,
            "skills": skills,
            "weeks": weeks,
            "availability_status": availability_status,
            "min_hours": min_hours,
            "limit": limit
        }
        
        # If not connected to Firebase, return empty results
        if not self.firebase_client.is_connected:
            return {
                "results": [],
                "total": 0,
                "query": self.last_query,
                "error": "Not connected to Firebase"
            }
        
        try:
            # Call the Firebase client's get_resources method
            results = self.firebase_client.get_resources(
                locations=locations,
                ranks=ranks,
                skills=skills,
                weeks=weeks,
                availability_status=availability_status,
                min_hours=min_hours,
                limit=limit
            )
            
            # Store results in cache
            self.cached_results = results
            
            return {
                "results": results,
                "total": len(results),
                "query": self.last_query
            }
        except Exception as e:
            return {
                "results": [],
                "total": 0,
                "query": self.last_query,
                "error": str(e)
            }

    def _get_resource_metadata_impl(self) -> Dict[str, List[str]]:
        """
        Implementation of get_resource_metadata tool.
        """
        try:
            if not self.firebase_client.is_connected:
                return {
                    "locations": [],
                    "skills": [],
                    "ranks": [],
                    "error": "Not connected to Firebase"
                }
            
            return self.firebase_client.get_resource_metadata()
        except Exception as e:
            return {
                "locations": [],
                "skills": [],
                "ranks": [],
                "error": str(e)
            }

    def _save_query_impl(
        self, 
        query: str, 
        response: str, 
        metadata: Dict[str, Any], 
        session_id: str
    ) -> bool:
        """
        Implementation of save_query tool.
        """
        try:
            if not self.firebase_client.is_connected:
                return False
                
            self.firebase_client.save_query_data(
                query=query,
                response=response,
                metadata=metadata,
                session_id=session_id
            )
            return True
        except Exception as e:
            print(f"Error saving query: {e}")
            return False 