# Quick Start Guide

Get your voice assistant up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
# Using Poetry (recommended)
poetry install

# Or using pip
pip install -r requirements.txt
```

## Step 2: Set Up API Keys

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use your favorite editor
```

Required API keys:
- **DEEPSEEK_API_KEY**: Get from [DeepSeek Platform](https://platform.deepseek.com/)
- **OPENAI_API_KEY**: Get from [OpenAI Platform](https://platform.openai.com/) (for voice features)

Your `.env` file should look like:
```
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
OPENAI_API_KEY=sk-your-openai-key-here
```

## Step 3: Create Data Directory

```bash
mkdir -p data
```

## Step 4: Run the Example

Test that everything works:

```bash
# Using Poetry
poetry run python example_usage.py

# Or directly with Python
python example_usage.py
```

## Step 5: Start the Server

```bash
# Using Poetry
poetry run python -m app.server

# Or using uvicorn
poetry run uvicorn app.server:app --reload
```

The server will start at `http://localhost:8000`

## Step 6: Try the API

Open your browser and go to:
- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Example API Calls

### Using curl

```bash
# Record a consumption
curl -X POST "http://localhost:8000/chat?message=A%20consumed%20100%20units"

# Get statistics
curl -X GET "http://localhost:8000/statistics"

# Get recent transactions
curl -X GET "http://localhost:8000/transactions/recent?limit=5"
```

### Using Python requests

```python
import requests

# Record consumption
response = requests.post(
    "http://localhost:8000/chat",
    params={"message": "A consumed 100 units"}
)
print(response.json())

# Get statistics
response = requests.get("http://localhost:8000/statistics")
print(response.json())
```

## Common Commands

### Recording Transactions

- "A consumed 100 units"
- "B received 50 items"
- "C consumed 75 with description 'office supplies'"
- "D received 200"

### Getting Information

- "How much has A consumed?"
- "What are the statistics for B?"
- "Show me all statistics"
- "Who consumed the most?"
- "Compare entities by net balance"

## Troubleshooting

### "ModuleNotFoundError"
```bash
poetry install
```

### "API key not found"
Check your `.env` file exists and has the correct keys

### "Port 8000 already in use"
```bash
# Use a different port
poetry run uvicorn app.server:app --port 8001
```

### Check logs
The agent runs in verbose mode - check console output for detailed logs

## Next Steps

1. Explore the API documentation at `/docs`
2. Read the full README.md for more details
3. Customize prompts in `app/prompts.py`
4. Add new features by editing `app/agent.py`

## Need Help?

- Check the full [README.md](README.md) for detailed documentation
- Review the example script: `example_usage.py`
- Check API docs: http://localhost:8000/docs
