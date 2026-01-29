"""Simple test client for the voice assistant API.

This script demonstrates how to interact with the running server.
Make sure the server is running before executing this script.
"""

import requests
import json
from typing import Optional


class VoiceAssistantClient:
    """Client for interacting with the Voice Assistant API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def check_health(self) -> dict:
        """Check if the server is healthy."""
        response = requests.get(f"{self.base_url}/health")
        return response.json()
    
    def chat(self, message: str) -> dict:
        """Send a text message to the assistant."""
        response = requests.post(
            f"{self.base_url}/chat",
            params={"message": message}
        )
        return response.json()
    
    def get_statistics(self, entity: Optional[str] = None) -> dict:
        """Get statistics for entities."""
        url = f"{self.base_url}/statistics"
        if entity:
            url += f"?entity={entity}"
        response = requests.get(url)
        return response.json()
    
    def get_recent_transactions(self, limit: int = 10) -> dict:
        """Get recent transactions."""
        response = requests.get(
            f"{self.base_url}/transactions/recent",
            params={"limit": limit}
        )
        return response.json()
    
    def clear_data(self) -> dict:
        """Clear all data (use with caution!)."""
        response = requests.delete(f"{self.base_url}/data/clear")
        return response.json()
    
    def get_welcome(self) -> dict:
        """Get welcome message."""
        response = requests.get(f"{self.base_url}/welcome")
        return response.json()
    
    def get_help(self) -> dict:
        """Get help message."""
        response = requests.get(f"{self.base_url}/help")
        return response.json()


def run_tests():
    """Run a series of test interactions."""
    
    print("=" * 70)
    print("Voice Assistant API Test Client")
    print("=" * 70)
    print()
    
    # Create client
    client = VoiceAssistantClient()
    
    # Check health
    print("1. Checking server health...")
    try:
        health = client.check_health()
        print(f"   ✓ Server is {health['status']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        print("   Make sure the server is running: python -m app.server")
        return
    
    print()
    
    # Get welcome message
    print("2. Getting welcome message...")
    welcome = client.get_welcome()
    print(f"   {welcome['message']}")
    print()
    
    # Test interactions
    test_messages = [
        "A consumed 100 units",
        "B received 150 items",
        "C consumed 75 units",
        "D received 200 units",
        "How much has A consumed?",
        "Show me statistics for all entities",
        "Who consumed the most?",
    ]
    
    print("3. Testing chat interactions...")
    print("-" * 70)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. User: {message}")
        try:
            response = client.chat(message)
            if response.get("success"):
                print(f"   Agent: {response['response']}")
            else:
                print(f"   Error: {response}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print()
    print("-" * 70)
    
    # Get statistics
    print("\n4. Getting final statistics...")
    try:
        stats = client.get_statistics()
        print(json.dumps(stats, indent=2))
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print()
    
    # Get recent transactions
    print("5. Getting recent transactions...")
    try:
        transactions = client.get_recent_transactions(limit=5)
        print(f"   Found {len(transactions.get('transactions', []))} transactions")
        for t in transactions.get('transactions', [])[:3]:
            print(f"   - Entity {t['entity']} {t['transaction_type']} {t['amount']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print()
    print("=" * 70)
    print("Tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    print()
    print("Starting Voice Assistant API tests...")
    print("Note: Make sure the server is running before running this script")
    print("      Start server: python -m app.server")
    print()
    
    try:
        run_tests()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
