"""
Resource Fetcher module for retrieving resources from Firebase based on structured queries.
"""

import logging
from typing import Dict, List, Optional, Any, Union, Set
import json

from src.firebase_utils import FirebaseClient

class ResourceFetcher:
    """
    A class for fetching employee resources based on structured queries
    """

    def __init__(self, firebase_client: FirebaseClient):
        """
        Initialize the ResourceFetcher.

        Args:
            firebase_client: A Firebase client instance
        """
        self.firebase_client = firebase_client
        self.cached_results = None
        self.last_query = None
        self.logger = logging.getLogger(__name__)

    def fetch_resources(
        self, 
        query_dict=None,
        locations: Optional[List[str]] = None,
        ranks: Optional[List[str]] = None,
        skills: Optional[List[str]] = None,
        weeks: Optional[List[int]] = None,
        availability_status: Optional[List[str]] = None,
        min_hours: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Fetch employees based on query parameters.

        Args:
            query_dict: Optional dictionary containing all query parameters
            locations: List of locations to filter by
            ranks: List of ranks to filter by
            skills: List of skills to filter by
            weeks: List of week numbers to check availability for
            availability_status: List of availability statuses to filter by
            min_hours: Minimum available hours required
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Dict containing employees and total_count
        """
        # Handle if a complete query dictionary is passed
        if query_dict:
            locations = query_dict.get('locations', locations)
            ranks = query_dict.get('ranks', ranks)
            skills = query_dict.get('skills', skills)
            weeks = query_dict.get('weeks', weeks)
            availability_status = query_dict.get('availability_status', availability_status)
            min_hours = query_dict.get('min_hours', min_hours)
        
        # Expand geographic regions into their component cities
        if locations:
            expanded_locations = []
            for location in locations:
                if location:  # Check for None
                    location_lower = location.lower()
                    if location_lower in ['nordics', 'nordic', 'nordic countries', 'scandinavia']:
                        expanded_locations.extend(['Oslo', 'Stockholm', 'Copenhagen'])
                    elif location_lower in ['uk', 'united kingdom', 'britain']:
                        expanded_locations.extend(['London', 'Manchester', 'Belfast', 'Bristol'])
                    elif location_lower in ['us', 'usa', 'united states', 'america']:
                        expanded_locations.extend(['New York', 'Chicago', 'San Francisco'])
                    else:
                        expanded_locations.append(location)
            locations = expanded_locations
            
        # Normalize ranks to match exact database values
        if ranks:
            normalized_ranks = []
            # Special handling for skills that might be mistakenly classified as ranks
            if skills is None:
                skills = []
                
            for rank in ranks:
                if rank:  # Check for None
                    rank_lower = rank.lower()
                    # Check for skills that might be misclassified as ranks
                    if any(x in rank_lower for x in ['agile coach', 'scrum master', 'data engineer', 'cloud engineer']):
                        # Move these to skills instead
                        skills.append(rank)
                        continue
                        
                    if 'partner' in rank_lower and not any(x in rank_lower for x in ['associate', 'consulting']):
                        normalized_ranks.append('Partner')
                    elif any(x in rank_lower for x in ['associate partner', 'consulting director']):
                        normalized_ranks.extend(['Associate Partner', 'Consulting Director'])
                    elif 'management consultant' in rank_lower:
                        normalized_ranks.append('Management Consultant')
                    elif 'principal' in rank_lower:
                        normalized_ranks.append('Principal Consultant')
                    elif 'senior' in rank_lower:
                        normalized_ranks.append('Senior Consultant')
                    elif 'consultant' in rank_lower and not any(x in rank_lower for x in ['senior', 'principal', 'management']):
                        normalized_ranks.append('Consultant')
                    elif 'analyst' in rank_lower:
                        normalized_ranks.append('Analyst')
                    else:
                        normalized_ranks.append(rank)  # keep original if no match
                        
            ranks = normalized_ranks if normalized_ranks else None
            
        self.logger.debug(f"Fetching employees with params: locations={locations}, ranks={ranks}, skills={skills}, weeks={weeks}, availability_status={availability_status}, min_hours={min_hours}")
        
        # Store the current query for potential follow-up queries
        self.last_query = {
            "locations": locations,
            "ranks": ranks,
            "skills": skills,
            "weeks": weeks,
            "availability_status": availability_status,
            "min_hours": min_hours
        }
        
        # Fetch employees with the provided filters
        try:
            employees = self.firebase_client.fetch_employees(
                locations=locations,
                ranks=ranks,
                skills=skills,
                weeks=weeks,
                availability_status=availability_status,
                min_hours=min_hours,
                limit=limit,
                offset=offset
            )
            
            total_count = len(employees)
            
            # Cache the results for potential follow-up queries
            self.cached_results = employees
            
            return {
                "employees": employees,
                "total_count": total_count
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.logger.error(f"Error fetching employees: {str(e)}")
            return {
                "employees": [],
                "total_count": 0,
                "error": str(e)
            }

    def filter_cached_results(
        self,
        follow_up_locations: Optional[List[str]] = None,
        follow_up_ranks: Optional[List[str]] = None,
        follow_up_skills: Optional[List[str]] = None,
        follow_up_weeks: Optional[List[int]] = None,
        follow_up_availability_status: Optional[List[str]] = None,
        follow_up_min_hours: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Filter the cached results from a previous query for follow-up queries.

        Args:
            follow_up_locations: Additional locations to filter by
            follow_up_ranks: Additional ranks to filter by
            follow_up_skills: Additional skills to filter by
            follow_up_weeks: Additional weeks to check availability for
            follow_up_availability_status: Additional availability statuses to filter by
            follow_up_min_hours: Updated minimum hours requirement
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Dict containing filtered resources and total_count
        """
        if not self.cached_results or not self.last_query:
            self.logger.warning("No cached results available for filtering. Performing a new query.")
            return self.fetch_resources(
                locations=follow_up_locations,
                ranks=follow_up_ranks,
                skills=follow_up_skills,
                weeks=follow_up_weeks,
                availability_status=follow_up_availability_status,
                min_hours=follow_up_min_hours,
                limit=limit,
                offset=offset
            )

        # Combine the original query parameters with the follow-up parameters
        combined_locations = self._combine_params(self.last_query.get("locations"), follow_up_locations)
        combined_ranks = self._combine_params(self.last_query.get("ranks"), follow_up_ranks)
        combined_skills = self._combine_params(self.last_query.get("skills"), follow_up_skills)
        combined_weeks = self._combine_params(self.last_query.get("weeks"), follow_up_weeks)
        combined_availability_status = self._combine_params(self.last_query.get("availability_status"), follow_up_availability_status)
        
        # Use the follow-up min_hours if specified, otherwise use the original
        combined_min_hours = follow_up_min_hours if follow_up_min_hours is not None else self.last_query.get("min_hours")

        # Perform a new query with the combined parameters
        return self.fetch_resources(
            locations=combined_locations,
            ranks=combined_ranks,
            skills=combined_skills,
            weeks=combined_weeks,
            availability_status=combined_availability_status,
            min_hours=combined_min_hours,
            limit=limit,
            offset=offset
        )

    def _combine_params(self, original: Optional[List], follow_up: Optional[List]) -> Optional[List]:
        """
        Combine original and follow-up parameters, removing duplicates.

        Args:
            original: Original parameter values
            follow_up: Follow-up parameter values

        Returns:
            Combined list of parameter values
        """
        if not original and not follow_up:
            return None
        
        if not original:
            return follow_up
        
        if not follow_up:
            return original
        
        # Combine the lists and remove duplicates
        return list(set(original + follow_up))
