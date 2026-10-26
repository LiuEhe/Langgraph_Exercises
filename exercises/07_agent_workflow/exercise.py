"""第 07 课练习：补全带模型调用次数上限的条件路由。

运行：uv run python exercises/07_agent_workflow/exercise.py
默认：三份手工状态 → 你的路由 → 比较分支，不读取 .env、不请求模型。
完成后追加 --live：当前文件直接初始化模型并执行完整图，最多三次模型请求。
本文件独立包含配置、工具、节点和边，不加载导师示例；只补全路由函数。
"""

import argparse
from math import isfinite
from pathlib import Path

from dotenv import dotenv_values
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


MAX_MODEL_CALLS = 3


@tool
def add_numbers(a: int, b: int) -> int:
    """Add two integers and return their sum."""
    return a + b


class AgentState(MessagesState):
    model_calls: int
    status: str


def route_after_model(state: AgentState) -> str:
    """返回 END、'tools' 或 'stop' 分支标签，不返回状态更新。

    任务：结合 tools_condition 与 MAX_MODEL_CALLS 判断。
    先预测最后一次恰好给出最终答案时的分支，再补全判断顺序。
    """
    destination = tools_condition(state)
    if destination == END:
        return END
    if state["model_calls"] >= MAX_MODEL_CALLS:
        return "stop"
    return "tools"
    # raise NotImplementedError("请补全 route_after_model，区分正常结束、工具执行和次数上限。")


def build_graph(bound_model):
    """返回用学习者路由连接的编译图，构造不请求模型。"""
    def call_model(state: AgentState) -> dict:
        for message in reversed(state["messages"]):
            if not isinstance(message, ToolMessage):
                break
            if message.status == "error":
                raise ValueError("工具返回错误，停止模型循环。")
        response = bound_model.invoke(state["messages"])
        return {"messages": [response], "model_calls": state["model_calls"] + 1,
                "status": "running" if response.tool_calls else "completed"}

    def stop_at_limit(state: AgentState) -> dict:
        return {"status": "limit_reached"}

    # 已有框架：工具返回增量由 MessagesState 合并，再回到模型节点。
    builder = StateGraph(AgentState)
    builder.add_node("model", call_model)
    builder.add_node("tools", ToolNode([add_numbers], handle_tool_errors=False))
    builder.add_node("stop", stop_at_limit)
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", route_after_model, {"tools": "tools", "stop": "stop", END: END})
    builder.add_edge("tools", "model")
    builder.add_edge("stop", END)
    return builder.compile()


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--live", action="store_true")
    args = arguments.parse_args()
    try:
        if not args.live:
            # 均为手工状态，不是模型生成结果；无需读取配置。
            final_answer = AIMessage(content="结果为 95。")
            request = AIMessage(content="", tool_calls=[{
                "name": "add_numbers", "args": {"a": 37, "b": 58}, "id": "practice-1",
            }])
            for message, count, expected in [
                (final_answer, 3, END), (request, 1, "tools"), (request, 3, "stop"),
            ]:
                actual = route_after_model({"messages": [message], "model_calls": count, "status": "running"})
                print("模型次数：", count, "有工具请求：", bool(message.tool_calls), "路由：", actual)
                if actual != expected:
                    raise ValueError("路由与当前案例预期不一致。")
            print("三份本地状态检查通过；尚未验证你的路由在完整图中的行为。")
            return 0

        # 真实模式的配置、初始化与建图都在当前文件可见。
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
        model = init_chat_model(
            model=config["LLM_MODEL"], model_provider="openai",
            api_key=config["LLM_API_KEY"], base_url=config["LLM_BASE_URL"],
            timeout=timeout, max_tokens=512, max_retries=0,
            use_responses_api=False, stream_usage=False,
            extra_body={"enable_thinking": False},
        )
        bound_model = model.bind_tools([add_numbers])
        graph = build_graph(bound_model)
        result = graph.invoke({
            "messages": [
                SystemMessage(content="请用 add_numbers 计算，不要心算；得到工具结果后给出最终答案。"),
                HumanMessage(content="请计算 37 加 58。"),
            ], "model_calls": 0, "status": "running",
        }, config={"recursion_limit": 12})
        print("最终状态：", result["status"], "模型请求次数：", result["model_calls"])
        if result["status"] != "completed":
            print("已达到上限，任务仍未完成。")
            return 2
        print("模型回答：", result["messages"][-1].content)
        return 0
    except NotImplementedError as error:
        print("练习尚未完成：", error)
        return 1
    except Exception as error:
        print("执行失败类型：", type(error).__name__)
        print("HTTP 状态：", getattr(error, "status_code", None))
        print("请核对路由标签、判断顺序和限制；不打印可能包含私有值的服务错误原文。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
