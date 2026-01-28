"""Voice assistant agent for processing user messages."""

import re
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from app.storage import get_storage
from app.models import Transaction
from app.llm_config import get_reasoning_llm
from app.prompts import (
    SYSTEM_PROMPT,
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    ERROR_ENTITY_NOT_FOUND,
    ERROR_AMOUNT_NOT_FOUND,
    ERROR_TRANSACTION_TYPE,
    ERROR_ENTITY_NOT_IN_COLLECTION,
    ERROR_NO_COLLECTIONS,
    LLM_PARSING_PROMPT
)


# Pydantic models for structured LLM output
class ParsedIntent(BaseModel):
    """Structured representation of user intent."""
    intent_type: Literal[
        "add_collection", 
        "remove_collection", 
        "list_collections",
        "record_transaction",
        "get_statistics",
        "help",
        "general"
    ] = Field(description="The type of intent detected")
    
    entities: List[str] = Field(
        default_factory=list,
        description="List of entity/item names mentioned (e.g., ['coffee', 'tea'])"
    )
    
    transaction_type: Optional[Literal["consumed", "received"]] = Field(
        default=None,
        description="Type of transaction if recording a transaction"
    )
    
    amount: Optional[float] = Field(
        default=None,
        description="Numerical amount for transaction (convert words to numbers)"
    )
    
    confidence: float = Field(
        default=1.0,
        description="Confidence in the parsing (0.0 to 1.0)"
    )
    
    clarification_needed: Optional[str] = Field(
        default=None,
        description="What information is missing or unclear, if any"
    )


