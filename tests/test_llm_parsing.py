"""Test the LLM-based natural language parsing.

This demonstrates how the new LLM-based approach handles natural variations
that the old regex approach couldn't handle.
"""

import sys
from app.core.agent import create_voice_agent
from app.storage import get_storage


def test_natural_language():
    """Test various natural language inputs."""
    
    print("=" * 70)
    print("Testing LLM-Based Natural Language Parsing")
    print("=" * 70)
    print()
    
    # Clear data
    storage = get_storage()
    storage.clear_all_including_collections()
    
    agent = create_voice_agent()
    
    # Test cases that would fail with regex but work with LLM
    test_cases = [
        # Adding collections with natural variations
        ("Add coffee to my tracking list", "✓ Should add coffee"),
        ("I want to track tea and milk", "✓ Should add tea and milk"),
        ("Please register orange juice", "✓ Should add orange juice"),
        
        # Transactions with word numbers
        ("I consume coffee twice", "✓ Should record 2 coffees consumed"),
        ("I had three cups of tea", "✓ Should record 3 teas consumed"),
        ("Received five apples", "✓ Should record 5 apples received"),
        ("Got a couple of milk cartons", "✓ Should record 2 milk received"),
        ("Used several orange juice", "✓ Should record ~3 orange juice consumed"),
        
        # Natural variations
        ("I drank 2 coffees this morning", "✓ Should record 2 coffees consumed"),
        ("Bought 4 tea bags", "✓ Should record 4 tea received"),
        ("Ate one apple", "✓ Should record 1 apple consumed"),
        
        # Statistics with natural language
        ("How much coffee did I consume?", "✓ Should show coffee stats"),
        ("Tell me about tea", "✓ Should show tea stats"),
        ("Show me everything", "✓ Should show all stats"),
    ]
    
    print("Running test cases...\n")
    
    for i, (message, expected) in enumerate(test_cases, 1):
        print(f"{i}. Testing: \"{message}\"")
        print(f"   Expected: {expected}")
        
        try:
            result = agent.process_message(message)
            
            if result["success"]:
                print(f"   Result: {result['response']}")
                print("   ✓ SUCCESS\n")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
                print("   ✗ FAILED\n")
        except Exception as e:
            print(f"   Exception: {str(e)}")
            print("   ✗ FAILED\n")
    
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    # Show final collections
    collections = storage.get_entities()
    print(f"\nFinal collections ({len(collections)} items):")
    for item in collections:
        print(f"  - {item}")
    
    # Show transactions
    transactions = storage.get_recent_transactions(limit=20)
    print(f"\nTotal transactions recorded: {len(transactions)}")
    for t in transactions[-5:]:  # Show last 5
        print(f"  - {t.entity} {t.transaction_type} {t.amount}")
    
    print("\n" + "=" * 70)
    print("LLM-based parsing allows much more natural interaction!")
    print("=" * 70)


if __name__ == "__main__":
    print("\nStarting LLM-based parsing tests...")
    print("Note: Make sure DEEPSEEK_API_KEY is set in your environment\n")
    
    try:
        test_natural_language()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
