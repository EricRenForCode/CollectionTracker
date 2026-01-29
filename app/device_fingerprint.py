"""Device fingerprint generation for anonymous user identification."""

import hashlib
import secrets
from typing import Dict, Optional
from fastapi import Request


def generate_device_fingerprint(request: Request) -> str:
    """
    Generate a device fingerprint from request headers.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Device fingerprint string (16 characters)
    """
    # Collect features from request
    features = []
    
    # User-Agent
    user_agent = request.headers.get("user-agent", "")
    features.append(user_agent)
    
    # Accept-Language
    accept_language = request.headers.get("accept-language", "")
    features.append(accept_language)
    
    # Accept-Encoding
    accept_encoding = request.headers.get("accept-encoding", "")
    features.append(accept_encoding)
    
    # Client IP (optional, can be behind proxy)
    client_ip = get_client_ip(request)
    features.append(client_ip)
    
    # Combine all features
    feature_string = "|".join(features)
    
    # Generate SHA256 hash
    fingerprint_hash = hashlib.sha256(feature_string.encode()).hexdigest()
    
    # Take first 16 characters
    return fingerprint_hash[:16]


def generate_device_id(fingerprint: str) -> str:
    """
    Generate a unique device ID from fingerprint with random salt.
    
    Args:
        fingerprint: Device fingerprint string
        
    Returns:
        Device ID in format: device_{fingerprint}_{random_salt}
    """
    # Generate 4-byte random hex salt
    random_salt = secrets.token_hex(4)
    
    # Construct device ID
    device_id = f"device_{fingerprint}_{random_salt}"
    
    return device_id


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Handles X-Forwarded-For header for proxied requests.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Client IP address string
    """
    # Check for X-Forwarded-For header (from proxy/load balancer)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    # Check for X-Real-IP header
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct client
    if request.client:
        return request.client.host
    
    return "unknown"


def extract_device_features(request: Request) -> Dict[str, str]:
    """
    Extract device features from request for analysis or storage.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Dictionary of device features
    """
    return {
        "user_agent": request.headers.get("user-agent", ""),
        "accept_language": request.headers.get("accept-language", ""),
        "accept_encoding": request.headers.get("accept-encoding", ""),
        "client_ip": get_client_ip(request),
        "referer": request.headers.get("referer", ""),
        "origin": request.headers.get("origin", ""),
    }


def parse_user_agent(user_agent: str) -> Dict[str, str]:
    """
    Parse user agent string to extract browser and OS information.
    
    Simple parser - for production, consider using user-agents library.
    
    Args:
        user_agent: User agent string
        
    Returns:
        Dictionary with browser and os fields
    """
    ua_lower = user_agent.lower()
    
    # Detect browser
    browser = "Unknown"
    if "chrome" in ua_lower and "edg" not in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser = "Safari"
    elif "edg" in ua_lower:
        browser = "Edge"
    elif "opera" in ua_lower or "opr" in ua_lower:
        browser = "Opera"
    
    # Detect OS
    os_name = "Unknown"
    if "windows" in ua_lower:
        os_name = "Windows"
    elif "mac os" in ua_lower or "macos" in ua_lower:
        os_name = "macOS"
    elif "linux" in ua_lower:
        os_name = "Linux"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    
    return {
        "browser": browser,
        "os": os_name
    }


def is_valid_device_id(device_id: str) -> bool:
    """
    Validate device ID format.
    
    Args:
        device_id: Device ID string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not device_id:
        return False
    
    parts = device_id.split("_")
    
    # Should have format: device_{fingerprint}_{salt}
    if len(parts) != 3:
        return False
    
    # First part should be "device"
    if parts[0] != "device":
        return False
    
    # Fingerprint should be 16 hex characters
    if len(parts[1]) != 16:
        return False
    
    # Salt should be 8 hex characters (4 bytes)
    if len(parts[2]) != 8:
        return False
    
    # Validate hex format
    try:
        int(parts[1], 16)
        int(parts[2], 16)
    except ValueError:
        return False
    
    return True


def extract_fingerprint_from_device_id(device_id: str) -> Optional[str]:
    """
    Extract fingerprint from device ID.
    
    Args:
        device_id: Device ID string
        
    Returns:
        Fingerprint string or None if invalid
    """
    if not is_valid_device_id(device_id):
        return None
    
    parts = device_id.split("_")
    return parts[1]
