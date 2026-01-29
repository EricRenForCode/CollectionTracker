"""Middleware for automatic user identification and session management."""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.user_session import get_session_manager


class UserIdentificationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically identifies users and attaches user info to request.
    
    This middleware:
    1. Checks for device_id cookie
    2. Generates device fingerprint if needed
    3. Creates or retrieves user from database
    4. Attaches user info to request.state
    5. Sets/refreshes device_id cookie
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.session_manager = get_session_manager()
        # Paths that don't need user identification
        self.excluded_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and attach user information."""
        
        # Skip middleware for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Skip for static files
        if request.url.path.startswith("/static/"):
            return await call_next(request)
        
        # Create a temporary response to set cookies
        # We'll merge cookies into the final response
        temp_response = Response()
        
        try:
            # Get or create user
            user = self.session_manager.get_or_create_user(request, temp_response)
            
            # Attach user info to request state
            request.state.user = user
            request.state.device_id = user["device_id"]
            
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error in UserIdentificationMiddleware: {e}")
            request.state.user = None
            request.state.device_id = None
        
        # Process the request
        response = await call_next(request)
        
        # Copy cookies from temp_response to actual response
        if hasattr(temp_response, "raw_headers"):
            for header_name, header_value in temp_response.raw_headers:
                if header_name == b"set-cookie":
                    response.raw_headers.append((header_name, header_value))
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware for anonymous users.
    
    Limits requests per device_id to prevent abuse.
    """
    
    def __init__(self, app: ASGIApp, max_requests_per_minute: int = 100):
        super().__init__(app)
        self.max_requests = max_requests_per_minute
        self.request_counts = {}  # In-memory counter (use Redis in production)
        self.excluded_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit before processing request."""
        
        # Skip middleware for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Get device_id from request state (set by UserIdentificationMiddleware)
        device_id = getattr(request.state, "device_id", None)
        
        if device_id:
            # Check rate limit
            count = self.request_counts.get(device_id, 0)
            
            if count >= self.max_requests:
                return Response(
                    content='{"error": "请求过于频繁，请稍后再试"}',
                    status_code=429,
                    media_type="application/json"
                )
            
            # Increment counter
            self.request_counts[device_id] = count + 1
        
        # Process request
        response = await call_next(request)
        
        return response
    
    def reset_counters(self):
        """Reset request counters (call this every minute)."""
        self.request_counts.clear()


# Helper function to get current user from request
def get_current_user(request: Request) -> dict:
    """
    Get current user from request state.
    
    Usage in route handlers:
        user = get_current_user(request)
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User dictionary or None
    """
    return getattr(request.state, "user", None)


def get_current_device_id(request: Request) -> str:
    """
    Get current device_id from request state.
    
    Usage in route handlers:
        device_id = get_current_device_id(request)
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Device ID string or None
    """
    return getattr(request.state, "device_id", None)


def require_user(request: Request) -> dict:
    """
    Require user to be identified (raise error if not).
    
    Usage in route handlers:
        user = require_user(request)
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User dictionary
        
    Raises:
        HTTPException: If user not found
    """
    from fastapi import HTTPException
    
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="无法识别设备，请启用 Cookie"
        )
    return user
