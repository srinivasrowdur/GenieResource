# Resource Management Agent - Test-Driven Development Plan

## Overview

This document outlines our plan to rebuild the Resource Management Agent using test-driven development (TDD) principles. The agent will help users find and manage resources (employees) based on various criteria such as location, skills, rank, and availability.

## Core Components

1. **Master Agent**: The main orchestrator that:
   - Evaluates if a query is a resource-related query
   - Rejects non-resource queries with an appropriate message
   - Orchestrates the flow between components for resource queries

2. **Query Translator**: Converts natural language queries into structured JSON
   - Extracts locations, skills, ranks, and availability requirements
   - Handles follow-up queries by maintaining context

3. **Resource Fetcher**: Retrieves employee data based on structured queries
   - Executes Firebase queries efficiently
   - Caches results for follow-up queries

4. **Availability Checker**: Checks availability for specific employees
   - Only queries availability when explicitly requested
   - Reuses previous employee results for follow-up availability queries

5. **Response Generator**: Creates human-friendly responses
   - Summarizes results in a clear, readable format
   - Provides helpful suggestions when no results are found

## Test-Driven Development Approach

We'll follow these TDD steps for each component:

1. Write tests first
2. Implement minimal code to pass tests
3. Refactor while maintaining test coverage
4. Repeat for each component

## Test Cases

### 1. Master Agent Tests

```python
def test_master_agent_identifies_resource_query():
    # Test that the agent correctly identifies resource-related queries
    
def test_master_agent_rejects_non_resource_query():
    # Test that the agent rejects queries not related to resources
    
def test_master_agent_orchestrates_components():
    # Test that the agent correctly orchestrates the flow between components
```

### 2. Query Translator Tests

```python
def test_query_translator_extracts_location():
    # Test that the translator extracts location information
    
def test_query_translator_extracts_skills():
    # Test that the translator extracts skills information
    
def test_query_translator_extracts_rank():
    # Test that the translator extracts rank information
    
def test_query_translator_extracts_availability():
    # Test that the translator extracts availability information
    
def test_query_translator_handles_followup_queries():
    # Test that the translator maintains context for follow-up queries
```

### 3. Resource Fetcher Tests

```python
def test_resource_fetcher_executes_query():
    # Test that the fetcher executes Firebase queries correctly
    
def test_resource_fetcher_caches_results():
    # Test that the fetcher caches results for follow-up queries
    
def test_resource_fetcher_handles_empty_results():
    # Test that the fetcher handles empty results gracefully
```

### 4. Availability Checker Tests

```python
def test_availability_checker_queries_availability():
    # Test that the checker queries availability correctly
    
def test_availability_checker_reuses_employee_results():
    # Test that the checker reuses employee results for follow-up queries
    
def test_availability_checker_handles_missing_data():
    # Test that the checker handles missing availability data gracefully
```

### 5. Response Generator Tests

```python
def test_response_generator_formats_results():
    # Test that the generator formats results correctly
    
def test_response_generator_handles_empty_results():
    # Test that the generator handles empty results gracefully
    
def test_response_generator_includes_availability():
    # Test that the generator includes availability information when present
```

## Integration Tests

```python
def test_end_to_end_resource_query():
    # Test the entire flow for a resource query
    
def test_end_to_end_availability_query():
    # Test the entire flow for an availability query
    
def test_end_to_end_followup_query():
    # Test the entire flow for a follow-up query
```

## Implementation Plan

1. Set up the project structure and testing framework
2. Implement each component following TDD principles:
   - Write tests
   - Implement minimal code to pass tests
   - Refactor
3. Integrate components
4. Write integration tests
5. Refactor for performance and maintainability

## Project Structure

```
LangchainAgent/
├── tests/
│   ├── test_master_agent.py
│   ├── test_query_translator.py
│   ├── test_resource_fetcher.py
│   ├── test_availability_checker.py
│   ├── test_response_generator.py
│   └── test_integration.py
├── src/
│   ├── master_agent.py
│   ├── query_translator.py
│   ├── resource_fetcher.py
│   ├── availability_checker.py
│   └── response_generator.py
├── app.py
└── requirements.txt
```

