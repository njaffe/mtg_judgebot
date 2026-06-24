import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.external import llm_client


class LLMClientTests(unittest.TestCase):
    ENV_KEYS = [
        "LLM_PROVIDER",
        "LLM_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
    ]

    def setUp(self):
        self._old_env = {
            key: os.environ.get(key)
            for key in self.ENV_KEYS
            if key in os.environ
        }
        for key in self.ENV_KEYS:
            os.environ.pop(key, None)

    def tearDown(self):
        for key in self.ENV_KEYS:
            os.environ.pop(key, None)
        for key, value in self._old_env.items():
            os.environ[key] = value

    def test_anthropic_provider_dispatches_to_anthropic_client(self):
        os.environ["LLM_PROVIDER"] = "anthropic"
        expected = {
            "vendor": "anthropic",
            "choices": [{"message": {"content": "ok"}}],
        }

        with patch("src.external.anthropic_client.chat", return_value=expected) as chat:
            result = llm_client.chat(messages=[{"role": "user", "content": "hi"}])

        self.assertEqual(result, expected)
        chat.assert_called_once()
        self.assertEqual(chat.call_args.kwargs["messages"][0]["content"], "hi")

    def test_default_provider_is_anthropic(self):
        expected = {
            "vendor": "anthropic",
            "choices": [{"message": {"content": "ok"}}],
        }

        with patch("src.external.anthropic_client.chat", return_value=expected) as chat:
            result = llm_client.chat(messages=[{"role": "user", "content": "hi"}])

        self.assertEqual(result["vendor"], "anthropic")
        chat.assert_called_once()

    def test_openai_provider_normalizes_chat_completion_response(self):
        os.environ["LLM_PROVIDER"] = "openai"
        os.environ["OPENAI_API_KEY"] = "test-key"
        os.environ["LLM_MODEL"] = "test-model"

        response = Mock()
        response.json.return_value = {
            "model": "test-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "openai ok"},
                }
            ],
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 2,
                "total_tokens": 5,
            },
        }

        with patch("src.external.llm_client.requests.post", return_value=response) as post:
            result = llm_client.chat(messages=[{"role": "user", "content": "hi"}])

        post.assert_called_once()
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["messages"][0]["content"], "hi")
        self.assertEqual(result["vendor"], "openai")
        self.assertEqual(
            result["choices"][0]["message"]["content"],
            "openai ok",
        )
        self.assertEqual(result["usage"]["total_tokens"], 5)
        self.assertIn("latency_ms", result["usage"])

    def test_invalid_provider_raises_clear_error(self):
        os.environ["LLM_PROVIDER"] = "banana"

        with self.assertRaisesRegex(ValueError, "Unsupported LLM_PROVIDER"):
            llm_client.chat(messages=[{"role": "user", "content": "hi"}])


if __name__ == "__main__":
    unittest.main()
