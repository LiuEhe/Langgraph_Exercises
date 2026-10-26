"""离线验证真实图和封装循环；模型替身只返回手工消息，不访问服务。"""

from pathlib import Path
import runpy
import unittest

from langchain.agents.middleware.model_call_limit import ModelCallLimitExceededError
from langchain.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.prebuilt.tool_node import ToolInvocationError
from pydantic import Field, ValidationError


ROOT = Path(__file__).resolve().parents[1]


class ScriptedModel(BaseChatModel):
    responses: list[AIMessage]
    calls: int = 0
    inputs: list = Field(default_factory=list)

    @property
    def _llm_type(self):
        return "offline-lesson-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.inputs.append(list(messages))
        response = self.responses[min(self.calls, len(self.responses) - 1)].model_copy(deep=True)
        self.calls += 1
        for index, call in enumerate(response.tool_calls):
            call["id"] = f"call-{self.calls}-{index}"
        return ChatResult(generations=[ChatGeneration(message=response)])


def tool_request(arguments=None, name="add_numbers"):
    return AIMessage(content="", tool_calls=[{
        "name": name, "args": arguments if arguments is not None else {"a": 37, "b": 58},
        "id": "replaced-for-each-call",
    }])


class AgentWorkflowTests(unittest.TestCase):
    def load(self, filename="demo.py"):
        path = ROOT / "examples/07_agent_workflow" / filename
        self.assertTrue(path.is_file(), "第 07 课配套示例尚未创建")
        return runpy.run_path(str(path))

    def invoke_graph(self, model, limit=3):
        demo = self.load()
        graph = demo["build_graph"](model, max_model_calls=limit)
        return graph.invoke({
            "messages": [HumanMessage(content="请计算 37 加 58。")],
            "model_calls": 0, "status": "running",
        }, config={"recursion_limit": 12})

    def test_direct_answer_finishes_without_running_tools(self):
        model = ScriptedModel(responses=[AIMessage(content="直接回答。")])
        state = self.invoke_graph(model)
        self.assertEqual((model.calls, state["model_calls"], state["status"]), (1, 1, "completed"))
        self.assertFalse(any(isinstance(message, ToolMessage) for message in state["messages"]))

    def test_tool_result_is_merged_before_second_model_call(self):
        model = ScriptedModel(responses=[tool_request(), AIMessage(content="95")])
        state = self.invoke_graph(model)
        self.assertEqual(state["model_calls"], 2)
        self.assertEqual(state["status"], "completed")
        self.assertEqual([message.type for message in state["messages"]], ["human", "ai", "tool", "ai"])
        request, reply = model.inputs[1][-2:]
        self.assertEqual(reply.content, "95")
        self.assertEqual(reply.tool_call_id, request.tool_calls[0]["id"])

    def test_answer_on_last_allowed_call_is_still_completed(self):
        model = ScriptedModel(responses=[tool_request(), tool_request(), AIMessage(content="95")])
        state = self.invoke_graph(model)
        self.assertEqual((model.calls, state["status"]), (3, "completed"))

    def test_repeating_tool_requests_stop_before_executing_last_request(self):
        model = ScriptedModel(responses=[tool_request()])
        state = self.invoke_graph(model)
        self.assertEqual((model.calls, state["model_calls"], state["status"]), (3, 3, "limit_reached"))
        self.assertEqual(sum(isinstance(message, ToolMessage) for message in state["messages"]), 2)
        self.assertTrue(state["messages"][-1].tool_calls)

    def test_invalid_tool_arguments_propagate_without_another_model_request(self):
        model = ScriptedModel(responses=[tool_request({"a": "invalid-number", "b": 2})])
        with self.assertRaises((ToolInvocationError, ValidationError)):
            self.invoke_graph(model)
        self.assertEqual(model.calls, 1)

    def test_unknown_tool_error_is_not_sent_as_success_to_model(self):
        model = ScriptedModel(responses=[tool_request(name="unknown")])
        with self.assertRaisesRegex(ValueError, "工具返回错误"):
            self.invoke_graph(model)
        self.assertEqual(model.calls, 1)

    def test_create_agent_returns_tool_roundtrip_messages(self):
        demo = self.load("demo_create_agent.py")
        model = ScriptedModel(responses=[tool_request(), AIMessage(content="95")])
        agent = demo["build_agent"](model)
        result = agent.invoke({"messages": [HumanMessage(content="请计算 37 加 58。") ]},
                              config={"recursion_limit": 24})
        self.assertEqual(model.calls, 2)
        self.assertEqual(result["messages"][-1].content, "95")
        reply = next(message for message in result["messages"] if isinstance(message, ToolMessage))
        self.assertEqual(reply.content, "95")
        self.assertEqual(reply.tool_call_id, "call-1-0")

    def test_create_agent_limit_blocks_fourth_model_call(self):
        demo = self.load("demo_create_agent.py")
        model = ScriptedModel(responses=[tool_request()])
        agent = demo["build_agent"](model, max_model_calls=3)
        with self.assertRaises(ModelCallLimitExceededError):
            agent.invoke({"messages": [HumanMessage(content="继续计算。") ]},
                         config={"recursion_limit": 24})
        self.assertEqual(model.calls, 3)


if __name__ == "__main__":
    unittest.main()
