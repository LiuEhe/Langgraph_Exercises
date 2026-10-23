"""验证手工模拟消息经过新增与更正后，不丢失原问题或重复回复。"""

from pathlib import Path
import runpy
import unittest

from langchain.messages import AIMessage, HumanMessage


DEMO_PATH = Path(__file__).resolve().parents[1] / "examples/04_prompt_messages/demo_message_state.py"


class MessageStateTests(unittest.TestCase):
    def load_demo(self):
        self.assertTrue(DEMO_PATH.is_file(), "第 04 课消息状态示例尚未创建")
        return runpy.run_path(str(DEMO_PATH))

    def test_revision_replaces_reply_and_preserves_the_original_question(self):
        demo = self.load_demo()
        result = demo["graph"].invoke({
            "messages": [HumanMessage(content="什么是 State？", id="question-1")],
        })
        messages = result["messages"]
        self.assertEqual([message.id for message in messages], ["question-1", "reply-1"])
        self.assertIsInstance(messages[0], HumanMessage)
        self.assertEqual(messages[0].content, "什么是 State？")
        self.assertIsInstance(messages[1], AIMessage)
        self.assertEqual(messages[1].content, "模拟更正：State 保存工作流共享的数据，节点可以只返回部分更新。")

    def test_state_trace_adds_one_reply_then_changes_its_content(self):
        demo = self.load_demo()
        snapshots = list(demo["graph"].stream(
            {"messages": [HumanMessage(content="什么是 State？", id="question-1")]},
            stream_mode="values",
            version="v1",
        ))
        self.assertEqual([len(state["messages"]) for state in snapshots], [1, 2, 2])
        draft = snapshots[1]["messages"][1]
        revised = snapshots[2]["messages"][1]
        self.assertEqual(draft.id, revised.id)
        self.assertNotEqual(draft.content, revised.content)
        self.assertEqual(draft.content, "模拟草稿：State 是共享数据。")
        self.assertTrue(revised.content.startswith("模拟更正："))


if __name__ == "__main__":
    unittest.main()
