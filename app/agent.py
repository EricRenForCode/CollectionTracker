"""Voice assistant agent for processing user messages."""

import json
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from app.storage import get_storage
from app.models import Transaction
from app.llm_config import get_reasoning_llm
from app.prompts import get_prompt


# Pydantic models for structured LLM output
class ParsedIntent(BaseModel):
    """Structured representation of user intent."""
    intent_type: Literal[
        "add_collection", 
        "remove_collection", 
        "list_collections",
        "record_transaction",
        "get_statistics",
        "clear_data",
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
    
    def get_welcome_message(self, device_id: str, lang: str = "en") -> str:
        """Get the welcome message."""
        entities = self.storage.get_entities(device_id)
        if not entities:
            return get_prompt("welcome", lang)
        else:
            if lang == "zh":
                return f"欢迎回来！你目前正在追踪：{', '.join(entities)}。你想做什么？"
            return f"Welcome back! You're currently tracking: {', '.join(entities)}. What would you like to do?"
    
    def get_help_message(self, lang: str = "en") -> str:
        """Get the help message."""
        return get_prompt("help", lang)
    
    def _parse_message_with_llm(self, message: str, device_id: str, history: Optional[List[Dict[str, str]]] = None, lang: str = "en") -> ParsedIntent:
        """
        Use LLM to parse user message and extract intent and entities.
        
        Args:
            message: The user's input message
            device_id: User's device ID
            history: Optional conversation history
            lang: Language for parsing
            
        Returns:
            ParsedIntent object with structured information
        """
        import json
        
        collections = self.storage.get_entities(device_id)
        collections_str = ", ".join(collections) if collections else ("none yet" if lang == "en" else "暂无")
        
        # Format history for prompt
        history_str = ""
        if history:
            history_str = "\nConversation history:\n" if lang == "en" else "\n对话历史：\n"
            for msg in history[-5:]:  # Last 5 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                role_name = role.capitalize() if lang == "en" else ("用户" if role == "user" else "助手")
                history_str += f"{role_name}: {content}\n"

        # Use centralized prompt from prompts.py
        prompt = get_prompt("parsing", lang).format(
            collections=collections_str,
            message=message
        )
        
        if history_str:
            prompt = history_str + "\n" + prompt

        try:
            # Get response from LLM with system prompt
            messages = [
                SystemMessage(content=get_prompt("system", lang)),
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
                clarification_needed=get_prompt("error_general", lang)
            )
    
    def process_message(self, message: str, device_id: str, history: Optional[List[Dict[str, str]]] = None, lang: str = "en") -> Dict[str, Any]:
        """
        Process a user message and return a response.
        
        Args:
            message: The user's input message
            device_id: User's device ID
            history: Optional conversation history
            lang: Language preference
        
        Returns:
            Dictionary with 'success', 'response', and optional 'transaction_id'
        """
        try:
            message = message.strip()
            
            # Parse message with LLM
            parsed = self._parse_message_with_llm(message, device_id, history, lang)
            
            # Handle low confidence or need for clarification
            if parsed.confidence < 0.5 or parsed.clarification_needed:
                default_msg = "I'm not sure what you mean. Could you rephrase that?" if lang == "en" else "我不确定你的意思。你能换个说法吗？"
                return {
                    "success": True,
                    "response": parsed.clarification_needed or default_msg
                }
            
            # Route to appropriate handler based on intent
            if parsed.intent_type == "add_collection":
                return self._handle_add_to_collection_llm(parsed, device_id, lang)
            
            elif parsed.intent_type == "remove_collection":
                return self._handle_remove_from_collection_llm(parsed, device_id, lang)
            
            elif parsed.intent_type == "list_collections":
                return self._handle_list_collections(device_id, lang)
            
            elif parsed.intent_type == "record_transaction":
                return self._handle_transaction_llm(parsed, device_id, lang)
            
            elif parsed.intent_type == "get_statistics":
                return self._handle_statistics_query_llm(parsed, device_id, lang)
            
            elif parsed.intent_type == "clear_data":
                return self._handle_clear_data_llm(parsed, device_id, lang)
            
            elif parsed.intent_type == "help":
                return {
                    "success": True,
                    "response": self.get_help_message(lang)
                }
            
            else:  # general
                entities = self.storage.get_entities(device_id)
                if not entities:
                    return {
                        "success": True,
                        "response": get_prompt("error_no_collections", lang)
                    }
                else:
                    if lang == "zh":
                        response = f"我不确定你想做什么。目前正在追踪：{', '.join(entities)}。试试说“我喝了2杯咖啡”或“咖啡喝了多少？”"
                    else:
                        response = f"I'm not sure what you want to do. Currently tracking: {', '.join(entities)}. Try saying something like 'I consumed 2 coffees' or 'How much coffee have I consumed?'"
                    return {
                        "success": True,
                        "response": response
                    }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": f"Sorry, I encountered an error: {str(e)}"
            }
    
    def _handle_add_to_collection_llm(self, parsed: ParsedIntent, device_id: str, lang: str = "en") -> Dict[str, Any]:
        """Handle adding items to collection (LLM-based)."""
        if not parsed.entities:
            response = "I couldn't identify what items to add. Please tell me what you'd like to track." if lang == "en" else "我没能识别出要添加的物品。请告诉我你想追踪什么。"
            return {
                "success": False,
                "response": response
            }
        
        added = []
        already_exists = []
        
        for item in parsed.entities:
            # Normalize entity name (lowercase for consistency)
            item_lower = item.lower()
            result = self.storage.add_entity(device_id, item_lower)
            if result["success"]:
                added.append(item_lower)
            else:
                already_exists.append(item_lower)
        
        responses = []
        if added:
            if lang == "zh":
                responses.append(f"已将 {', '.join(added)} 添加到你的集合。")
            else:
                responses.append(f"Added {', '.join(added)} to your collection.")
        if already_exists:
            if lang == "zh":
                responses.append(f"{', '.join(already_exists)} 已经在集合中。")
            else:
                responses.append(f"{', '.join(already_exists)} already in collection.")
        
        all_entities = self.storage.get_entities(device_id)
        if lang == "zh":
            responses.append(f"目前正在追踪：{', '.join(all_entities)}")
        else:
            responses.append(f"Currently tracking: {', '.join(all_entities)}")
        
        # Check if any of the added items have pending transactions
        fulfilled_transactions = []
        for item in added:
            if item in self.pending_transactions:
                pending = self.pending_transactions.pop(item)
                # Create and store transaction
                entity_proper = self.storage.get_entity_case_preserved(device_id, item)
                transaction = Transaction(
                    entity=entity_proper,
                    transaction_type=pending["transaction_type"],
                    amount=pending["amount"],
                    description=None,
                    timestamp=datetime.now()
                )
                self.storage.add_transaction(device_id, transaction)
                fulfilled_transactions.append(f"{entity_proper} {pending['transaction_type']} {pending['amount']}")
        
        if fulfilled_transactions:
            if lang == "zh":
                responses.append(f"还记录了：{', '.join(fulfilled_transactions)}。")
            else:
                responses.append(f"Also recorded: {', '.join(fulfilled_transactions)}.")
        
        return {
            "success": True,
            "response": " ".join(responses)
        }
    
    def _handle_remove_from_collection_llm(self, parsed: ParsedIntent, device_id: str, lang: str = "en") -> Dict[str, Any]:
        """Handle removing items from collection (LLM-based)."""
        if not parsed.entities:
            response = "I couldn't identify what item to remove. Please specify which item." if lang == "en" else "我没能识别出要移除的物品。请指定物品名称。"
            return {
                "success": False,
                "response": response
            }
        
        entity = parsed.entities[0].lower()  # Take first entity
        
        result = self.storage.remove_entity(device_id, entity)
        if result["success"]:
            remaining = self.storage.get_entities(device_id)
            if remaining:
                if lang == "zh":
                    response = f"已从集合中移除 {entity}。仍在追踪：{', '.join(remaining)}"
                else:
                    response = f"Removed {entity} from your collection. Still tracking: {', '.join(remaining)}"
                return {
                    "success": True,
                    "response": response
                }
            else:
                if lang == "zh":
                    response = f"已从集合中移除 {entity}。你的集合现在是空的。"
                else:
                    response = f"Removed {entity} from your collection. Your collection is now empty."
                return {
                    "success": True,
                    "response": response
                }
        else:
            return {
                "success": False,
                "response": result["error"]
            }
    
    def _handle_list_collections(self, device_id: str, lang: str = "en") -> Dict[str, Any]:
        """Handle listing all collections."""
        entities = self.storage.get_entities(device_id)
        
        if not entities:
            return {
                "success": True,
                "response": get_prompt("error_no_collections", lang)
            }
        else:
            if lang == "zh":
                response = f"你目前正在追踪 {len(entities)} 个物品：{', '.join(entities)}"
            else:
                response = f"You're currently tracking {len(entities)} items: {', '.join(entities)}"
            return {
                "success": True,
                "response": response
            }
    
    def _handle_transaction_llm(self, parsed: ParsedIntent, device_id: str, lang: str = "en") -> Dict[str, Any]:
        """Handle recording a transaction (LLM-based)."""
        # Validate parsed data
        if not parsed.entities:
            return {
                "success": False,
                "response": get_prompt("error_entity_not_found", lang)
            }
        
        if not parsed.transaction_type:
            return {
                "success": False,
                "response": get_prompt("error_transaction_type", lang)
            }
        
        if parsed.amount is None or parsed.amount <= 0:
            return {
                "success": False,
                "response": get_prompt("error_amount_not_found", lang)
            }
        
        entity = parsed.entities[0].lower()  # Take first entity
        
        # Check if entity exists in collection
        if not self.storage.entity_exists(device_id, entity):
            # Ask user if they want to add it
            self.pending_transactions[entity] = {
                "entity": entity,
                "transaction_type": parsed.transaction_type,
                "amount": parsed.amount,
                "timestamp": datetime.now()
            }
            suffix = " (Reply 'yes' to add it, or 'no' to cancel)" if lang == "en" else "（回复“是”添加，或回复“不”取消）"
            return {
                "success": True,
                "response": get_prompt("error_entity_not_in_collection", lang).format(entity=entity) + suffix
            }
        
        # Get the proper case for the entity
        entity_proper = self.storage.get_entity_case_preserved(device_id, entity)
        
        # Create and store transaction
        transaction = Transaction(
            entity=entity_proper,
            transaction_type=parsed.transaction_type,
            amount=parsed.amount,
            description=None,
            timestamp=datetime.now()
        )
        
        saved_transaction = self.storage.add_transaction(device_id, transaction)
        
        # Get current statistics for the entity
        stats = self.storage.get_statistics(device_id, entity=entity_proper)
        stat = stats[entity_proper]
        
        if lang == "zh":
            type_zh = "消耗" if parsed.transaction_type == "consumed" else "入库"
            response = (
                f"已记录：{entity_proper} {type_zh} {parsed.amount}。\n"
                f"当前 {entity_proper} 统计：\n"
                f"- 总消耗：{stat.total_consumed}\n"
                f"- 总入库：{stat.total_received}\n"
                f"- 净余额：{stat.net_balance}"
            )
        else:
            response = (
                f"Recorded: {entity_proper} {parsed.transaction_type} {parsed.amount}.\n"
                f"Current {entity_proper} Statistics:\n"
                f"- Total consumed: {stat.total_consumed}\n"
                f"- Total received: {stat.total_received}\n"
                f"- Net balance: {stat.net_balance}"
            )
        
        return {
            "success": True,
            "response": response,
            "transaction_id": saved_transaction.id
        }
    
    def _handle_statistics_query_llm(self, parsed: ParsedIntent, device_id: str, lang: str = "en") -> Dict[str, Any]:
        """Handle statistics queries (LLM-based)."""
        entities = self.storage.get_entities(device_id)
        
        if not entities:
            return {
                "success": True,
                "response": get_prompt("error_no_collections", lang)
            }
        
        # Check if asking about specific entity
        specific_entity = None
        if parsed.entities:
            # Find matching entity (case-insensitive)
            for entity in parsed.entities:
                if self.storage.entity_exists(device_id, entity.lower()):
                    specific_entity = self.storage.get_entity_case_preserved(device_id, entity.lower())
                    break
        
        stats = self.storage.get_statistics(device_id, entity=specific_entity)
        
        if specific_entity:
            stat = stats[specific_entity]
            if lang == "zh":
                response = (
                    f"{specific_entity} 统计：\n"
                    f"- 总消耗：{stat.total_consumed}\n"
                    f"- 总入库：{stat.total_received}\n"
                    f"- 净余额：{stat.net_balance}"
                )
            else:
                response = (
                    f"{specific_entity} Statistics:\n"
                    f"- Total consumed: {stat.total_consumed}\n"
                    f"- Total received: {stat.total_received}\n"
                    f"- Net balance: {stat.net_balance}"
                )
            return {
                "success": True,
                "response": response
            }
        else:
            # Show all
            if lang == "zh":
                response = "所有物品统计：\n"
                for entity, stat in stats.items():
                    response += f"\n{entity}：\n"
                    response += f"  - 消耗：{stat.total_consumed}\n"
                    response += f"  - 入库：{stat.total_received}\n"
                    response += f"  - 余额：{stat.net_balance}\n"
            else:
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
    
    def _handle_clear_data_llm(self, parsed: ParsedIntent, device_id: str, lang: str = "en") -> Dict[str, Any]:
        """Handle clearing data (LLM-based)."""
        if not parsed.entities:
            if lang == "zh":
                response = "你想清除什么？你可以清除“交易记录”、“集合”或“两者”。"
            else:
                response = "What would you like to clear? You can clear 'transactions', 'collections', or 'both'."
            return {
                "success": False,
                "response": response
            }
        
        target = parsed.entities[0].lower()
        
        if target in ["transactions", "交易记录", "交易"]:
            self.storage.clear_all_data(device_id)
            if lang == "zh":
                response = "所有交易数据已清除。你的集合已保留。"
            else:
                response = "All transaction data has been cleared. Your collections have been preserved."
            return {
                "success": True,
                "response": response
            }
        elif target in ["collections", "集合"]:
            self.storage.clear_all_including_collections(device_id)
            if lang == "zh":
                response = "所有集合和交易数据已清除。"
            else:
                response = "All collections and transaction data have been cleared."
            return {
                "success": True,
                "response": response
            }
        elif target in ["both", "两者", "全部"]:
            self.storage.clear_all_including_collections(device_id)
            if lang == "zh":
                response = "所有数据（包括集合和交易）已成功清除。"
            else:
                response = "All data, including collections and transactions, has been cleared successfully."
            return {
                "success": True,
                "response": response
            }
        else:
            if lang == "zh":
                response = f"我不确定如何清除“{target}”。请尝试说“交易记录”、“集合”或“全部”。"
            else:
                response = f"I'm not sure how to clear '{target}'. Try 'transactions', 'collections', or 'both'."
            return {
                "success": False,
                "response": response
            }
    
    # Keep old methods for backward compatibility (but they won't be called)
    def _handle_add_to_collection(self, message: str) -> Dict[str, Any]:
        """Handle adding items to the collection."""
        return {"success": False, "response": "This method is deprecated."}
    
    def _handle_remove_from_collection(self, message: str) -> Dict[str, Any]:
        """Handle removing items from the collection."""
        return {"success": False, "response": "This method is deprecated."}
    
    def _handle_list_collections_old(self) -> Dict[str, Any]:
        """Handle listing all collections."""
        return {"success": False, "response": "This method is deprecated."}
    
    def _handle_transaction(self, message: str) -> Dict[str, Any]:
        """Handle recording a transaction (consumed or received)."""
        return {"success": False, "response": "This method is deprecated."}
    
    def _handle_statistics_query(self, message: str) -> Dict[str, Any]:
        """Handle statistics queries."""
        return {"success": False, "response": "This method is deprecated."}


def create_voice_agent() -> VoiceAgent:
    """Factory function to create a voice agent."""
    return VoiceAgent()
