"""工具调用的消息配对、拒绝路径和字段约束；不请求真实模型。"""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

from langchain.messages import AIMessage, ToolMessage
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]


class ToolLessonTests(unittest.TestCase):
    def load(self, filename="demo.py"):
        path = ROOT / "examples/06_tools_structured_output" / filename
        self.assertTrue(path.is_file(), "第 06 课配套示例尚未创建")
        return runpy.run_path(str(path))

    def test_reply_uses_calculated_result_and_matches_each_call_id(self):
        demo = self.load()
        for call_id, a, b, expected in [("call-a", 7, 8, "56"), ("call-b", 3, 9, "27")]:
            with self.subTest(call_id=call_id):
                call = {"name": "multiply", "args": {"a": a, "b": b}, "id": call_id}
                reply = demo["make_tool_reply"](call)
                self.assertIsInstance(reply, ToolMessage)
                self.assertEqual(reply.content, expected)
                self.assertEqual(reply.tool_call_id, call_id)
                self.assertEqual(reply.name, "multiply")
                self.assertEqual(call["args"], {"a": a, "b": b})

    def test_unknown_tool_missing_id_and_invalid_arguments_are_rejected(self):
        demo = self.load()
        for call in [
            {"name": "unknown", "args": {"a": 7, "b": 8}, "id": "call-a"},
            {"name": "multiply", "args": {"a": 7, "b": 8}},
            {"name": "multiply", "args": {"a": 7, "b": 8}, "id": ""},
        ]:
            with self.subTest(call=call), self.assertRaises(ValueError):
                demo["make_tool_reply"](call)
        for arguments in [{"a": 7}, {"a": "not-an-integer", "b": 8}]:
            with self.subTest(arguments=arguments), self.assertRaises(ValidationError):
                demo["make_tool_reply"]({"name": "multiply", "args": arguments, "id": "call-a"})

    def test_main_sends_request_and_matching_tool_reply_before_final_answer(self):
        demo = self.load()

        class OfflineToolModel:
            def __init__(self):
                self.inputs = []

            def bind_tools(self, tools, **kwargs):
                return self

            def invoke(self, messages):
                self.inputs.append(list(messages))
                if len(self.inputs) == 1:
                    return AIMessage(content="", tool_calls=[{
                        "name": "multiply", "args": {"a": 7, "b": 8}, "id": "offline-call",
                    }])
                return AIMessage(content="一共 56 本书。")

        model = OfflineToolModel()
        config = {
            "LLM_PROVIDER": "openai_compatible", "LLM_MODEL": "unused",
            "LLM_API_KEY": "unused", "LLM_BASE_URL": "https://provider.example/v1",
            "LLM_TIMEOUT_SECONDS": "2",
        }
        with patch.dict(demo["main"].__globals__, {
            "dotenv_values": lambda path: config,
            "init_chat_model": lambda **kwargs: model,
        }), patch.object(sys, "argv", ["demo.py"]), redirect_stdout(StringIO()):
            self.assertEqual(demo["main"](), 0)
        self.assertEqual(len(model.inputs), 2)
        self.assertEqual([message.type for message in model.inputs[1]], ["system", "human", "ai", "tool"])
        request, reply = model.inputs[1][-2:]
        self.assertEqual(reply.tool_call_id, request.tool_calls[0]["id"])
        self.assertEqual(reply.content, "56")

    def test_schema_extracts_fields_and_rejects_invalid_quantity(self):
        demo = self.load("demo_structured.py")
        schema = demo["OrderInfo"]
        order = schema(product="键盘", quantity=2)
        self.assertEqual(order.model_dump(), {"product": "键盘", "quantity": 2})
        self.assertIsInstance(order.quantity, int)
        with self.assertRaises(ValidationError):
            schema(product="键盘", quantity=0)
        with self.assertRaises(ValidationError):
            schema(product="键盘")


if __name__ == "__main__":
    unittest.main()
