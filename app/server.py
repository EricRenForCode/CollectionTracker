from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes
from typing import Optional
from datetime import datetime
from pathlib import Path

from app.models import VoiceRequest, VoiceResponse, StatisticsQuery
from app.agent import create_voice_agent
from app.voice_utils import speech_to_text, text_to_speech
from app.storage import get_storage
from app.middleware import UserIdentificationMiddleware, get_current_device_id, get_current_user
from app.user_session import get_session_manager

app = FastAPI(
    title="Voice Assistant API",
    description="Voice assistant for tracking consumption and receipts statistics with anonymous user support",
    version="0.2.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add user identification middleware
app.add_middleware(UserIdentificationMiddleware)

# Initialize agent, storage, and session manager
agent = create_voice_agent()
storage = get_storage()
session_manager = get_session_manager()

# In-memory session history (per device_id)
sessions = {}

def get_session_history(device_id: str) -> list:
    """Get or create session history for a device."""
    if device_id not in sessions:
        sessions[device_id] = []
    return sessions[device_id]

def add_to_session_history(device_id: str, role: str, content: str):
    """Add a message to session history for a device."""
    history = get_session_history(device_id)
    history.append({"role": role, "content": content})
    # Keep only last 10 messages to avoid bloat
    if len(history) > 10:
        sessions[device_id] = history[-10:]

@app.get("/")
async def serve_chat_ui():
    """Serve the chat UI."""
    html_path = Path(__file__).parent.parent / "chat-ui.html"
    if html_path.exists():
        return FileResponse(html_path)
    return RedirectResponse("/docs")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "voice-assistant"}


