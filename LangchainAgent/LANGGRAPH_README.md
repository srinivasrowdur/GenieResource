# Resource Genie: LangGraph Implementation

This directory contains the LangGraph implementation of the Resource Genie application. This implementation follows the migration plan outlined in `newGraphPlan.md`.

## Overview

The LangGraph implementation uses a ReAct agent architecture to simplify the codebase while preserving all existing functionalities. Key benefits include:

- Simplified architecture using LangGraph's prebuilt ReAct agent
- Better reasoning capabilities
- Built-in state management
- Easier extensibility
- Alignment with the broader LangChain ecosystem

## Implementation Details

The implementation consists of several key components:

### 1. Tools

The tools are organized into two main categories:

- **Resource Tools** (`src/tools/resource_tools.py`): Tools for querying resources from Firebase and extracting metadata.
- **Query Tools** (`src/tools/query_tools.py`): Tools for translating natural language queries and generating responses.

### 2. Agent

The ReAct agent (`src/agent.py`) integrates these tools with a language model to create a powerful reasoning engine. The agent:

- Processes natural language queries
- Translates them into structured queries
- Fetches matching resources from Firebase
- Generates helpful, human-readable responses

### 3. Test Script

A test script (`test_langgraph_agent.py`) allows for testing the implementation with or without Firebase integration.

## Testing the Implementation

To test the current implementation, run:

```bash
# Test with a default query without Firebase
python test_langgraph_agent.py --no-firebase

# Test with a custom query
python test_langgraph_agent.py --no-firebase --query "Find senior consultants with Python skills"

# Test with Firebase integration (requires credentials)
python test_langgraph_agent.py

# Test with debug output
python test_langgraph_agent.py --debug
```

The test script provides an interactive mode where you can continue the conversation with follow-up questions.

## Implementation Status

This implementation now includes Phase 1 and Phase 2 of the migration plan, with Phase 3 in progress:

### Phase 1 (Completed)
- [x] Basic tool structure
- [x] Agent setup using LangChain's AgentExecutor
- [x] Query translation
- [x] Response generation
- [x] Basic testing framework

### Phase 2 (Completed)
- [x] Streamlit UI integration
- [x] Trends dashboard
- [x] Basic Firebase connection

### Phase 3 (In Progress)
- [x] Comprehensive testing framework
- [x] Unit tests for components
- [x] Integration tests 
- [x] Performance benchmark tests
- [x] Performance optimizations
  - [x] Response caching system
  - [ ] Additional performance improvements

The implementation currently supports:
- Natural language query translation
- Response generation
- Firebase integration (when enabled)
- Interactive testing
- Streamlit chat interface
- Query analytics and trends visualization
- Comprehensive test suite
- Response caching for improved performance

Future phases will include:
- [ ] CI/CD integration
- [ ] Advanced analytics features
- [ ] Enhanced caching strategies

## Running the Application

You can now run the application in two ways:

### 1. Test Script (CLI)

Run the test script for command-line testing:

```bash
# Test with a default query without Firebase
python test_langgraph_agent.py --no-firebase

# Test with a custom query
python test_langgraph_agent.py --no-firebase --query "Find senior consultants with Python skills"

# Test with Firebase integration (requires credentials)
python test_langgraph_agent.py

# Test with debug output
python test_langgraph_agent.py --debug
```

### 2. Streamlit App (Web UI)

Run the Streamlit app for a full web interface:

```bash
streamlit run langgraph_app.py
```

The Streamlit app provides:
- A chat interface for interacting with the agent
- A trends dashboard for analytics
- Resource information in the sidebar

## Testing Framework

The project now includes a comprehensive testing framework in the `tests/langgraph_tests` directory:

### Unit Tests

- `test_agent.py`: Tests for the ReActAgent class
- `test_resource_tools.py`: Tests for the ResourceTools class
- `test_query_tools.py`: Tests for the QueryTools class

### Integration Tests

- `test_integration.py`: End-to-end tests for the entire system

### Performance Testing

- `performance_test.py`: Benchmarking script for measuring response times and throughput

### Running Tests

You can run all tests using the provided script:

```bash
# Navigate to the tests directory
cd tests

# Run all tests
./run_all_tests.sh

# Install requirements and run tests
./run_all_tests.sh --install

# Run tests including performance tests
./run_all_tests.sh --performance
```

The test suite uses mock objects to simulate Firebase and model responses, allowing for fast and reliable testing without external dependencies. For performance testing or full integration testing, you can configure the tests to use real dependencies.

## Performance Optimizations

The LangGraph implementation now includes performance optimizations to improve response times and reduce resource usage:

### Response Caching

The implementation includes a sophisticated caching system for responses:

- **Query Caching**: Identical or similar queries are served from cache to reduce response time
- **TTL Management**: Cached responses expire after a configurable time period (default: 1 hour)
- **Cache Controls**: The Streamlit UI provides controls to enable/disable caching, adjust TTL, and clear the cache
- **Cache Statistics**: Real-time metrics showing cache hit rate, size, and performance impact

Key benefits of the caching system:
- Significantly faster response times for repeated queries (often 10-100x faster)
- Reduced API costs when using paid LLM services
- Lower compute requirements for high-traffic deployments

### Performance Test Suite

A performance testing framework is included:
- Benchmark different types of queries
- Compare performance with and without caching
- Generate detailed performance metrics
- Run with or without Firebase integration

To run performance tests:

```bash
cd tests
./run_all_tests.sh --performance
```

## Next Steps

1. Complete the remaining items in Phase 3, focusing on performance optimizations
2. Implement CI/CD integration for automated testing
3. Enhance the application with advanced features from Phase 4
4. Optimize performance for production use

## Comparing with Original Implementation

The LangGraph implementation differs from the original implementation in several ways:

1. **Architecture**: Uses a simpler, more modular architecture based on LangGraph's ReAct agent pattern.
2. **State Management**: Leverages LangGraph's built-in state management instead of custom state handling.
3. **Tool Definition**: Tools are defined using LangGraph's tool decorators for better integration.
4. **Reasoning Process**: The ReAct agent provides more transparent reasoning through a think-act-observe cycle.

## Next Steps

1. Complete the remaining phases of the migration plan
2. Integrate the agent with the Streamlit UI
3. Enhance test coverage
4. Optimize performance for production use 