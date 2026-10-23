"""离线验证模型配置边界；使用假凭据，仅构造对象，不请求真实服务。"""

from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
import runpy
import unittest

from langchain.messages import AIMessage, AIMessageChunk


DEMO_PATH = Path(__file__).resolve().parents[1] / "examples/05_model_calls/demo.py"


class ModelConfigTests(unittest.TestCase):
    def load_demo(self):
        self.assertTrue(DEMO_PATH.is_file(), "第 05 课模型示例尚未创建")
        return runpy.run_path(str(DEMO_PATH))

    def config(self):
        # 这些是测试数据，不读取学习者的 .env。
        return {
            "LLM_PROVIDER": "openai_compatible",
            "LLM_MODEL": "classroom-model",
            "LLM_API_KEY": "test-key-unused",
            "LLM_BASE_URL": "https://provider.example/v1",
            "LLM_TIMEOUT_SECONDS": "2.5",
        }

    def test_missing_and_blank_fields_are_rejected_without_private_values(self):
        demo = self.load_demo()
        for name in self.config():
            for value in (None, "", "  "):
                with self.subTest(name=name, value=value):
                    config = self.config()
                    if value is None:
                        config.pop(name)
                    else:
                        config[name] = value
                    with self.assertRaises(demo["ConfigurationError"]) as caught:
                        demo["build_model"](config)
                    self.assertIn(name, str(caught.exception))
                    self.assertNotIn("test-key-unused", str(caught.exception))

    def test_timeout_rejects_nonpositive_nonfinite_and_nonnumeric_values(self):
        demo = self.load_demo()
        for value in ("0", "-1", "nan", "inf", "-inf", "private-invalid-timeout"):
            with self.subTest(value=value):
                config = self.config()
                config["LLM_TIMEOUT_SECONDS"] = value
                with self.assertRaises(demo["ConfigurationError"]) as caught:
                    demo["build_model"](config)
                self.assertIn("LLM_TIMEOUT_SECONDS", str(caught.exception))
                self.assertNotIn("private-invalid-timeout", str(caught.exception))

    def test_unsupported_provider_and_malformed_urls_are_rejected(self):
        demo = self.load_demo()
        cases = [
            ("LLM_PROVIDER", "private-unsupported-provider"),
            ("LLM_BASE_URL", "private-malformed-url"),
            ("LLM_BASE_URL", "ftp://provider.example/v1"),
            ("LLM_BASE_URL", "https://"),
        ]
        for name, value in cases:
            with self.subTest(name=name, value=value):
                config = self.config()
                config[name] = value
                with self.assertRaises(demo["ConfigurationError"]) as caught:
                    demo["build_model"](config)
                self.assertIn(name, str(caught.exception))
                self.assertNotIn(value, str(caught.exception))

    def test_valid_config_maps_to_adapter_with_bounded_generation(self):
        demo = self.load_demo()
        model = demo["build_model"](self.config())
        self.assertEqual(type(model).__name__, "ChatOpenAI")
        self.assertEqual(model.model_name, "classroom-model")
        self.assertEqual(model.openai_api_key.get_secret_value(), "test-key-unused")
        self.assertEqual(model.openai_api_base, "https://provider.example/v1")
        self.assertEqual(model.request_timeout, 2.5)
        self.assertEqual(model.max_tokens, 512)
        self.assertEqual(model.max_retries, 0)
        self.assertFalse(model.use_responses_api)
        self.assertFalse(model.stream_usage)

    def test_empty_text_reports_finish_reason_and_usage_before_rejecting(self):
        demo = self.load_demo()
        # 复现真实服务的结构：预算全部用于推理，没有最终文本。
        # 这里是手工消息，不发送请求，也不作为模型成功的证据。
        response = AIMessage(
            content="",
            response_metadata={"finish_reason": "length"},
            usage_metadata={"input_tokens": 78, "output_tokens": 128, "total_tokens": 206},
        )
        output = StringIO()
        with redirect_stdout(output):
            with self.assertRaisesRegex(ValueError, "模型返回空文本"):
                demo["show_response"](response)
        self.assertIn("length", output.getvalue())
        self.assertIn("128", output.getvalue())

    def test_empty_stream_preserves_finish_reason_and_rejects_empty_text(self):
        demo = self.load_demo()

        class EmptyStreamModel:
            """只模拟无文本的服务块，不接触网络或模型配置。"""

            def stream(self, messages):
                yield AIMessageChunk(content="", response_metadata={"finish_reason": "length"})

        output = StringIO()
        with redirect_stdout(output):
            with self.assertRaisesRegex(ValueError, "流式请求未产生非空文本"):
                demo["run_mode"](EmptyStreamModel(), "stream")
        self.assertIn("length", output.getvalue())


if __name__ == "__main__":
    unittest.main()
