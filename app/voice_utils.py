"""Voice processing utilities for speech-to-text and text-to-speech."""

import base64
import io
import os
from typing import Optional
import openai


def speech_to_text(audio_data: str, api_key: Optional[str] = None) -> str:
    """
    Convert speech to text using OpenAI Whisper API.
    
    Args:
        audio_data: Base64 encoded audio data (supports various formats: mp3, wav, webm, etc.)
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
    
    Returns:
        Transcribed text
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "OpenAI API key not found. Please set OPENAI_API_KEY environment variable."
        )
    
    # Decode base64 audio data
    audio_bytes = base64.b64decode(audio_data)
    
    # Create a file-like object
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.wav"  # OpenAI expects a filename
    
    # Use OpenAI Whisper API
    client = openai.OpenAI(api_key=api_key)
    
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    
    return transcript.text


def text_to_speech(text: str, api_key: Optional[str] = None, voice: str = "alloy") -> str:
    """
    Convert text to speech using OpenAI TTS API.
    
    Args:
        text: Text to convert to speech
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
    
    Returns:
        Base64 encoded audio data
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "OpenAI API key not found. Please set OPENAI_API_KEY environment variable."
        )
    
    # Use OpenAI TTS API
    client = openai.OpenAI(api_key=api_key)
    
    response = client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text
    )
    
    # Get audio bytes and encode to base64
    audio_bytes = response.content
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    return audio_base64


def get_available_voices() -> list:
    """
    Get list of available TTS voices.
    
    Returns:
        List of voice names
    """
    return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


# Optional: Add support for alternative STT/TTS providers if needed
def speech_to_text_alternative(audio_data: str) -> str:
    """
    Alternative STT implementation (placeholder for future providers).
    
    Could integrate:
    - Google Cloud Speech-to-Text
    - Azure Speech Services
    - AssemblyAI
    - etc.
    """
    raise NotImplementedError("Alternative STT provider not implemented yet")


def text_to_speech_alternative(text: str) -> str:
    """
    Alternative TTS implementation (placeholder for future providers).
    
    Could integrate:
    - Google Cloud Text-to-Speech
    - Azure Speech Services
    - ElevenLabs
    - etc.
    """
    raise NotImplementedError("Alternative TTS provider not implemented yet")
