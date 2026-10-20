"""Tests for the SQLite-backed conversation state.

The production server runs uvicorn with several worker processes, so these
tests explicitly simulate "another worker" by opening a second Database
instance against the same file.

Run with:
    python -m unittest tests.test_conversation_store tests.test_confirmation_flow -v
"""

import tempfile
import time
import unittest
from pathlib import Path

from app.storage.conversation import ConversationStore
from app.storage.database import Database


class ConversationStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "store.db")

    def tearDown(self):
        self.tmp.cleanup()

    def store(self):
        """A store backed by a fresh connection, i.e. a different worker."""
        return ConversationStore(Database(self.db_path))

    def test_history_is_shared_between_workers(self):
        worker_a = self.store()
        worker_a.append_exchange("device_1", "我喝了2杯咖啡", "物品 '咖啡' 不在你的集合中")

        worker_b = self.store()
        history = worker_b.get_history("device_1")

        self.assertEqual([m["role"] for m in history], ["user", "assistant"])
        self.assertEqual(history[0]["content"], "我喝了2杯咖啡")
        self.assertEqual(history[1]["content"], "物品 '咖啡' 不在你的集合中")

    def test_history_keeps_only_the_newest_messages(self):
        store = self.store()
        for i in range(8):
            store.append_exchange("device_1", "u%d" % i, "a%d" % i)

        history = store.get_history("device_1")

        self.assertEqual(len(history), 10)
        self.assertEqual(history[0]["content"], "u3")
        self.assertEqual(history[-1]["content"], "a7")

    def test_history_expires(self):
        db = Database(self.db_path)
        store = ConversationStore(db)
        store.append_exchange("device_1", "u", "a")

        with db.get_connection() as conn:
            conn.execute("UPDATE conversation_messages SET created_at = created_at - 7200")

        self.assertEqual(store.get_history("device_1"), [])

    def test_pending_action_is_shared_and_consumed_once(self):
        worker_a = self.store()
        worker_a.set_pending("device_1", "coffee", "consumed", 2.0)

        worker_b = self.store()
        self.assertEqual(len(worker_b.list_pending("device_1")), 1)

        popped = worker_b.pop_pending("device_1", "coffee")
        self.assertIsNotNone(popped)
        self.assertEqual(popped["amount"], 2.0)
        self.assertEqual(popped["transaction_type"], "consumed")

        self.assertIsNone(worker_a.pop_pending("device_1", "coffee"))
        self.assertEqual(worker_a.list_pending("device_1"), [])

    def test_pending_actions_are_scoped_per_device(self):
        store = self.store()
        store.set_pending("device_1", "coffee", "consumed", 2.0)

        self.assertEqual(store.list_pending("device_2"), [])
        self.assertIsNone(store.pop_pending("device_2", "coffee"))
        self.assertEqual(len(store.list_pending("device_1")), 1)

    def test_pending_action_expires(self):
        db = Database(self.db_path)
        store = ConversationStore(db)
        store.set_pending("device_1", "coffee", "consumed", 2.0)

        with db.get_connection() as conn:
            conn.execute("UPDATE pending_actions SET created_at = created_at - 7200")

        self.assertEqual(store.list_pending("device_1"), [])
        self.assertIsNone(store.pop_pending("device_1", "coffee"))

    def test_clear_pending_only_touches_one_device(self):
        store = self.store()
        store.set_pending("device_1", "coffee", "consumed", 2.0)
        store.set_pending("device_2", "tea", "received", 5.0)

        store.clear_pending("device_1")

        self.assertEqual(store.list_pending("device_1"), [])
        self.assertEqual(len(store.list_pending("device_2")), 1)
