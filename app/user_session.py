"""User session management for anonymous users."""

from typing import Dict, Optional, Any
from fastapi import Request, Response
from datetime import datetime

from app.database import get_database
from app.device_fingerprint import (
    generate_device_fingerprint,
    generate_device_id,
    extract_device_features,
    parse_user_agent,
    is_valid_device_id,
    extract_fingerprint_from_device_id
)


class UserSessionManager:
    """Manages anonymous user sessions."""
    
    def __init__(self):
        self.db = get_database()
        self.cookie_name = "device_id"
        self.cookie_max_age = 30 * 24 * 60 * 60  # 30 days
    
    def get_or_create_user(self, request: Request, response: Response) -> Dict:
        """
        Get existing user or create new one based on device fingerprint.
        
        Args:
            request: FastAPI Request object
            response: FastAPI Response object (for setting cookies)
            
        Returns:
            User data dictionary
        """
        # 1. Try to get device_id from cookie
        device_id = request.cookies.get(self.cookie_name)
        
        if device_id and is_valid_device_id(device_id):
            # Check if user exists in database
            user = self.db.get_user_by_device_id(device_id)
            if user:
                # Update last_seen
                self.db.update_user_last_seen(device_id)
                # Refresh cookie
                self._set_device_cookie(response, device_id)
                return user
        
        # 2. Generate device fingerprint
        fingerprint = generate_device_fingerprint(request)
        
        # 3. Try to find existing user by fingerprint
        existing_user = self.db.get_user_by_fingerprint(fingerprint)
        
        if existing_user:
            # Found existing user with same fingerprint
            # This could be a returning user who cleared cookies
            device_id = existing_user["device_id"]
            self.db.update_user_last_seen(device_id)
            self._set_device_cookie(response, device_id)
            return existing_user
        
        # 4. Create new user
        device_id = generate_device_id(fingerprint)
        
        # Extract device features for user_data
        device_features = extract_device_features(request)
        user_agent_info = parse_user_agent(device_features["user_agent"])
        
        user_data = {
            "device_info": {
                "browser": user_agent_info["browser"],
                "os": user_agent_info["os"],
                "user_agent": device_features["user_agent"],
                "language": device_features["accept_language"]
            },
            "first_visit": datetime.now().isoformat(),
            "preferences": {}
        }
        
        user = self.db.create_user(device_id, fingerprint, user_data)
        
        # Set cookie
        self._set_device_cookie(response, device_id)
        
        return user
    
    def get_user_from_request(self, request: Request) -> Optional[Dict]:
        """
        Get user data from request (without creating new user).
        
        Args:
            request: FastAPI Request object
            
        Returns:
            User data dictionary or None
        """
        device_id = request.cookies.get(self.cookie_name)
        
        if device_id and is_valid_device_id(device_id):
            return self.db.get_user_by_device_id(device_id)
        
        return None
    
    def update_user_data(self, device_id: str, user_data: Dict) -> bool:
        """
        Update user's data.
        
        Args:
            device_id: Device ID
            user_data: New user data
            
        Returns:
            True if successful
        """
        return self.db.update_user_data(device_id, user_data)
    
    def set_user_preference(self, device_id: str, key: str, value: Any) -> bool:
        """
        Set a user preference.
        
        Args:
            device_id: Device ID
            key: Preference key
            value: Preference value
            
        Returns:
            True if successful
        """
        return self.db.set_preference(device_id, key, value)
    
    def get_user_preference(self, device_id: str, key: str) -> Optional[Any]:
        """
        Get a user preference.
        
        Args:
            device_id: Device ID
            key: Preference key
            
        Returns:
            Preference value or None
        """
        return self.db.get_preference(device_id, key)
    
    def get_all_user_preferences(self, device_id: str) -> Dict:
        """
        Get all preferences for a user.
        
        Args:
            device_id: Device ID
            
        Returns:
            Dictionary of preferences
        """
        return self.db.get_all_preferences(device_id)
    
    def delete_user_preference(self, device_id: str, key: str) -> bool:
        """
        Delete a user preference.
        
        Args:
            device_id: Device ID
            key: Preference key
            
        Returns:
            True if successful
        """
        return self.db.delete_preference(device_id, key)
    
    def track_user_action(self, device_id: str, action: str, data: Optional[Dict] = None):
        """
        Track a user action (for analytics).
        
        Args:
            device_id: Device ID
            action: Action name
            data: Optional action data
        """
        # Get current user data
        user = self.db.get_user_by_device_id(device_id)
        if not user:
            return
        
        user_data = user.get("user_data", {})
        
        # Initialize actions array if not exists
        if "actions" not in user_data:
            user_data["actions"] = []
        
        # Add new action
        action_entry = {
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        user_data["actions"].append(action_entry)
        
        # Keep only last 100 actions
        if len(user_data["actions"]) > 100:
            user_data["actions"] = user_data["actions"][-100:]
        
        # Update user data
        self.db.update_user_data(device_id, user_data)
    
    def get_user_stats(self) -> Dict:
        """
        Get user statistics.
        
        Returns:
            Statistics dictionary
        """
        return self.db.get_user_stats(days=7)
    
    def _set_device_cookie(self, response: Response, device_id: str):
        """
        Set device_id cookie.
        
        Args:
            response: FastAPI Response object
            device_id: Device ID to set
        """
        response.set_cookie(
            key=self.cookie_name,
            value=device_id,
            max_age=self.cookie_max_age,
            httponly=True,  # Prevent XSS
            samesite="lax",  # CSRF protection
            secure=False,  # Set to True in production with HTTPS
            path="/"
        )
    
    def clear_device_cookie(self, response: Response):
        """
        Clear device_id cookie.
        
        Args:
            response: FastAPI Response object
        """
        response.delete_cookie(
            key=self.cookie_name,
            path="/"
        )


# Global session manager instance
_session_manager = None


def get_session_manager() -> UserSessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = UserSessionManager()
    return _session_manager
