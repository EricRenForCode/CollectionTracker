# Voice Assistant - Collection Tracker

A voice-enabled assistant for tracking consumption and receipts with anonymous user support.

## 📁 Project Structure

```
voice-assistant/
├── app/                    # Main application code
│   ├── api/               # API endpoints and models
│   │   ├── server.py      # FastAPI application and routes
│   │   └── models.py      # Pydantic models for API
│   ├── auth/              # Authentication and user management
│   │   ├── device_fingerprint.py  # Device identification
│   │   ├── middleware.py          # User identification middleware
│   │   └── user_session.py        # Session management
│   ├── core/              # Core business logic
│   │   ├── agent.py       # Voice assistant agent
│   │   ├── llm_config.py  # LLM configuration
│   │   └── prompts.py     # Prompt templates
│   ├── storage/           # Data persistence layer
│   │   ├── database.py    # Database operations
│   │   └── storage.py     # Storage interface
│   └── utils/             # Utility functions
│       └── voice_utils.py # Voice processing utilities
├── frontend/              # Frontend files
│   └── chat-ui.html       # Web chat interface
├── tests/                 # Test files
│   ├── test_client.py
│   ├── test_collections.py
│   └── test_llm_parsing.py
├── docs/                  # Documentation
│   ├── en/               # English documentation
│   └── zh/               # Chinese documentation
├── scripts/              # Helper scripts
│   └── example_usage.py
├── data/                 # Runtime data (SQLite, JSON)
└── requirements.txt      # Python dependencies

```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Environment

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 3. Run the Server

**Development mode (auto-reload):**
```bash
uvicorn app.api.server:app --reload
```

**Production mode (with workers):**
```bash
uvicorn app.api.server:app --workers 4 --host 0.0.0.0 --port 8000
```

### 4. Access the Application

- **Web Interface**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📖 Documentation

- [English Documentation](docs/en/)
- [中文文档](docs/zh/)

## 🧪 Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python tests/test_client.py
```

## 🏗️ Architecture

### Module Organization

- **`app/api/`**: HTTP endpoints, request/response models
- **`app/auth/`**: User identification, device fingerprinting, session management
- **`app/core/`**: Business logic, LLM integration, agent processing
- **`app/storage/`**: Data persistence (SQLite, transactions, user data)
- **`app/utils/`**: Shared utilities (voice processing, helpers)

### Key Features

- ✅ Anonymous user support with device fingerprinting
- ✅ Multi-language support (English, Chinese)
- ✅ Real-time chat interface
- ✅ Transaction tracking and statistics
- ✅ Collection management
- ✅ SQLite-based persistence

## 🔧 Configuration

Key configuration files:
- `.env` - Environment variables (API keys, settings)
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Project metadata

## 📊 Database

The application uses SQLite for data persistence:
- `data/users.db` - User and session data
- `data/voice_assistant.db` - Transactions and collections
- `data/transactions.json` - Legacy transaction storage

## 🌐 API Endpoints

- `GET /` - Serve web interface
- `GET /health` - Health check
- `POST /chat` - Chat with the assistant
- `GET /collections` - Get user collections
- `GET /transactions/recent` - Get recent transactions
- `POST /voice` - Process voice input
- `GET /api/user/me` - Get current user info

## 🤝 Contributing

See [docs/en/](docs/en/) for development guidelines.

## 📄 License

[Add your license here]
