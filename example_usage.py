"""Example usage script for the voice assistant.

This script demonstrates how to interact with the voice assistant programmatically.
"""

import os
from app.agent import create_voice_agent
from app.storage import get_storage


def main():
    """Run example interactions with the voice assistant."""
    
    print("=" * 60)
    print("Voice Assistant - Example Usage")
    print("=" * 60)
    print()
    
    # Create agent
    agent = create_voice_agent()
    storage = get_storage()
    
    # Clear any existing data for clean demo
    print("Clearing existing data...")
    storage.clear_all_data()
    print()
    
    # Show welcome message
    print("Agent: " + agent.get_welcome_message())
    print()
    
    # Example interactions
    examples = [
        "A consumed 100 units",
        "B received 150 items",
        "C consumed 75 units with description 'office supplies'",
        "D received 200 units",
        "How much has A consumed?",
        "What are the statistics for all entities?",
        "Who consumed the most?",
        "Compare entities by net balance",
    ]
    
    print("-" * 60)
    print("Running Example Interactions:")
    print("-" * 60)
    print()
    
    for i, example in enumerate(examples, 1):
        print(f"{i}. User: {example}")
        
        # Process message
        result = agent.process_message(example)
        
        if result["success"]:
            print(f"   Agent: {result['response']}")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")
        
        print()
    
    # Show final statistics
    print("-" * 60)
    print("Final Statistics:")
    print("-" * 60)
    print()
    
    stats = storage.get_statistics()
    for entity, stat in stats.items():
        print(f"Entity {entity}:")
        print(f"  Total Consumed: {stat.total_consumed}")
        print(f"  Total Received: {stat.total_received}")
        print(f"  Net Balance: {stat.net_balance}")
        print(f"  Transactions: {stat.transaction_count}")
        print()
    
    print("-" * 60)
    print("Example completed!")
    print()
    print("To run the server, use:")
    print("  python -m app.server")
    print()
    print("Then visit: http://localhost:8000/docs")
    print("-" * 60)


if __name__ == "__main__":
    # Check for API keys
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("⚠️  Warning: DEEPSEEK_API_KEY not found in environment variables")
        print("   Please set it in your .env file or environment")
        print()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not found in environment variables")
        print("   This is only needed for voice features (STT/TTS)")
        print("   Text-based features will work without it")
        print()
    
    if os.getenv("DEEPSEEK_API_KEY"):
        main()
    else:
        print("Cannot run examples without DEEPSEEK_API_KEY")
        print("Please create a .env file with your API key:")
        print()
        print("  cp .env.example .env")
        print("  # Edit .env and add your DEEPSEEK_API_KEY")
