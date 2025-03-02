#!/bin/bash

# Run all LangGraph tests

# Set script directory as working directory
cd "$(dirname "$0")"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}======================================${NC}"
echo -e "${YELLOW}Running LangGraph Implementation Tests${NC}"
echo -e "${YELLOW}======================================${NC}"

# Check if python exists
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed or not in PATH${NC}"
    exit 1
fi

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate || {
    echo -e "${RED}Failed to activate virtual environment${NC}"
    exit 1
}

# Install requirements if needed
if [ "$1" == "--install" ]; then
    echo -e "${YELLOW}Installing requirements...${NC}"
    pip install -r ../requirements.txt
fi

# Run unit tests
echo -e "\n${YELLOW}Running unit tests...${NC}"
python -m unittest langgraph_tests.test_agent
python -m unittest langgraph_tests.test_resource_tools
python -m unittest langgraph_tests.test_query_tools

# Run integration tests
echo -e "\n${YELLOW}Running integration tests...${NC}"
python -m unittest langgraph_tests.test_integration

# Run performance tests if requested
if [ "$1" == "--performance" ] || [ "$2" == "--performance" ]; then
    echo -e "\n${YELLOW}Running performance tests...${NC}"
    python langgraph_tests/performance_test.py --runs 1 --verbose
fi

# Run the full test suite
echo -e "\n${YELLOW}Running full test suite...${NC}"
python langgraph_tests/run_tests.py

echo -e "\n${GREEN}All tests completed!${NC}"

# Deactivate the virtual environment
deactivate

# Give execution hints
echo -e "\n${YELLOW}Usage:${NC}"
echo -e "  ${GREEN}./run_all_tests.sh${NC} - Run all tests"
echo -e "  ${GREEN}./run_all_tests.sh --install${NC} - Install requirements and run tests"
echo -e "  ${GREEN}./run_all_tests.sh --performance${NC} - Run tests including performance tests" 