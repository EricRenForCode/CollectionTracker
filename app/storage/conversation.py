"""Conversation state shared by every API worker process.

The API server runs uvicorn with several worker processes. Chat history and the
"item X is not tracked - add it?" confirmation used to be kept in module-level
dictionaries, so each worker had its own copy: a follow-up turn such as "yes"
only kept its context when the request happened to hit the same worker again.
This store keeps that state in the shared SQLite database instead, so it is
visible to every worker and survives restarts.
"""

from typing import Any, Dict, List, Optional

from app.storage.database import Database, get_database


class ConversationStore:
    """Wraps the SQLite-backed conversation and pending-action tables."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()

    def get_history(self, device_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Recent conversation for a device, oldest message first."""
        return self.db.get_conversation_history(device_id, limit=limit)

    def append_exchange(self, device_id: str, user_message: str,
                        assistant_message: str, keep: int = 10) -> None:
        """Persist one user/assistant turn pair."""
        self.db.append_conversation_message(device_id, "user", user_message, keep=keep)
        self.db.append_conversation_message(device_id, "assistant", assistant_message, keep=keep)

    def set_pending(self, device_id: str, entity: str, transaction_type: str,
                    amount: float) -> None:
        self.db.set_pending_action(device_id, entity, transaction_type, amount)

    def list_pending(self, device_id: str) -> List[Dict[str, Any]]:
        return self.db.get_pending_actions(device_id)

    def pop_pending(self, device_id: str, entity: str) -> Optional[Dict[str, Any]]:
        return self.db.pop_pending_action(device_id, entity)

    def clear_pending(self, device_id: str) -> None:
        self.db.clear_pending_actions(device_id)

    def clear(self, device_id: str) -> None:
        self.db.clear_conversation(device_id)


_store: Optional[ConversationStore] = None


def get_conversation_store() -> ConversationStore:
    """Get the global conversation store instance."""
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
