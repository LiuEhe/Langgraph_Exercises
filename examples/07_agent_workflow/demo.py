"""第 07 课主示例：手写有调用上限的模型—工具循环。

运行：uv run python examples/07_agent_workflow/demo.py
顺序：直接读取 .env → 构造模型和图 → 模型提出请求 → ToolNode 执行 → 模型判断。
模型最多请求三次，自动重试为 0；工具是本地真实加法，不是检索或模拟服务。
本文件独立包含配置、工具、节点和边，不加载其他示例。
"""

from math import isfinite
from pathlib import Path
from time import perf_counter

from dotenv import dotenv_values
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, SystemMessage, ToolMessage
from langchain.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


@tool
def add_numbers(a: int, b: int) -> int:
    """Add two integers and return their sum."""
    return a + b


class AgentState(MessagesState):
    # messages 继承 add_messages 规则；另外两个字段按节点返回值覆盖。
    model_calls: int
    status: str


def build_graph(bound_model, max_model_calls: int = 3):
    """接收已绑定工具的模型，返回编译图；建图本身不请求模型。

    内部节点直接使用本函数收到的模型，这叫闭包：仍在当前文件内，
    不是去其他脚本寻找初始化。调用次数由状态字段和路由共同控制。
    """
    if max_model_calls < 1:
        raise ValueError("模型调用上限必须至少为 1。")

    def call_model(state: AgentState) -> dict:
        """读取完整消息，返回本次助手消息和计数更新，不返回整个历史。"""
        # ToolNode 对未知工具可能返回 error 消息；不把它当成功结果继续请求。
        for message in reversed(state["messages"]):
            if not isinstance(message, ToolMessage):
                break
            if message.status == "error":
                raise ValueError("工具返回错误，停止模型循环。")
        response = bound_model.invoke(state["messages"])
        return {
            "messages": [response],
            "model_calls": state["model_calls"] + 1,
            "status": "running" if response.tool_calls else "completed",
        }

    def route_after_model(state: AgentState) -> str:
        """返回分支标签；先接受正常答案，再限制仍想继续的调用。"""
        destination = tools_condition(state)
        if destination == END:
            return END
        if state["model_calls"] >= max_model_calls:
            return "stop"
        return "tools"

    def stop_at_limit(state: AgentState) -> dict:
        """只标记未完成；不伪造模型回答或未执行工具的结果。"""
        return {"status": "limit_reached"}

    # ToolNode 只执行已注册的工具，并返回 ToolMessage 增量。
    builder = StateGraph(AgentState)
    builder.add_node("model", call_model)
    builder.add_node("tools", ToolNode([add_numbers], handle_tool_errors=False))
    builder.add_node("stop", stop_at_limit)
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", route_after_model, {
        "tools": "tools", "stop": "stop", END: END,
    })
    builder.add_edge("tools", "model")
    builder.add_edge("stop", END)
    return builder.compile()


def main() -> int:
    # 配置读取和初始化在本文件中可见，不打印密钥或私有地址。
    config = dotenv_values(Path(__file__).resolve().parents[2] / ".env")
    required = ("LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY", "LLM_BASE_URL", "LLM_TIMEOUT_SECONDS")
    missing = [key for key in required if not (config.get(key) or "").strip()]
    if missing:
        print("根目录 .env 缺少：", ", ".join(missing))
        return 1
    if config["LLM_PROVIDER"] != "openai_compatible":
        print("LLM_PROVIDER 本课仅支持 openai_compatible。")
        return 1
    try:
        timeout = float(config["LLM_TIMEOUT_SECONDS"])
        if not isfinite(timeout) or timeout <= 0:
            raise ValueError
    except ValueError:
        print("LLM_TIMEOUT_SECONDS 必须是有限正数。")
        return 1

    started = perf_counter()
    try:
        model = init_chat_model(
            model=config["LLM_MODEL"], model_provider="openai",
            api_key=config["LLM_API_KEY"], base_url=config["LLM_BASE_URL"],
            timeout=timeout, max_tokens=512, max_retries=0,
            use_responses_api=False, stream_usage=False,
            extra_body={"enable_thinking": False},
        )
        bound_model = model.bind_tools([add_numbers])  # 不强制每次都选择工具。
        graph = build_graph(bound_model, max_model_calls=3)
        print("图对象：", type(graph).__name__)
        result = graph.invoke({
            "messages": [
                SystemMessage(content="请使用 add_numbers 计算，不要心算。拿到结果后用简体中文给出最终答案。"),
                HumanMessage(content="请计算 37 加 58。"),
            ],
            "model_calls": 0, "status": "running",
        }, config={"recursion_limit": 12})
        print("最终状态类型：", type(result).__name__)
        print("模型请求次数：", result["model_calls"], "状态：", result["status"])
        print("消息角色：", [message.type for message in result["messages"]])
        for message in result["messages"]:
            if isinstance(message, ToolMessage):
                print("工具结果与调用 ID：", message.content, message.tool_call_id)
        if result["status"] != "completed":
            print("达到上限，最后的工具请求未执行，任务尚未完成。")
            return 2
        answer = result["messages"][-1]
        print("最终回答：", answer.content)
        tool_replies = [message for message in result["messages"] if isinstance(message, ToolMessage)]
        if not any(reply.content == "95" for reply in tool_replies) or "95" not in answer.content:
            raise ValueError("本次没有观察到预期的工具结果与最终回答。")
        print("客户端总耗时秒数：", round(perf_counter() - started, 3))
        usage = [message.usage_metadata for message in result["messages"] if message.type == "ai"]
        print("各模型消息 token 用量：", usage)
        return 0
    except Exception as error:
        print("图执行失败，异常类型：", type(error).__name__)
        print("HTTP 状态：", getattr(error, "status_code", None))
        print("不打印可能包含私有值的异常原文；请按讲义区分路由、工具和模型错误。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
