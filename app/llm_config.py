"""DeepSeek LLM configuration and integration."""

import os
from typing import Optional
from langchain_openai import ChatOpenAI


def get_deepseek_llm(
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    api_key: Optional[str] = None
) -> ChatOpenAI:
    """
    Get a configured DeepSeek LLM instance.
    
    DeepSeek API is OpenAI-compatible, so we use ChatOpenAI with custom base_url.
    
    Args:
        model: Model name (default: deepseek-chat)
        temperature: Temperature for generation (0-2)
        max_tokens: Maximum tokens to generate
        api_key: DeepSeek API key (defaults to DEEPSEEK_API_KEY env var)
    
    Returns:
        Configured ChatOpenAI instance pointing to DeepSeek
    """
    api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        raise ValueError(
            "DeepSeek API key not found. Please set DEEPSEEK_API_KEY environment variable."
        )
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        openai_api_key=api_key,
        openai_api_base="https://api.deepseek.com",
        model_kwargs={}
    )


def get_reasoning_llm(
    temperature: float = 0.3,
    api_key: Optional[str] = None
) -> ChatOpenAI:
    """
    Get DeepSeek configured for reasoning tasks (lower temperature).
    
    Args:
        temperature: Temperature for generation (default: 0.3 for more focused responses)
        api_key: DeepSeek API key
    
    Returns:
        Configured ChatOpenAI instance
    """
    return get_deepseek_llm(
        model="deepseek-chat",
        temperature=temperature,
        api_key=api_key
    )


def get_conversation_llm(
    temperature: float = 0.8,
    api_key: Optional[str] = None
) -> ChatOpenAI:
    """
    Get DeepSeek configured for conversational tasks (higher temperature).
    
    Args:
        temperature: Temperature for generation (default: 0.8 for more creative responses)
        api_key: DeepSeek API key
    
    Returns:
        Configured ChatOpenAI instance
    """
    return get_deepseek_llm(
        model="deepseek-chat",
        temperature=temperature,
        api_key=api_key
    )
