"""Test the new collection-based workflow.

This script tests the new functionality where users define their own collections.
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
    
    def get_collections(self) -> dict:
        """Get all collections."""
        response = requests.get(f"{self.base_url}/collections")
        return response.json()
    
    def add_to_collection(self, entity: str) -> dict:
        """Add an entity to the collection."""
        response = requests.post(
            f"{self.base_url}/collections",
            params={"entity": entity}
        )
        return response.json()
    
    def remove_from_collection(self, entity: str) -> dict:
        """Remove an entity from the collection."""
        response = requests.delete(f"{self.base_url}/collections/{entity}")
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
    
    def clear_data(self, include_collections: bool = False) -> dict:
        """Clear all data."""
        response = requests.delete(
            f"{self.base_url}/data/clear",
            params={"include_collections": include_collections}
        )
        return response.json()
    
    def get_welcome(self) -> dict:
        """Get welcome message."""
        response = requests.get(f"{self.base_url}/welcome")
        return response.json()


def run_collection_tests():
    """Run tests for the new collection workflow."""
    
    print("=" * 70)
    print("Voice Assistant Collection Workflow Tests")
    print("=" * 70)
    print()
    
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
    
    # Clear all data to start fresh
    print("2. Clearing all data (including collections)...")
    try:
        result = client.clear_data(include_collections=True)
        print(f"   ✓ {result['message']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print()
    
    # Test 1: Try to consume without collection
    print("3. Testing transaction without collection (should fail gracefully)...")
    response = client.chat("I consumed 2 coffee")
    print(f"   User: I consumed 2 coffee")
    print(f"   Agent: {response.get('response', response)}")
    print()
    
    # Test 2: Add items to collection using chat
    print("4. Adding items to collection via chat...")
    test_cases = [
        "Add coffee to my collection",
        "Track tea and milk",
        "Add orange juice"
    ]
    
    for message in test_cases:
        print(f"   User: {message}")
        response = client.chat(message)
        print(f"   Agent: {response.get('response', response)}")
    
    print()
    
    # Test 3: List collections
    print("5. Listing current collections...")
    response = client.chat("What's in my collection?")
    print(f"   User: What's in my collection?")
    print(f"   Agent: {response.get('response', response)}")
    print()
    
    # Also check via API
    collections = client.get_collections()
    print(f"   Via API: {collections}")
    print()
    
    # Test 4: Record transactions for items in collection
    print("6. Recording transactions for items in collection...")
    transactions = [
        "I consumed 2 coffee",
        "I received 5 tea",
        "I consumed 1 milk",
        "I consumed 3 orange juice",
    ]
    
    for message in transactions:
        print(f"   User: {message}")
        response = client.chat(message)
        print(f"   Agent: {response.get('response', response)}")
    
    print()
    
    # Test 5: Try to consume item NOT in collection
    print("7. Trying to consume item not in collection...")
    print(f"   User: I consumed 1 apple")
    response = client.chat("I consumed 1 apple")
    print(f"   Agent: {response.get('response', response)}")
    print()
    
    # Test 6: Get statistics
    print("8. Getting statistics...")
    print(f"   User: Show me statistics")
    response = client.chat("Show me statistics")
    print(f"   Agent: {response.get('response', response)}")
    print()
    
    # Test 7: Get statistics for specific item
    print("9. Getting statistics for specific item...")
    print(f"   User: How much coffee have I consumed?")
    response = client.chat("How much coffee have I consumed?")
    print(f"   Agent: {response.get('response', response)}")
    print()
    
    # Test 8: Remove item from collection
    print("10. Removing item from collection...")
    print(f"   User: Remove orange juice from my collection")
    response = client.chat("Remove orange juice from my collection")
    print(f"   Agent: {response.get('response', response)}")
    print()
    
    # Test 9: Final collections list
    print("11. Final collections list...")
    collections = client.get_collections()
    print(f"   Collections: {', '.join(collections['collections'])}")
    print(f"   Total items: {collections['count']}")
    print()
    
    # Test 10: Recent transactions
    print("12. Recent transactions...")
    transactions = client.get_recent_transactions(limit=10)
    print(f"   Total transactions: {len(transactions.get('transactions', []))}")
    for t in transactions.get('transactions', []):
        print(f"   - {t['entity']} {t['transaction_type']} {t['amount']}")
    
    print()
    print("=" * 70)
    print("All tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    print()
    print("Starting Collection Workflow tests...")
    print("Note: Make sure the server is running before running this script")
    print("      Start server: python -m app.server")
    print()
    
    try:
        run_collection_tests()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
