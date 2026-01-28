"""Storage layer for managing transactions and statistics."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from app.models import Transaction, EntityStatistics


class TransactionStorage:
    """Simple JSON-based storage for transactions."""
    
    def __init__(self, data_file: str = "data/transactions.json"):
        self.data_file = Path(data_file)
        self.data_file.parent.mkdir(exist_ok=True)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Ensure the data file exists."""
        if not self.data_file.exists():
            self.data_file.write_text(json.dumps({"transactions": [], "collections": []}))
    
    def _read_data(self) -> dict:
        """Read data from file."""
        with open(self.data_file, 'r') as f:
            return json.load(f)
    
    def _write_data(self, data: dict):
        """Write data to file."""
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def add_entity(self, entity_name: str) -> dict:
        """Add an entity to the collection."""
        entity_name = entity_name.strip()
        if not entity_name:
            return {"success": False, "error": "Entity name cannot be empty"}
        
        data = self._read_data()
        if "collections" not in data:
            data["collections"] = []
        
        # Check if entity already exists (case-insensitive)
        existing_entities = [e.lower() for e in data["collections"]]
        if entity_name.lower() in existing_entities:
            return {"success": False, "error": f"Entity '{entity_name}' already exists"}
        
        data["collections"].append(entity_name)
        self._write_data(data)
        return {"success": True, "entity": entity_name}
    
    def remove_entity(self, entity_name: str) -> dict:
        """Remove an entity from the collection."""
        data = self._read_data()
        if "collections" not in data:
            data["collections"] = []
        
        # Find and remove (case-insensitive match)
        found = False
        for i, entity in enumerate(data["collections"]):
            if entity.lower() == entity_name.lower():
                data["collections"].pop(i)
                found = True
                break
        
        if not found:
            return {"success": False, "error": f"Entity '{entity_name}' not found"}
        
        self._write_data(data)
        return {"success": True, "entity": entity_name}
    
    def get_entities(self) -> List[str]:
        """Get list of all entities in the collection."""
        data = self._read_data()
        return data.get("collections", [])
    
    def entity_exists(self, entity_name: str) -> bool:
        """Check if an entity exists in the collection (case-insensitive)."""
        entities = self.get_entities()
        return entity_name.lower() in [e.lower() for e in entities]
    
    def get_entity_case_preserved(self, entity_name: str) -> Optional[str]:
        """Get the entity name with its original case from the collection."""
        entities = self.get_entities()
        for entity in entities:
            if entity.lower() == entity_name.lower():
                return entity
        return None
    
    def add_transaction(self, transaction: Transaction) -> Transaction:
        """Add a new transaction."""
        if not transaction.id:
            transaction.id = str(uuid.uuid4())
        
        data = self._read_data()
        transaction_dict = transaction.dict()
        transaction_dict['timestamp'] = transaction.timestamp.isoformat()
        data['transactions'].append(transaction_dict)
        self._write_data(data)
        
        return transaction
    
    def get_transactions(
        self,
        entity: Optional[str] = None,
        transaction_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """Get transactions with optional filtering."""
        data = self._read_data()
        transactions = []
        
        for t_dict in data['transactions']:
            # Parse datetime
            t_dict['timestamp'] = datetime.fromisoformat(t_dict['timestamp'])
            transaction = Transaction(**t_dict)
            
            # Apply filters
            if entity and transaction.entity != entity:
                continue
            if transaction_type and transaction.transaction_type != transaction_type:
                continue
            if start_date and transaction.timestamp < start_date:
                continue
            if end_date and transaction.timestamp > end_date:
                continue
            
            transactions.append(transaction)
        
        return transactions
    
    def get_statistics(
        self,
        entity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, EntityStatistics]:
        """Get statistics for entities."""
        transactions = self.get_transactions(
            entity=entity,
            start_date=start_date,
            end_date=end_date
        )
        
        # Initialize statistics for user-defined entities only
        entities = [entity] if entity else self.get_entities()
        stats = {
            e: EntityStatistics(
                entity=e,
                total_consumed=0.0,
                total_received=0.0,
                net_balance=0.0,
                transaction_count=0,
                last_transaction=None
            )
            for e in entities
        }
        
        # Calculate statistics
        for transaction in transactions:
            entity_stats = stats[transaction.entity]
            entity_stats.transaction_count += 1
            
            if transaction.transaction_type == "consumed":
                entity_stats.total_consumed += transaction.amount
            else:  # received
                entity_stats.total_received += transaction.amount
            
            # Update last transaction
            if (entity_stats.last_transaction is None or 
                transaction.timestamp > entity_stats.last_transaction):
                entity_stats.last_transaction = transaction.timestamp
            
            # Calculate net balance (received - consumed)
            entity_stats.net_balance = (
                entity_stats.total_received - entity_stats.total_consumed
            )
        
        return stats
    
    def clear_all_data(self):
        """Clear all transaction data (useful for testing)."""
        data = self._read_data()
        # Keep collections but clear transactions
        data["transactions"] = []
        self._write_data(data)
    
    def clear_all_including_collections(self):
        """Clear all data including collections."""
        self._write_data({"transactions": [], "collections": []})
    
    def get_recent_transactions(self, limit: int = 10) -> List[Transaction]:
        """Get the most recent transactions."""
        transactions = self.get_transactions()
        transactions.sort(key=lambda t: t.timestamp, reverse=True)
        return transactions[:limit]


# Global storage instance
_storage = None


def get_storage() -> TransactionStorage:
    """Get the global storage instance."""
    global _storage
    if _storage is None:
        _storage = TransactionStorage()
    return _storage
