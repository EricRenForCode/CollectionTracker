# Voice Assistant - Project Overview

## What This Application Does

This is a **voice-enabled AI assistant** that helps you track consumption and receipt statistics for four entities: A, B, C, and D. Think of it as a smart bookkeeper that understands natural language.

### Key Capabilities

1. **Natural Language Understanding**: Talk to it naturally - "A consumed 100 units" or "How much has B received?"
2. **Voice Input/Output**: Speak to it using your microphone and hear responses (optional)
3. **Statistics Tracking**: Automatically tracks and calculates consumption, receipts, and net balances
4. **Intelligent Agent**: Uses DeepSeek AI to understand context and answer complex queries
5. **Comparisons**: "Who consumed the most?" or "Compare all entities"

## Project Structure

```
voice-assistant/
│
├── app/                          # Main application code
│   ├── server.py                 # FastAPI server (REST API endpoints)
│   ├── agent.py                  # LangChain agent with AI logic
│   ├── prompts.py               # ⭐ Centralized prompts (easy to customize!)
│   ├── models.py                 # Data models (Transaction, Statistics, etc.)
│   ├── storage.py                # JSON-based data storage
│   ├── llm_config.py            # ⭐ DeepSeek API configuration
│   └── voice_utils.py            # Speech-to-text & text-to-speech
│
├── data/                         # Transaction data (auto-created)
│   └── transactions.json         # All transaction records
│
├── .env                          # Your API keys (create from .env.example)
├── .env.example                  # Template for environment variables
│
├── pyproject.toml               # Poetry dependencies
├── requirements.txt             # Pip dependencies (alternative)
│
├── example_usage.py             # Run examples without server
├── test_client.py               # Test the running server
│
├── README.md                    # Full documentation
├── QUICKSTART.md                # 5-minute setup guide
└── PROJECT_OVERVIEW.md          # This file!
```

## Core Components Explained

### 1. Prompts (`app/prompts.py`) ⭐ CENTRALIZED!

All prompts in one place for easy customization:

- **SYSTEM_PROMPT**: Main instructions for the AI agent
- **TRANSACTION_EXTRACTION_PROMPT**: How to parse transaction requests
- **STATISTICS_QUERY_PROMPT**: How to answer statistics questions
- **WELCOME_MESSAGE**: First message users see
- **HELP_MESSAGE**: Instructions for users
- **Error messages**: Friendly error responses

**To customize**: Edit `app/prompts.py` - no code changes needed!

### 2. Agent (`app/agent.py`)

The brain of the application. Uses LangChain to:
- Create tools for recording transactions
- Create tools for querying statistics
- Process natural language with DeepSeek AI
- Decide which tools to use based on user input

**Tools available to the agent:**
- `record_consumption`: Track what entities consumed
- `record_receipt`: Track what entities received
- `get_statistics`: Get stats for one or all entities
- `get_recent_transactions`: Show recent activity
- `compare_entities`: Compare by consumption/receipts/balance

### 3. LLM Configuration (`app/llm_config.py`) ⭐ DEEPSEEK!

Uses DeepSeek API (OpenAI-compatible):
- **Reasoning LLM**: Temperature 0.3 (precise for transactions)
- **Conversation LLM**: Temperature 0.8 (natural for chat)

**API Endpoint**: `https://api.deepseek.com`

### 4. Storage (`app/storage.py`)

Simple JSON-based storage:
- Stores all transactions in `data/transactions.json`
- Calculates statistics on-the-fly
- Supports filtering by entity, type, date
- Easily upgradable to PostgreSQL/MongoDB later

### 5. Server (`app/server.py`)

FastAPI REST API with endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | Send text messages |
| `/voice` | POST | Send voice/text with audio response |
| `/statistics` | GET | Get entity statistics |
| `/transactions/recent` | GET | List recent transactions |
| `/welcome` | GET | Get welcome message |
| `/help` | GET | Get help message |
| `/data/clear` | DELETE | Clear all data |

### 6. Voice Utilities (`app/voice_utils.py`)

- **Speech-to-Text**: OpenAI Whisper API
- **Text-to-Speech**: OpenAI TTS API (6 voices available)
- Supports multiple audio formats

## Data Flow

