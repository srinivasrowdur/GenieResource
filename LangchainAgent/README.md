# Resource Management Agent

A specialized resource management agent that helps users find and manage resources based on various criteria such as location, rank, skill, and availability.

## Features

- **Natural Language Understanding**: Understands user queries in natural language and extracts structured information.
- **LLM-Enhanced Query Translation**: Uses large language models to handle typos, unconventional phrasing, and novel expressions.
- **Resource Search**: Finds resources based on location, rank, skill, and other criteria.
- **Availability Checking**: Checks resource availability for specific weeks.
- **Follow-up Queries**: Maintains context for follow-up queries, allowing for conversational interactions.
- **Human-friendly Responses**: Generates clear, concise, and human-friendly responses.
- **Rank Hierarchy Queries**: Support for queries about ranks above, below, or between specific ranks

## Architecture

The Resource Management Agent is built with a modular architecture consisting of the following components:

1. **Master Agent**: Orchestrates the flow of information between components.
2. **Query Translator**: Translates natural language queries into structured queries.
3. **Resource Fetcher**: Retrieves resource data from the database.
4. **Availability Checker**: Checks resource availability for specific time periods.
5. **Response Generator**: Generates human-friendly responses based on the results.

## Test-Driven Development (TDD)

This project follows Test-Driven Development principles:

1. Write tests first
2. Run the tests (they should fail)
3. Write the code to make the tests pass
4. Refactor the code
5. Repeat

## Components

### Query Translator

The Query Translator is responsible for extracting structured information from natural language queries. It identifies:

- **Location**: One or more of: London, Bristol, Manchester, Belfast, Oslo, Stockholm, Copenhagen
- **Rank**: Following the hierarchy from Partner to Analyst
- **Skill**: Technical skills (Frontend Developer, Backend Developer, etc.) or Business skills (Business Analyst, Product Manager, etc.)
- **Availability**: Week numbers mentioned in the query

The Query Translator uses two approaches:

1. **LLM-based Translation**: Uses Anthropic Claude to understand queries with typos, unconventional phrasing, and novel expressions.
2. **Rule-based Translation**: Falls back to regex patterns and predefined mappings when the LLM is unavailable.

Example output:
```json
{
  "location": ["London", "Bristol"],
  "rank": "Senior Consultant",
  "skill": "Frontend Developer",
  "availability": [1, 2, 3, 4]
}
```

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Firebase account (for database)
- Anthropic API key (for natural language processing)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/resource-management-agent.git
cd resource-management-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export ANTHROPIC_API_KEY=your_api_key
export FIREBASE_CREDENTIALS_PATH=path/to/your/credentials.json
```

### Running the Application

```bash
streamlit run app.py
```

### Running Tests

```bash
python -m unittest discover tests
```

### Testing the Query Translator

To test the Query Translator with both rule-based and LLM-based approaches:

```bash
python test_translator.py
```

## Usage Examples

- "Find frontend developers in London"
- "Show me consultants with AWS skills in Oslo"
- "Are there any partners in Manchester?"
- "Find senior consultants in Bristol available in Week 2"
- "Who are the analysts in Copenhagen?"

With LLM-based translation, the system can also handle queries with typos and unconventional phrasing:

- "Find frntend devs in Londn" (typos)
- "Show me ppl who know AWS in Osloo" (slang and typos)
- "Any1 who is a partner in Manchestr?" (shorthand and typo)

## Project Structure

```
LangchainAgent/
├── app.py                  # Streamlit application entry point
├── requirements.txt        # Project dependencies
├── README.md               # Project documentation
├── test_translator.py      # Script to test the QueryTranslator
├── src/                    # Source code
│   ├── __init__.py
│   ├── master_agent.py     # Master Agent component
│   ├── query_translator.py # Query Translator component
│   ├── resource_fetcher.py # Resource Fetcher component
│   ├── availability_checker.py # Availability Checker component
│   └── response_generator.py # Response Generator component
└── tests/                  # Test files
    ├── __init__.py
    ├── test_master_agent.py
    ├── test_query_translator.py
    ├── test_resource_fetcher.py
    ├── test_availability_checker.py
    ├── test_response_generator.py
    └── test_integration.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [LangChain](https://github.com/hwchase17/langchain) - For the language model integration
- [Anthropic Claude](https://www.anthropic.com/) - For the natural language processing
- [Streamlit](https://streamlit.io/) - For the web interface 