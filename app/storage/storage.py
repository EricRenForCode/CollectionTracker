"""Storage layer for managing transactions and statistics with multi-user support."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from app.api.models import Transaction, EntityStatistics
from app.storage.database import get_database


class TransactionStorage:
    """SQLite-based storage for transactions with multi-user support."""
    
    def __init__(self):
        self.db = get_database()
        # Keep legacy file for migration purposes
        self.legacy_data_file = Path("data/transactions.json")
        self._migrate_legacy_data_if_needed()
    
    def _migrate_legacy_data_if_needed(self):
        """Migrate data from legacy JSON file to SQLite (one-time migration)."""
        if not self.legacy_data_file.exists():
            return
        
        # Check if we've already migrated
        migration_flag = self.legacy_data_file.parent / ".migrated"
        if migration_flag.exists():
            return
        
        print("Migrating legacy data from JSON to SQLite...")
        
        try:
            with open(self.legacy_data_file, 'r') as f:
                legacy_data = json.load(f)
            
            # Use a default device_id for legacy data
            legacy_device_id = "device_legacy_0000000000000000"
            
            # Create legacy user if not exists
            if not self.db.get_user_by_device_id(legacy_device_id):
                self.db.create_user(
                    device_id=legacy_device_id,
                    fingerprint="legacy",
                    user_data={"migrated": True, "note": "Migrated from JSON storage"}
                )
            
            # Migrate collections
            for entity in legacy_data.get("collections", []):
                self._add_entity_to_db(legacy_device_id, entity)
            
            # Migrate transactions
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                for trans in legacy_data.get("transactions", []):
                    cursor.execute("""
                        INSERT OR IGNORE INTO transactions 
                        (id, device_id, entity, transaction_type, amount, description, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trans.get("id", str(uuid.uuid4())),
                        legacy_device_id,
                        trans["entity"],
                        trans["transaction_type"],
                        trans["amount"],
                        trans.get("description"),
                        int(datetime.fromisoformat(trans["timestamp"]).timestamp())
                    ))
            
            # Mark as migrated
            migration_flag.write_text("migrated")
            print(f"Successfully migrated {len(legacy_data.get('collections', []))} collections and {len(legacy_data.get('transactions', []))} transactions")
            
        except Exception as e:
            print(f"Error during migration: {e}")
    
    def _add_entity_to_db(self, device_id: str, entity_name: str) -> bool:
        """Internal method to add entity to database."""
        now = int(datetime.now().timestamp())
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO collections (device_id, entity_name, created_at)
                    VALUES (?, ?, ?)
                """, (device_id, entity_name, now))
                return True
            except Exception:
                return False
    
    def add_entity(self, device_id: str, entity_name: str) -> dict:
        """Add an entity to the collection for a specific user."""
        entity_name = entity_name.strip()
        if not entity_name:
            return {"success": False, "error": "Entity name cannot be empty"}
        
        # Check if entity already exists (case-insensitive)
        existing_entities = self.get_entities(device_id)
        if entity_name.lower() in [e.lower() for e in existing_entities]:
            return {"success": False, "error": f"Entity '{entity_name}' already exists"}
        
        # Add to database
        if self._add_entity_to_db(device_id, entity_name):
            return {"success": True, "entity": entity_name}
        else:
            return {"success": False, "error": "Failed to add entity"}
    
    def remove_entity(self, device_id: str, entity_name: str) -> dict:
        """Remove an entity from the collection for a specific user."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM collections 
                WHERE device_id = ? AND entity_name = ? COLLATE NOCASE
            """, (device_id, entity_name))
            
            if cursor.rowcount > 0:
                return {"success": True, "entity": entity_name}
            else:
                return {"success": False, "error": f"Entity '{entity_name}' not found"}
    
    def get_entities(self, device_id: str) -> List[str]:
        """Get list of all entities in the collection for a specific user."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT entity_name FROM collections 
                WHERE device_id = ?
                ORDER BY created_at DESC
            """, (device_id,))
            return [row["entity_name"] for row in cursor.fetchall()]
    
    def entity_exists(self, device_id: str, entity_name: str) -> bool:
        """Check if an entity exists in the collection (case-insensitive)."""
        entities = self.get_entities(device_id)
        return entity_name.lower() in [e.lower() for e in entities]
    
    def get_entity_case_preserved(self, device_id: str, entity_name: str) -> Optional[str]:
        """Get the entity name with its original case from the collection."""
        entities = self.get_entities(device_id)
        for entity in entities:
            if entity.lower() == entity_name.lower():
                return entity
        return None
    
    def add_transaction(self, device_id: str, transaction: Transaction) -> Transaction:
        """Add a new transaction for a specific user."""
        if not transaction.id:
            transaction.id = str(uuid.uuid4())
        
        timestamp_unix = int(transaction.timestamp.timestamp())
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions 
                (id, device_id, entity, transaction_type, amount, description, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction.id,
                device_id,
                transaction.entity,
                transaction.transaction_type,
                transaction.amount,
                transaction.description,
                timestamp_unix
            ))
        
        return transaction
    
    def get_transactions(
        self,
        device_id: str,
        entity: Optional[str] = None,
        transaction_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        """Get transactions with optional filtering for a specific user."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM transactions WHERE device_id = ?"
            params = [device_id]
            
            if entity:
                query += " AND entity = ?"
                params.append(entity)
            
            if transaction_type:
                query += " AND transaction_type = ?"
                params.append(transaction_type)
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(int(start_date.timestamp()))
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(int(end_date.timestamp()))
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            
            transactions = []
            for row in cursor.fetchall():
                transactions.append(Transaction(
                    id=row["id"],
                    entity=row["entity"],
                    transaction_type=row["transaction_type"],
                    amount=row["amount"],
                    description=row["description"],
                    timestamp=datetime.fromtimestamp(row["timestamp"])
                ))
            
            return transactions
    
    def get_statistics(
        self,
        device_id: str,
        entity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, EntityStatistics]:
        """Get statistics for entities for a specific user."""
        transactions = self.get_transactions(
            device_id=device_id,
            entity=entity,
            start_date=start_date,
            end_date=end_date
        )
        
        # Initialize statistics for user-defined entities only
        entities = [entity] if entity else self.get_entities(device_id)
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
            if transaction.entity not in stats:
                continue
                
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
    
    def clear_all_data(self, device_id: str):
        """Clear all transaction data for a specific user (useful for testing)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE device_id = ?", (device_id,))
    
    def clear_all_including_collections(self, device_id: str):
        """Clear all data including collections for a specific user."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE device_id = ?", (device_id,))
            cursor.execute("DELETE FROM collections WHERE device_id = ?", (device_id,))
    
    def get_recent_transactions(self, device_id: str, limit: int = 10) -> List[Transaction]:
        """Get the most recent transactions for a specific user."""
        transactions = self.get_transactions(device_id)
        return transactions[:limit]  # Already sorted by timestamp DESC


# Global storage instance
_storage = None


def get_storage() -> TransactionStorage:
    """Get the global storage instance."""
    global _storage
    if _storage is None:
        _storage = TransactionStorage()
    return _storage


def get_legacy_storage() -> TransactionStorage:
    """
    Get storage instance for legacy (non-user-specific) operations.
    Uses a special legacy device_id.
    This is for backward compatibility only.
    """
    return get_storage()
