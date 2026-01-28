from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes
from typing import Optional

from app.models import VoiceRequest, VoiceResponse, StatisticsQuery
from app.agent import create_voice_agent
from app.voice_utils import speech_to_text, text_to_speech
from app.storage import get_storage

app = FastAPI(
    title="Voice Assistant API",
    description="Voice assistant for tracking consumption and receipts statistics",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = create_voice_agent()
storage = get_storage()

# In-memory session history
sessions = {}

def get_session_history(session_id: str) -> list:
    """Get or create session history."""
    if session_id not in sessions:
        sessions[session_id] = []
    return sessions[session_id]

def add_to_session_history(session_id: str, role: str, content: str):
    """Add a message to session history."""
    history = get_session_history(session_id)
    history.append({"role": role, "content": content})
    # Keep only last 10 messages to avoid bloat
    if len(history) > 10:
        sessions[session_id] = history[-10:]

@app.get("/")
async def redirect_root_to_docs() -> RedirectResponse:
    """Redirect root to API documentation."""
    return RedirectResponse("/docs")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "voice-assistant"}


@app.post("/voice", response_model=VoiceResponse)
async def process_voice(request: VoiceRequest) -> VoiceResponse:
    """
    Process voice input or text input and return response.
    
    - If audio_data is provided, it will be transcribed to text
    - The text is processed by the agent
    - Response can optionally include audio (TTS)
    """
    try:
        # Get input text (either from audio or direct text)
        if request.audio_data:
            input_text = speech_to_text(request.audio_data)
        elif request.text:
            input_text = request.text
        else:
            raise HTTPException(
                status_code=400,
                detail="Either audio_data or text must be provided"
            )
        
        # Process with agent
        session_id = request.session_id or "default"
        history = get_session_history(session_id)
        
        result = agent.process_message(input_text, history)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Agent processing failed")
            )
        
        response_text = result["response"]
        
        # Update history
        add_to_session_history(session_id, "user", input_text)
        add_to_session_history(session_id, "assistant", response_text)
        
        # Optionally generate audio response
        # audio_response = text_to_speech(response_text)  # Uncomment if needed
        
        return VoiceResponse(
            text=response_text,
            audio_data=None,  # Set to audio_response if TTS is enabled
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(message: str, session_id: str = "default") -> dict:
    """
    Simple text chat endpoint (no voice).
    
    Args:
        message: User's text message
        session_id: Optional session identifier
    
    Returns:
        Agent's response
    """
    try:
        history = get_session_history(session_id)
        result = agent.process_message(message, history)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Agent processing failed")
            )
        
        response_text = result["response"]
        
        # Update history
        add_to_session_history(session_id, "user", message)
        add_to_session_history(session_id, "assistant", response_text)
        
        return {
            "response": response_text,
            "success": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections")
async def get_collections():
    """
    Get list of all items in the user's collection.
    
    Returns:
        List of collection items
    """
    try:
        entities = storage.get_entities()
        return {
            "collections": entities,
            "count": len(entities)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collections")
async def add_to_collection(entity: str):
    """
    Add an item to the user's collection.
    
    Args:
        entity: Item name to add
    
    Returns:
        Success status and entity name
    """
    try:
        result = storage.add_entity(entity)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collections/{entity}")
async def remove_from_collection(entity: str):
    """
    Remove an item from the user's collection.
    
    Args:
        entity: Item name to remove
    
    Returns:
        Success status
    """
    try:
        result = storage.remove_entity(entity)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/statistics")
async def get_statistics(entity: Optional[str] = None):
    """
    Get statistics for entities.
    
    Args:
        entity: Optional entity filter (any item in collection, or None for all)
    
    Returns:
        Statistics data
    """
    try:
        if entity and not storage.entity_exists(entity):
            raise HTTPException(
                status_code=404,
                detail=f"Entity '{entity}' not found in collection"
            )
        
        stats = storage.get_statistics(entity=entity)
        
        # Convert to dict
        return {
            "statistics": {
                ent: {
                    "entity": stat.entity,
                    "total_consumed": stat.total_consumed,
                    "total_received": stat.total_received,
                    "net_balance": stat.net_balance,
                    "transaction_count": stat.transaction_count,
                    "last_transaction": stat.last_transaction.isoformat() if stat.last_transaction else None
                }
                for ent, stat in stats.items()
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/transactions/recent")
async def get_recent_transactions(limit: int = 10):
    """
    Get recent transactions.
    
    Args:
        limit: Number of transactions to return (default: 10)
    
    Returns:
        List of recent transactions
    """
    try:
        transactions = storage.get_recent_transactions(limit=limit)
        
        return {
            "transactions": [
                {
                    "id": t.id,
                    "entity": t.entity,
                    "transaction_type": t.transaction_type,
                    "amount": t.amount,
                    "description": t.description,
                    "timestamp": t.timestamp.isoformat()
                }
                for t in transactions
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/welcome")
async def get_welcome():
    """Get welcome message."""
    return {"message": agent.get_welcome_message()}


@app.get("/help")
async def get_help():
    """Get help message."""
    return {"message": agent.get_help_message()}


@app.delete("/data/clear")
async def clear_data(include_collections: bool = False):
    """
    Clear all transaction data.
    
    Args:
        include_collections: If True, also clear the collections. Default is False.
    
    WARNING: This will delete data!
    """
    try:
        if include_collections:
            storage.clear_all_including_collections()
            return {"message": "All data including collections cleared successfully"}
        else:
            storage.clear_all_data()
            return {"message": "All transaction data cleared successfully (collections preserved)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