class VoiceAgent:
    """Agent for processing voice/text commands."""
    
    def __init__(self):
        self.storage = get_storage()
        self.pending_transactions = {}  # Store pending transactions waiting for confirmation
        self.llm = get_reasoning_llm(temperature=0.1)  # Low temperature for consistent parsing
    
    def get_welcome_message(self) -> str:
        """Get the welcome message."""
        entities = self.storage.get_entities()
        if not entities:
            return WELCOME_MESSAGE
        else:
            return f"Welcome back! You're currently tracking: {', '.join(entities)}. What would you like to do?"
    
    def get_help_message(self) -> str:
        """Get the help message."""
        return HELP_MESSAGE
    
    def _parse_message_with_llm(self, message: str) -> ParsedIntent:
        """
        Use LLM to parse user message and extract intent and entities.
        
        Args:
            message: The user's input message
            
        Returns:
            ParsedIntent object with structured information
        """
        import json
        
        collections = self.storage.get_entities()
        collections_str = ", ".join(collections) if collections else "none yet"
        
        # Use centralized prompt from prompts.py
        prompt = LLM_PARSING_PROMPT.format(
            collections=collections_str,
            message=message
        )

        try:
            # Get response from LLM with system prompt
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            # Parse JSON
            parsed_json = json.loads(response_text)
            
            # Create ParsedIntent from JSON
            return ParsedIntent(
                intent_type=parsed_json.get("intent_type", "general"),
                entities=parsed_json.get("entities", []),
                transaction_type=parsed_json.get("transaction_type"),
                amount=parsed_json.get("amount"),
                confidence=parsed_json.get("confidence", 1.0),
                clarification_needed=parsed_json.get("clarification_needed")
            )
        except Exception as e:
            print(f"LLM parsing error: {e}")
            # Fallback to general intent
            return ParsedIntent(
                intent_type="general",
                confidence=0.0,
                clarification_needed="I couldn't understand that. Could you rephrase?"
            )
    
    def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a user message and return a response.
        
        Args:
            message: The user's input message
        
        Returns:
            Dictionary with 'success', 'response', and optional 'transaction_id'
        """
        try:
            message = message.strip()
            
            # Parse message with LLM
            parsed = self._parse_message_with_llm(message)
            
            # Handle low confidence or need for clarification
            if parsed.confidence < 0.5 or parsed.clarification_needed:
                return {
                    "success": True,
                    "response": parsed.clarification_needed or "I'm not sure what you mean. Could you rephrase that?"
                }
            
            # Route to appropriate handler based on intent
            if parsed.intent_type == "add_collection":
                return self._handle_add_to_collection_llm(parsed)
            
            elif parsed.intent_type == "remove_collection":
                return self._handle_remove_from_collection_llm(parsed)
            
            elif parsed.intent_type == "list_collections":
                return self._handle_list_collections()
            
            elif parsed.intent_type == "record_transaction":
                return self._handle_transaction_llm(parsed)
            
            elif parsed.intent_type == "get_statistics":
                return self._handle_statistics_query_llm(parsed)
            
            elif parsed.intent_type == "help":
                return {
                    "success": True,
                    "response": self.get_help_message()
                }
            
            else:  # general
                entities = self.storage.get_entities()
                if not entities:
                    return {
                        "success": True,
                        "response": ERROR_NO_COLLECTIONS
                    }
                else:
                    return {
                        "success": True,
                        "response": f"I'm not sure what you want to do. Currently tracking: {', '.join(entities)}. Try saying something like 'I consumed 2 coffees' or 'How much coffee have I consumed?'"
                    }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": f"Sorry, I encountered an error: {str(e)}"
            }
    
    def _handle_add_to_collection_llm(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Handle adding items to collection (LLM-based)."""
        if not parsed.entities:
            return {
                "success": False,
                "response": "I couldn't identify what items to add. Please tell me what you'd like to track."
            }
        
        added = []
        already_exists = []
        
        for item in parsed.entities:
            # Normalize entity name (lowercase for consistency)
            item_lower = item.lower()
            result = self.storage.add_entity(item_lower)
            if result["success"]:
                added.append(item_lower)
            else:
                already_exists.append(item_lower)
        
        responses = []
        if added:
            responses.append(f"Added {', '.join(added)} to your collection.")
        if already_exists:
            responses.append(f"{', '.join(already_exists)} already in collection.")
        
        all_entities = self.storage.get_entities()
        responses.append(f"Currently tracking: {', '.join(all_entities)}")
        
        return {
            "success": True,
            "response": " ".join(responses)
        }
    
    def _handle_remove_from_collection_llm(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Handle removing items from collection (LLM-based)."""
        if not parsed.entities:
            return {
                "success": False,
                "response": "I couldn't identify what item to remove. Please specify which item."
            }
        
        entity = parsed.entities[0].lower()  # Take first entity
        
        result = self.storage.remove_entity(entity)
        if result["success"]:
            remaining = self.storage.get_entities()
            if remaining:
                return {
                    "success": True,
                    "response": f"Removed {entity} from your collection. Still tracking: {', '.join(remaining)}"
                }
            else:
                return {
                    "success": True,
                    "response": f"Removed {entity} from your collection. Your collection is now empty."
                }
        else:
            return {
                "success": False,
                "response": result["error"]
            }
    
    def _handle_transaction_llm(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Handle recording a transaction (LLM-based)."""
        # Validate parsed data
        if not parsed.entities:
            return {
                "success": False,
                "response": ERROR_ENTITY_NOT_FOUND
            }
        
        if not parsed.transaction_type:
            return {
                "success": False,
                "response": ERROR_TRANSACTION_TYPE
            }
        
        if parsed.amount is None or parsed.amount <= 0:
            return {
                "success": False,
                "response": ERROR_AMOUNT_NOT_FOUND
            }
        
        entity = parsed.entities[0].lower()  # Take first entity
        
        # Check if entity exists in collection
        if not self.storage.entity_exists(entity):
            # Ask user if they want to add it
            self.pending_transactions[entity] = {
                "entity": entity,
                "transaction_type": parsed.transaction_type,
                "amount": parsed.amount,
                "timestamp": datetime.now()
            }
            return {
                "success": True,
                "response": ERROR_ENTITY_NOT_IN_COLLECTION.format(entity=entity) + " (Reply 'yes' to add it, or 'no' to cancel)"
            }
        
        # Get the proper case for the entity
        entity_proper = self.storage.get_entity_case_preserved(entity)
        
        # Create and store transaction
        transaction = Transaction(
            entity=entity_proper,
            transaction_type=parsed.transaction_type,
            amount=parsed.amount,
            description=None,
            timestamp=datetime.now()
        )
        
        saved_transaction = self.storage.add_transaction(transaction)
        
        return {
            "success": True,
            "response": f"Recorded: {entity_proper} {parsed.transaction_type} {parsed.amount}",
            "transaction_id": saved_transaction.id
        }
    
    def _handle_statistics_query_llm(self, parsed: ParsedIntent) -> Dict[str, Any]:
        """Handle statistics queries (LLM-based)."""
        entities = self.storage.get_entities()
        
        if not entities:
            return {
                "success": True,
                "response": ERROR_NO_COLLECTIONS
            }
        
        # Check if asking about specific entity
        specific_entity = None
        if parsed.entities:
            # Find matching entity (case-insensitive)
            for entity in parsed.entities:
                if self.storage.entity_exists(entity.lower()):
                    specific_entity = self.storage.get_entity_case_preserved(entity.lower())
                    break
        
        stats = self.storage.get_statistics(entity=specific_entity)
        
        if specific_entity:
            stat = stats[specific_entity]
            return {
                "success": True,
                "response": f"{specific_entity} Statistics:\n" +
                           f"- Total consumed: {stat.total_consumed}\n" +
                           f"- Total received: {stat.total_received}\n" +
                           f"- Net balance: {stat.net_balance}\n" +
                           f"- Transactions: {stat.transaction_count}"
            }
        else:
            # Show all
            response = "Statistics for all items:\n"
            for entity, stat in stats.items():
                response += f"\n{entity}:\n"
                response += f"  - Consumed: {stat.total_consumed}\n"
                response += f"  - Received: {stat.total_received}\n"
                response += f"  - Balance: {stat.net_balance}\n"
            return {
                "success": True,
                "response": response
            }
    
    # Keep old methods for backward compatibility (but they won't be called)
    def _handle_add_to_collection(self, message: str) -> Dict[str, Any]:
        """Handle adding items to the collection."""
        # Try to extract entity names
        # Patterns: "add X to collection", "track X", "add X and Y"
        
        # Remove common words using word boundaries
        for word in ["add", "to", "collection", "my", "track", "register", "the", "tracking"]:
            message = re.sub(rf'\b{word}\b', ' ', message, flags=re.IGNORECASE)
        
        # Clean up extra spaces first
        message = ' '.join(message.split())
        
        # Split by "and" or commas to get multiple items
        items = re.split(r'\s+and\s+|,\s*', message)
        items = [item.strip() for item in items if item.strip() and len(item.strip()) > 0]
        
        if not items:
            return {
                "success": False,
                "response": "I couldn't identify what items to add. Please say something like 'Add coffee to my collection' or 'Track apples and oranges'."
            }
        
        added = []
        already_exists = []
        
        for item in items:
            result = self.storage.add_entity(item)
            if result["success"]:
                added.append(item)
            else:
                already_exists.append(item)
        
        responses = []
        if added:
            responses.append(f"Added {', '.join(added)} to your collection.")
        if already_exists:
            responses.append(f"{', '.join(already_exists)} already in collection.")
        
        all_entities = self.storage.get_entities()
        responses.append(f"Currently tracking: {', '.join(all_entities)}")
        
        return {
            "success": True,
            "response": " ".join(responses)
        }
    
    def _handle_remove_from_collection(self, message: str) -> Dict[str, Any]:
        """Handle removing items from the collection."""
        # Try to extract entity name more carefully
        entity_text = message
        
        # Remove keywords
        for word in ["remove", "delete", "stop", "tracking", "from", "collection", "my", "the"]:
            entity_text = re.sub(rf'\b{word}\b', '', entity_text, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        entity = ' '.join(entity_text.split()).strip()
        
        if not entity:
            return {
                "success": False,
                "response": "I couldn't identify what item to remove. Please say something like 'Remove coffee from my collection'."
            }
        
        result = self.storage.remove_entity(entity)
        if result["success"]:
            remaining = self.storage.get_entities()
            if remaining:
                return {
                    "success": True,
                    "response": f"Removed {entity} from your collection. Still tracking: {', '.join(remaining)}"
                }
            else:
                return {
                    "success": True,
                    "response": f"Removed {entity} from your collection. Your collection is now empty."
                }
        else:
            return {
                "success": False,
                "response": result["error"]
            }
    
    def _handle_list_collections(self) -> Dict[str, Any]:
        """Handle listing all collections."""
        entities = self.storage.get_entities()
        
        if not entities:
            return {
                "success": True,
                "response": "You don't have any items in your collection yet. Add some by saying 'Add coffee to my collection'."
            }
        else:
            return {
                "success": True,
                "response": f"You're currently tracking {len(entities)} items: {', '.join(entities)}"
            }
    
    def _handle_transaction(self, message: str) -> Dict[str, Any]:
        """Handle recording a transaction (consumed or received)."""
        # Extract transaction type
        transaction_type = None
        if "consumed" in message or "used" in message:
            transaction_type = "consumed"
        elif "received" in message or "got" in message:
            transaction_type = "received"
        
        if not transaction_type:
            return {
                "success": False,
                "response": ERROR_TRANSACTION_TYPE
            }
        
        # Extract amount (look for numbers)
        amount_match = re.search(r'(\d+(?:\.\d+)?)', message)
        if not amount_match:
            return {
                "success": False,
                "response": ERROR_AMOUNT_NOT_FOUND
            }
        
        amount = float(amount_match.group(1))
        
        # Extract entity name more carefully
        # Remove transaction type keywords and amount
        entity_text = message
        
        # Remove transaction keywords (word boundaries to avoid removing parts of words)
        if transaction_type == "consumed":
            entity_text = re.sub(r'\b(consumed|used)\b', ' ', entity_text, flags=re.IGNORECASE)
        else:
            entity_text = re.sub(r'\b(received|got)\b', ' ', entity_text, flags=re.IGNORECASE)
        
        # Remove the amount (try both integer and float forms)
        # First try integer form
        amount_int = int(amount) if amount == int(amount) else None
        if amount_int is not None:
            entity_text = re.sub(rf'\b{amount_int}\b', ' ', entity_text)
        # Also try float form if different
        entity_text = re.sub(rf'\b{amount}\b', ' ', entity_text)
        
        # Remove common words (with word boundaries only - won't affect letters inside words)
        entity_text = re.sub(r'\b(i|the|a|an|my)\b', ' ', entity_text, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        entity = ' '.join(entity_text.split()).strip()
        
        if not entity:
            return {
                "success": False,
                "response": ERROR_ENTITY_NOT_FOUND
            }
        
        # Check if entity exists in collection
        if not self.storage.entity_exists(entity):
            # Ask user if they want to add it
            self.pending_transactions[entity] = {
                "entity": entity,
                "transaction_type": transaction_type,
                "amount": amount,
                "timestamp": datetime.now()
            }
            return {
                "success": True,
                "response": ERROR_ENTITY_NOT_IN_COLLECTION.format(entity=entity) + " (Reply 'yes' to add it, or 'no' to cancel)"
            }
        
        # Get the proper case for the entity
        entity_proper = self.storage.get_entity_case_preserved(entity)
        
        # Create and store transaction
        transaction = Transaction(
            entity=entity_proper,
            transaction_type=transaction_type,
            amount=amount,
            description=None,
            timestamp=datetime.now()
        )
        
        saved_transaction = self.storage.add_transaction(transaction)
        
        return {
            "success": True,
            "response": f"Recorded: {entity_proper} {transaction_type} {amount}",
            "transaction_id": saved_transaction.id
        }
    
    def _handle_statistics_query(self, message: str) -> Dict[str, Any]:
        """Handle statistics queries."""
        # Check if asking about all entities or specific one
        entities = self.storage.get_entities()
        
        if not entities:
            return {
                "success": True,
                "response": ERROR_NO_COLLECTIONS
            }
        
        # Try to find specific entity in message
        specific_entity = None
        for entity in entities:
            if entity.lower() in message:
                specific_entity = entity
                break
        
        stats = self.storage.get_statistics(entity=specific_entity)
        
        if specific_entity:
            stat = stats[specific_entity]
            return {
                "success": True,
                "response": f"{specific_entity} Statistics:\n" +
                           f"- Total consumed: {stat.total_consumed}\n" +
                           f"- Total received: {stat.total_received}\n" +
                           f"- Net balance: {stat.net_balance}\n" +
                           f"- Transactions: {stat.transaction_count}"
            }
        else:
            # Show all
            response = "Statistics for all items:\n"
            for entity, stat in stats.items():
                response += f"\n{entity}:\n"
                response += f"  - Consumed: {stat.total_consumed}\n"
                response += f"  - Received: {stat.total_received}\n"
                response += f"  - Balance: {stat.net_balance}\n"
            return {
                "success": True,
                "response": response
            }


def create_voice_agent() -> VoiceAgent:
    """Factory function to create a voice agent."""
    return VoiceAgent()
