"""End-to-end test of "unknown item -> yes" without any network calls.

The LLM parser is stubbed, but everything else (storage, pending state,
transaction recording) is the real code path. Each turn may be handled by a
different simulated worker process.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")

import app.storage.conversation as conversation_module
import app.storage.database as database_module
import app.storage.storage as storage_module
from app.core.agent import ParsedIntent, VoiceAgent
from app.storage.database import Database


class ConfirmationFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "flow.db")
        self.start_worker()

    def tearDown(self):
        self.tmp.cleanup()

    def start_worker(self):
        """Simulate a fresh uvicorn worker: new singletons, same SQLite file."""
        database_module._database = Database(self.db_path)
        storage_module._storage = None
        conversation_module._store = None

    def agent_with(self, parsed):
        agent = VoiceAgent()
        agent._parse_message_with_llm = lambda *args, **kwargs: parsed
        return agent

    def record_coffee(self, agent):
        return agent.process_message("我喝了2杯咖啡", "device_1", lang="zh")

    def test_unknown_item_then_yes_records_the_transaction(self):
        parsed = ParsedIntent(
            intent_type="record_transaction", entities=["咖啡"],
            transaction_type="consumed", amount=2.0, confidence=1.0,
        )
        agent = self.agent_with(parsed)
        first = self.record_coffee(agent)
        self.assertIn("不在你的集合中", first["response"])
        self.assertEqual(len(agent.conversation.list_pending("device_1")), 1)

        # The confirmation is handled by a different worker process.
        self.start_worker()
        agent2 = self.agent_with(parsed)
        second = agent2.process_message("是", "device_1", lang="zh")

        self.assertIn("咖啡", second["response"])
        self.assertIn("已记录", second["response"])

        stats = agent2.storage.get_statistics("device_1", entity="咖啡")
        self.assertEqual(stats["咖啡"].total_consumed, 2.0)
        self.assertEqual(stats["咖啡"].transaction_count, 1)
        self.assertEqual(agent2.conversation.list_pending("device_1"), [])

    def test_no_cancels_the_pending_transaction(self):
        parsed = ParsedIntent(
            intent_type="record_transaction", entities=["咖啡"],
            transaction_type="consumed", amount=2.0, confidence=1.0,
        )
        agent = self.agent_with(parsed)
        self.record_coffee(agent)

        self.start_worker()
        agent2 = self.agent_with(parsed)
        reply = agent2.process_message("不", "device_1", lang="zh")

        self.assertIn("取消", reply["response"])
        self.assertEqual(agent2.storage.get_entities("device_1"), [])
        self.assertEqual(agent2.conversation.list_pending("device_1"), [])

    def test_short_yes_variants_are_understood(self):
        parsed = ParsedIntent(
            intent_type="record_transaction", entities=["咖啡"],
            transaction_type="consumed", amount=2.0, confidence=1.0,
        )
        for reply in ("添加吧", "好的，添加", "行吧"):
            with self.subTest(reply=reply):
                self.start_worker()
                agent = self.agent_with(parsed)
                agent.process_message("我喝了2杯咖啡", "device_1", lang="zh")
                self.start_worker()
                agent2 = self.agent_with(parsed)
                result = agent2.process_message(reply, "device_1", lang="zh")
                self.assertIn("已记录", result["response"])
                stats = agent2.storage.get_statistics("device_1", entity="咖啡")
                self.assertEqual(stats["咖啡"].total_consumed, 2.0)
                agent2.storage.clear_all_including_collections("device_1")

    def test_english_yes_works_too(self):
        parsed = ParsedIntent(
            intent_type="record_transaction", entities=["coffee"],
            transaction_type="consumed", amount=2.0, confidence=1.0,
        )
        agent = self.agent_with(parsed)
        agent.process_message("I drank 2 coffees", "device_1", lang="en")

        self.start_worker()
        agent2 = self.agent_with(parsed)
        reply = agent2.process_message("yes", "device_1", lang="en")

        self.assertIn("Recorded", reply["response"])
        stats = agent2.storage.get_statistics("device_1", entity="coffee")
        self.assertEqual(stats["coffee"].total_consumed, 2.0)