## Timeline

1. **Week 1**: Set up project structure, write tests
2. **Week 2**: Implement components
3. **Week 3**: Integration and testing
4. **Week 4**: Refactoring and optimization

## Success Criteria

1. All tests pass
2. The agent correctly handles resource queries
3. The agent efficiently handles follow-up queries
4. The agent provides human-friendly responses
5. The code is maintainable and well-documented

# Resource Management Agent - Implementation Status

## Current Implementation

### Master Agent (Implemented)
The Master Agent has been implemented using LangGraph for workflow orchestration:

1. **State Management**
   - Maintains messages, queries, results, and session history
   - Enables context-aware follow-up queries
   - Tracks conversation flow

2. **LangGraph Workflow**
   - Node 1: Query Translation
   - Node 2: Resource Fetching
   - Node 3: Response Generation
   - Linear workflow with clear state transitions

3. **Session Management**
   - Maintains conversation context
   - Stores query history and results
   - Enables intelligent follow-up handling

### Components Status

1. **Query Translator**: ✅ Implemented
   - LLM-based translation
   - Rule-based fallback
   - Context-aware processing

2. **Resource Fetcher**: ✅ Implemented
   - Firebase integration
   - Result caching
   - Efficient querying

3. **Response Generator**: ✅ Implemented
   - Human-friendly responses
   - Context-aware suggestions
   - Clear formatting

## Next Steps

1. **Testing**
   - Add integration tests for the LangGraph workflow
   - Test state management and transitions
   - Validate session history handling

2. **Optimization**
   - Profile performance
   - Optimize state transitions
   - Enhance caching strategies

3. **Documentation**
   - Add workflow diagrams
   - Document state management
   - Create usage examples

# Plan for Storing User Queries and Responses in Firebase

## Overview
We need to store the user queries, AI responses, and associated metadata (tags, rank, location, skills, availability) in a Firebase collection. This data will be useful for analyzing user interactions, improving the system, and tracking usage patterns.

## Implementation Plan

### 1. Create a New Firebase Collection
- Create a new collection called `queries` in Firestore
- Each document will store:
  - `query`: The user's original question
  - `response`: The AI's response
  - `timestamp`: When the query was made
  - `tags`: Array of extracted tags/topics
  - `metadata`: Object containing:
    - `ranks`: Ranks mentioned or used in the query
    - `locations`: Locations mentioned or used in the query
    - `skills`: Skills mentioned or used in the query
    - `availability`: Availability criteria used in the query
  - `session_id`: Unique identifier for the user session

### 2. Create a Setup Script
- Write a script to initialize the `queries` collection
- Ensure proper indexing for efficient querying
- Add sample data for testing purposes

### 3. Update FirebaseClient Class
- Add a new method `save_query_data(query, response, metadata)` to save query information
- Extract metadata from query and response
- Store data in the `queries` collection

### 4. Modify the App.py Process Flow
- After a successful query and response:
  - Extract metadata from the query and response
  - Call the FirebaseClient method to save the data
  - Ensure this does not impact the user experience

### 5. Testing and Validation
- Test the system with various queries
- Verify data is properly stored in Firebase
- Check that all metadata is correctly extracted and saved

## Implementation Timeline
1. Setup Script: Create a script to initialize the collection (1 day)
2. Firebase Client Update: Add a new method to save query data (1 day)
3. App.py Integration: Modify app.py to extract and save query data (1 day)
4. Testing and Refinement: Test and refine the implementation (1-2 days)

## Data Schema

```json
{
  "query": "Find frontend developers in London",
  "response": "I found 3 frontend developers in London...",
  "timestamp": "2023-05-20T15:30:00Z",
  "tags": ["frontend", "london", "availability"],
  "metadata": {
    "ranks": [],
    "locations": ["London"],
    "skills": ["frontend"],
    "availability": {
      "weeks": [],
      "status": []
    }
  },
  "session_id": "user123-session456"
}
```

## Required Changes
1. Add new method to `firebase_utils.py`
2. Create initialization script for the collection
3. Modify app.py to call the new method
4. Implement metadata extraction from queries 