@app.post("/voice", response_model=VoiceResponse)
async def process_voice(voice_request: VoiceRequest, request: Request) -> VoiceResponse:
    """
    Process voice input or text input and return response.
    
    - If audio_data is provided, it will be transcribed to text
    - The text is processed by the agent
    - Response can optionally include audio (TTS)
    """
    try:
        # Get device_id from request state (set by middleware)
        device_id = get_current_device_id(request)
        if not device_id:
            raise HTTPException(status_code=401, detail="无法识别设备")
        
        # Get input text (either from audio or direct text)
        if voice_request.audio_data:
            input_text = speech_to_text(voice_request.audio_data)
        elif voice_request.text:
            input_text = voice_request.text
        else:
            raise HTTPException(
                status_code=400,
                detail="Either audio_data or text must be provided"
            )
        
        # Process with agent
        history = get_session_history(device_id)
        lang = voice_request.language or "en"
        
        result = agent.process_message(input_text, device_id, history, lang=lang)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Agent processing failed")
            )
        
        response_text = result["response"]
        
        # Update history
        add_to_session_history(device_id, "user", input_text)
        add_to_session_history(device_id, "assistant", response_text)
        
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
async def chat(message: str, request: Request, lang: str = "en") -> dict:
    """
    Simple text chat endpoint (no voice).
    
    Args:
        message: User's text message
        request: FastAPI Request object
        lang: Language preference
    
    Returns:
        Agent's response
    """
    try:
        # Get device_id from request state
        device_id = get_current_device_id(request)
        if not device_id:
            raise HTTPException(status_code=401, detail="无法识别设备")
        
        history = get_session_history(device_id)
        result = agent.process_message(message, device_id, history, lang=lang)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Agent processing failed")
            )
        
        response_text = result["response"]
        
        # Update history
        add_to_session_history(device_id, "user", message)
        add_to_session_history(device_id, "assistant", response_text)
        
        return {
            "response": response_text,
            "success": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections")
async def get_collections(request: Request):
    """
    Get list of all items in the user's collection.
    
    Returns:
        List of collection items
    """
    try:
        device_id = get_current_device_id(request)
        if not device_id:
            raise HTTPException(status_code=401, detail="无法识别设备")
        
        entities = storage.get_entities(device_id)
        return {
            "collections": entities,
            "count": len(entities)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collections")
async def add_to_collection(entity: str, request: Request):
    """
    Add an item to the user's collection.
    
    Args:
        entity: Item name to add
        request: FastAPI Request object
    
    Returns:
        Success status and entity name
    """
    try:
        device_id = get_current_device_id(request)
        if not device_id:
            raise HTTPException(status_code=401, detail="无法识别设备")
        
        result = storage.add_entity(device_id, entity)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collections/{entity}")
async def remove_from_collection(entity: str, request: Request):
    """
    Remove an item from the user's collection.
    
    Args:
        entity: Item name to remove
        request: FastAPI Request object
    
    Returns:
        Success status
    """
    try:
        device_id = get_current_device_id(request)
        if not device_id:
            raise HTTPException(status_code=401, detail="无法识别设备")
        
        result = storage.remove_entity(device_id, entity)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/statistics")
async def get_statistics(request: Request, entity: Optional[str] = None):
    """
    Get statistics for entities.
    
    Args:
        request: FastAPI Request object
        entity: Optional entity filter (any item in collection, or None for all)
    
    Returns:
        Statistics data
    """
    try:
        device_id = get_current_device_id(request)
        if not device_id:
            raise HTTPException(status_code=401, detail="无法识别设备")
        
        if entity and not storage.entity_exists(device_id, entity):
            raise HTTPException(
                status_code=404,
                detail=f"Entity '{entity}' not found in collection"
            )
        
        stats = storage.get_statistics(device_id, entity=entity)
        
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
async def get_recent_transactions(request: Request, limit: int = 10):
    """
    Get recent transactions.
    
    Args:
        request: FastAPI Request object
        limit: Number of transactions to return (default: 10)
    
    Returns:
        List of recent transactions
    """
    try:
        device_id = get_current_device_id(request)
        if not device_id:
            raise HTTPException(status_code=401, detail="无法识别设备")
        
        transactions = storage.get_recent_transactions(device_id, limit=limit)
        
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
async def get_welcome(request: Request, lang: str = "en"):
    """Get welcome message."""
    device_id = get_current_device_id(request)
    if not device_id:
        raise HTTPException(status_code=401, detail="无法识别设备")
    return {"message": agent.get_welcome_message(device_id, lang=lang)}


@app.get("/help")
async def get_help(lang: str = "en"):
    """Get help message."""
    return {"message": agent.get_help_message(lang=lang)}


@app.delete("/data/clear")
async def clear_data(request: Request, include_collections: bool = False):
    """
    Clear all transaction data for current user.
    
    Args:
        request: FastAPI Request object
        include_collections: If True, also clear the collections. Default is False.
    
    WARNING: This will delete data!
    """
    try:
        device_id = get_current_device_id(request)
        if not device_id:
            raise HTTPException(status_code=401, detail="无法识别设备")
        
        if include_collections:
            storage.clear_all_including_collections(device_id)
            return {"message": "All data including collections cleared successfully"}
        else:
            storage.clear_all_data(device_id)
            return {"message": "All transaction data cleared successfully (collections preserved)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== New User-Related API Endpoints =====

@app.get("/api/user/me")
async def get_current_user_info(request: Request):
    """
    Get current anonymous user information.
    
    Returns:
        User information dictionary
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="无法识别设备")
    
    return {
        "success": True,
        "device_id": user["device_id"],
        "is_authenticated": False,
        "user_type": "anonymous",
        "created_at": user["created_at"],
        "last_seen": user["last_seen"],
        "session_count": user["session_count"],
        "message": "匿名用户" if "zh" in request.headers.get("accept-language", "en") else "Anonymous user"
    }


@app.post("/api/user/track")
async def track_user_action(request: Request, action: str, data: Optional[dict] = None):
    """
    Track a user action for analytics.
    
    Args:
        request: FastAPI Request object
        action: Action name (e.g., 'page_view', 'click', 'search')
        data: Optional action data
    
    Returns:
        Success status
    """
    device_id = get_current_device_id(request)
    if not device_id:
        raise HTTPException(status_code=401, detail="无法识别设备")
    
    session_manager.track_user_action(device_id, action, data)
    
    return {
        "success": True,
        "action": action,
        "recorded_at": datetime.now().isoformat()
    }


@app.post("/api/user/preferences")
async def update_user_preferences(request: Request, preferences: dict):
    """
    Update user preferences.
    
    Args:
        request: FastAPI Request object
        preferences: Dictionary of preference key-value pairs
    
    Returns:
        Success status with updated keys
    """
    device_id = get_current_device_id(request)
    if not device_id:
        raise HTTPException(status_code=401, detail="无法识别设备")
    
    updated = []
    for key, value in preferences.items():
        if session_manager.set_user_preference(device_id, key, value):
            updated.append(key)
    
    return {
        "success": True,
        "updated": updated
    }


@app.get("/api/user/preferences")
async def get_user_preferences(request: Request):
    """
    Get all user preferences.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Dictionary of preferences
    """
    device_id = get_current_device_id(request)
    if not device_id:
        raise HTTPException(status_code=401, detail="无法识别设备")
    
    preferences = session_manager.get_all_user_preferences(device_id)
    
    return {
        "success": True,
        "preferences": preferences
    }


@app.get("/api/analytics/dashboard")
async def get_analytics_dashboard(days: int = 7):
    """
    Get analytics dashboard data (simplified version without API key auth).
    
    Args:
        days: Number of days to include in statistics
    
    Returns:
        Analytics data
    """
    try:
        stats = session_manager.get_user_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