```
User Input (Voice/Text)
    ↓
[Speech-to-Text if needed]
    ↓
DeepSeek AI Agent (understands intent)
    ↓
Agent selects appropriate tool:
  - Record transaction → Storage
  - Query statistics → Storage
  - Compare entities → Storage
    ↓
Generate natural language response
    ↓
[Text-to-Speech if needed]
    ↓
User receives response
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (Python) |
| AI Agent | LangChain |
| LLM | DeepSeek API |
| STT/TTS | OpenAI Whisper & TTS |
| Data Storage | JSON (upgradable) |
| API Server | Uvicorn |
| Dependency Management | Poetry |

## Configuration

### Environment Variables (.env)

```bash
# Required for AI understanding
DEEPSEEK_API_KEY=sk-xxx...

# Required only for voice features
OPENAI_API_KEY=sk-xxx...

# Optional: for debugging
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=xxx...
```

### Customization Points

1. **Prompts**: Edit `app/prompts.py`
2. **AI Model**: Edit `app/llm_config.py` (temperature, model name)
3. **Tools**: Add new tools in `app/agent.py`
4. **Endpoints**: Add new routes in `app/server.py`
5. **Storage**: Replace JSON with database in `app/storage.py`

## Example Use Cases

### Personal Finance
Track what you spent vs received each month

### Team Resource Management
Track resource consumption per team member

### Inventory Management
Track items consumed vs received for entities A, B, C, D

### Budget Tracking
Monitor consumption against allocations

## API Examples

### Record a Transaction
```bash
POST /chat?message=A consumed 100 units

Response:
{
  "response": "Recorded: Entity A consumed 100.0 units.",
  "success": true
}
```

### Get Statistics
```bash
GET /statistics?entity=A

Response:
{
  "statistics": {
    "A": {
      "total_consumed": 100.0,
      "total_received": 50.0,
      "net_balance": -50.0,
      "transaction_count": 2
    }
  }
}
```

### Natural Language Query
```bash
POST /chat?message=Who consumed the most?

Response:
{
  "response": "Based on the data, Entity A consumed the most with 100 units.",
  "success": true
}
```

## Development Workflow

1. **Make changes** to code (prompts, tools, etc.)
2. **Restart server** (auto-reload with `--reload` flag)
3. **Test in browser** at http://localhost:8000/docs
4. **Or test with script**: `python test_client.py`

## Deployment Options

### Local
```bash
python -m app.server
```

### Docker
```bash
docker build -t voice-assistant .
docker run -p 8000:8080 voice-assistant
```

### Production (Cloud)
Deploy to:
- AWS (Elastic Beanstalk, ECS, Lambda)
- Google Cloud (Cloud Run, App Engine)
- Azure (App Service, Container Instances)
- Railway, Render, Fly.io, etc.

## Scaling Considerations

Current setup is great for:
- Personal use
- Small teams
- Prototyping
- Low-medium traffic

For production scale:
1. Replace JSON storage with PostgreSQL/MongoDB
2. Add caching (Redis)
3. Add authentication/authorization
4. Use async database drivers
5. Add rate limiting
6. Deploy with load balancer

## Security Notes

- **API Keys**: Never commit `.env` file
- **Data**: Currently no authentication - add it for production
- **Input Validation**: Models validate input, but add more for production
- **Rate Limiting**: Not implemented - add for public APIs

## Extending the System

### Add New Entities (beyond A, B, C, D)
1. Update `Literal["A", "B", "C", "D"]` in `models.py`
2. Update prompts in `prompts.py`
3. Update entity list in `storage.py`

### Add New Transaction Types
1. Add new type to `Literal["consumed", "received"]` in `models.py`
2. Update prompts and tools accordingly

### Add Database
1. Create database models with SQLAlchemy
2. Replace `storage.py` implementation
3. Add database connection in `server.py`

### Add Authentication
1. Install `python-jose`, `passlib`
2. Add auth middleware in `server.py`
3. Protect sensitive endpoints

## Troubleshooting

### "Cannot connect to server"
- Check if server is running: `python -m app.server`
- Check port 8000 is not in use

### "API key not found"
- Create `.env` file from `.env.example`
- Add your DEEPSEEK_API_KEY

### "Import errors"
- Run `poetry install` or `pip install -r requirements.txt`

### "Slow responses"
- DeepSeek API latency varies by region
- Consider adding caching for repeated queries

## Next Steps

1. ✅ Set up environment and API keys
2. ✅ Run example script to test
3. ✅ Start server and try API
4. 🎯 Customize prompts for your use case
5. 🎯 Add your own tools/features
6. 🎯 Deploy to production

## Questions?

- Check **QUICKSTART.md** for setup
- Check **README.md** for full docs
- Review code comments in each file
- Test with `example_usage.py` or `test_client.py`

---

**Built with**: LangChain, DeepSeek, FastAPI, OpenAI
**Created**: January 2026
**Version**: 0.1.0
