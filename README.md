# Voice Assistant - Consumption & Receipt Tracker

A voice-enabled AI assistant built with LangChain and FastAPI that tracks consumption and receipt statistics for entities A, B, C, and D. Powered by DeepSeek API for language understanding and OpenAI's Whisper/TTS for voice capabilities.

## Features

- 🎤 **Voice Input/Output**: Speech-to-text and text-to-speech capabilities
- 📊 **Statistics Tracking**: Track consumption and receipts for entities A, B, C, D
- 🤖 **AI Agent**: Intelligent agent using DeepSeek API for natural language understanding
- 💬 **Conversational Interface**: Natural language interaction
- 📈 **Real-time Statistics**: Get instant statistics and comparisons
- 🔧 **Centralized Prompts**: Easy-to-manage prompt configuration

## Architecture

```
app/
├── server.py          # FastAPI server with REST endpoints
├── agent.py           # LangChain agent with tools
├── prompts.py         # Centralized prompt configuration
├── models.py          # Pydantic data models
├── storage.py         # JSON-based transaction storage
├── llm_config.py      # DeepSeek API integration
└── voice_utils.py     # Speech-to-text and text-to-speech utilities
```

## Installation

### Prerequisites

- Python 3.11 or higher
- Poetry (for dependency management)

### Setup Steps

1. **Clone and navigate to the project**

```bash
cd voice-assistant
```

2. **Install dependencies**

```bash
# Install Poetry if you haven't
pip install poetry

# Install project dependencies
poetry install
```

3. **Configure environment variables**

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API keys
# - DEEPSEEK_API_KEY: Get from https://platform.deepseek.com/
# - OPENAI_API_KEY: Get from https://platform.openai.com/
```

4. **Create data directory**

```bash
mkdir -p data
```

## Usage

### Starting the Server

```bash
# Using Poetry
poetry run python -m app.server

# Or using uvicorn directly
poetry run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
```

The server will start at `http://localhost:8000`

### API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### API Endpoints

#### 1. **Chat Endpoint** (Text-based)

```bash
POST /chat?message=A consumed 100 units

Response:
{
  "response": "Recorded: Entity A consumed 100.0 units. Transaction ID: abc-123",
  "success": true
}
```

#### 2. **Voice Endpoint** (Audio or Text)

```bash
POST /voice
Content-Type: application/json

{
  "text": "How much has entity B consumed?",
  "audio_data": null  # or base64 encoded audio
}

Response:
{
  "text": "Entity B has consumed 150 units in total.",
  "audio_data": null,  # base64 encoded audio if TTS is enabled
  "statistics": null,
  "transaction_id": null
}
```

#### 3. **Get Statistics**

```bash
GET /statistics?entity=A

Response:
{
  "statistics": {
    "A": {
      "entity": "A",
      "total_consumed": 100.0,
      "total_received": 50.0,
      "net_balance": -50.0,
      "transaction_count": 2,
      "last_transaction": "2026-01-27T10:30:00"
    }
  }
}
```

#### 4. **Recent Transactions**

```bash
GET /transactions/recent?limit=5

Response:
{
  "transactions": [
    {
      "id": "abc-123",
      "entity": "A",
      "transaction_type": "consumed",
      "amount": 100.0,
      "description": null,
      "timestamp": "2026-01-27T10:30:00"
    }
  ]
}
```

## Example Interactions

### Recording Transactions

- "A consumed 100 units"
- "Entity B received 50 items"
- "C consumed 75 with description 'monthly usage'"
- "D received 200"

### Getting Statistics

- "How much has A consumed?"
- "What's the total for entity B?"
- "Show me statistics for all entities"
- "Compare consumption across all entities"

### Comparisons

- "Who consumed the most?"
- "Which entity received the least?"
- "Compare net balances"

## Configuration

### Centralized Prompts

All prompts are managed in `app/prompts.py`. You can customize:

- `SYSTEM_PROMPT`: Main system instructions
- `TRANSACTION_EXTRACTION_PROMPT`: Transaction parsing logic
- `STATISTICS_QUERY_PROMPT`: Statistics generation
- Welcome and help messages
- Error messages

### DeepSeek API

The agent uses DeepSeek API (OpenAI-compatible) for language understanding. Configuration is in `app/llm_config.py`:

- **Reasoning LLM**: Lower temperature (0.3) for precise transaction processing
- **Conversation LLM**: Higher temperature (0.8) for natural responses

### Voice Configuration

Voice utilities in `app/voice_utils.py` use:
- **OpenAI Whisper**: Speech-to-text transcription
- **OpenAI TTS**: Text-to-speech synthesis
- Available voices: alloy, echo, fable, onyx, nova, shimmer

## Data Storage

Transactions are stored in JSON format at `data/transactions.json`. The storage layer:

- Automatically creates the data directory
- Supports filtering by entity, type, and date range
- Calculates real-time statistics
- Maintains transaction history

### Clear Data

```bash
DELETE /data/clear

Response:
{
  "message": "All data cleared successfully"
}
```

## Development

### Project Structure

- **Models** (`models.py`): Pydantic models for type safety
- **Storage** (`storage.py`): JSON-based persistence layer
- **Agent** (`agent.py`): LangChain agent with custom tools
- **Server** (`server.py`): FastAPI REST API
- **Prompts** (`prompts.py`): Centralized prompt management

### Adding New Features

1. **New Tools**: Add tools in `agent.py` `_create_tools()` method
2. **New Prompts**: Add prompts in `prompts.py`
3. **New Endpoints**: Add routes in `server.py`
4. **New Models**: Add models in `models.py`

## Docker Deployment

### Building the Image

```bash
docker build . -t voice-assistant
```

### Running the Container

```bash
docker run \
  -e DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -p 8000:8080 \
  -v $(pwd)/data:/code/data \
  voice-assistant
```

## Optional: LangSmith Integration

For debugging and monitoring, you can enable LangSmith:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<your-api-key>
export LANGSMITH_PROJECT=voice-assistant
```

Sign up at: https://smith.langchain.com/

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure `.env` file has valid API keys
2. **Import Errors**: Run `poetry install` to install dependencies
3. **Port Already in Use**: Change port in server startup command
4. **Data Directory**: Ensure `data/` directory exists

### Logs

The agent runs in verbose mode by default. Check console output for detailed execution logs.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
