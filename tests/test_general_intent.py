"""Tests for the general-intent reply path (no network calls)."""

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


class FakeLLM:
    def __init__(self, content="你刚才说你喝了4杯普洱茶。", raises=False):
        self.content = content
        self.raises = raises
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        if self.raises:
            raise RuntimeError("llm unavailable")

        class Response:
            pass

        response = Response()
        response.content = self.content
        return response


class GeneralIntentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp.name) / "general.db")
        database_module._database = Database(self.db_path)
        storage_module._storage = None
        conversation_module._store = None

    def tearDown(self):
        self.tmp.cleanup()

    def make_agent(self):
        agent = VoiceAgent()
        agent._parse_message_with_llm = lambda *args, **kwargs: ParsedIntent(
            intent_type="general", confidence=0.6
        )
        agent.llm = FakeLLM()
        return agent

    def history(self):
        return [
            {"role": "user", "content": "我喝了4杯普洱茶"},
            {"role": "assistant", "content": "物品 '普洱茶' 不在你的集合中。你想要先添加它吗？"},
        ]

    def test_follow_up_question_uses_history(self):
        agent = self.make_agent()
        result = agent.process_message("我刚刚说了什么？", "device_1", self.history(), lang="zh")

        self.assertEqual(result["response"], "你刚才说你喝了4杯普洱茶。")
        sent = agent.llm.calls[0]
        # system prompt + the two history turns + the current question
        self.assertEqual(len(sent), 4)
        self.assertEqual(sent[1].content, "我喝了4杯普洱茶")
        self.assertIn("我刚刚说了什么？", sent[-1].content)

    def test_greeting_without_history_does_not_call_the_llm(self):
        agent = self.make_agent()
        result = agent.process_message("你好", "device_1", [], lang="zh")

        self.assertEqual(agent.llm.calls, [])
        self.assertIn("还没有任何物品", result["response"])

    def test_falls_back_when_the_llm_fails(self):
        agent = self.make_agent()
        agent.llm = FakeLLM(raises=True)
        result = agent.process_message("我刚刚说了什么？", "device_1", self.history(), lang="zh")

        self.assertTrue(result["success"])
        self.assertIn("还没有任何物品", result["response"])

    def test_english_follow_up_uses_history(self):
        agent = self.make_agent()
        agent.llm = FakeLLM(content="You said you drank 4 cups of pu-erh tea.")
        history = [
            {"role": "user", "content": "I drank 4 cups of pu-erh tea"},
            {"role": "assistant", "content": "Item 'pu-erh tea' is not in your collection. Add it?"},
        ]
        result = agent.process_message("What did I just say?", "device_1", history, lang="en")

        self.assertIn("pu-erh tea", result["response"])
        self.assertEqual(len(agent.llm.calls[0]), 4)


if __name__ == "__main__":
    unittest.main()
