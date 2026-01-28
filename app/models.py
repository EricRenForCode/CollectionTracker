"""Data models for tracking consumption and receipts."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """Model for a single transaction."""
    
    id: Optional[str] = None
    entity: str = Field(description="Entity identifier")
    transaction_type: Literal["consumed", "received"] = Field(description="Type of transaction")
    amount: float = Field(description="Transaction amount")
    description: Optional[str] = Field(default=None, description="Optional transaction description")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EntityStatistics(BaseModel):
    """Statistics for a single entity."""
    
    entity: str
    total_consumed: float = 0.0
    total_received: float = 0.0
    net_balance: float = 0.0
    transaction_count: int = 0
    last_transaction: Optional[datetime] = None


class VoiceRequest(BaseModel):
    """Request model for voice input."""
    
    audio_data: Optional[str] = Field(default=None, description="Base64 encoded audio data")
    text: Optional[str] = Field(default=None, description="Direct text input (alternative to audio)")
    session_id: Optional[str] = Field(default=None, description="Session identifier for context")


class VoiceResponse(BaseModel):
    """Response model for voice output."""
    
    text: str = Field(description="Text response")
    audio_data: Optional[str] = Field(default=None, description="Base64 encoded audio response")
    statistics: Optional[dict] = Field(default=None, description="Any relevant statistics")
    transaction_id: Optional[str] = Field(default=None, description="Transaction ID if a transaction was created")


class StatisticsQuery(BaseModel):
    """Query model for statistics requests."""
    
    entity: Optional[str] = Field(default=None, description="Specific entity or None for all")
    transaction_type: Optional[Literal["consumed", "received"]] = Field(default=None, description="Filter by transaction type")
    start_date: Optional[datetime] = Field(default=None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(default=None, description="End date for filtering")
