"""第 07 课对照：create_agent 封装工具循环，显式添加模型调用上限。

运行：uv run python examples/07_agent_workflow/demo_create_agent.py
顺序：直接读取 .env → 初始化模型 → create_agent → invoke → 观察最终消息状态。
最多三次真实模型请求；工具是本地加法，不加载主示例、不模拟远程成功。
"""

from math import isfinite
from pathlib import Path
from time import perf_counter

from dotenv import dotenv_values
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, ToolMessage
from langchain.tools import tool


@tool
def add_numbers(a: int, b: int) -> int:
    """Add two integers and return their sum."""
    return a + b


def build_agent(model, max_model_calls: int = 3):
    """用当前文件的工具创建编译图，构造本身不发送模型请求。"""
    return create_agent(
        model=model,
        tools=[add_numbers],
        system_prompt="请使用 add_numbers 计算，不要心算。拿到结果后用简体中文给出最终答案。",
        middleware=[ModelCallLimitMiddleware(run_limit=max_model_calls, exit_behavior="error")],
    )


def main() -> int:
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
        # 工具列表交给 create_agent 组织；传入原模型，不强制反复调用工具。
        agent = build_agent(model, max_model_calls=3)
        print("Agent 对象：", type(agent).__name__)
        result = agent.invoke({
            "messages": [HumanMessage(content="请计算 37 加 58。")],
        }, config={"recursion_limit": 24})
        print("最终状态类型：", type(result).__name__)
        print("消息角色：", [message.type for message in result["messages"]])
        for message in result["messages"]:
            if isinstance(message, ToolMessage):
                print("工具结果与调用 ID：", message.content, message.tool_call_id)
        answer = result["messages"][-1]
        if answer.type != "ai" or answer.tool_calls or "95" not in answer.content:
            raise ValueError("尚未得到本题预期的最终助手回答。")
        if not any(isinstance(message, ToolMessage) and message.content == "95"
                   for message in result["messages"]):
            raise ValueError("本次没有观察到工具实际执行的结果。")
        print("最终回答：", answer.content)
        model_messages = [message for message in result["messages"] if message.type == "ai"]
        print("模型消息数量：", len(model_messages))
        print("各模型消息 token 用量：", [message.usage_metadata for message in model_messages])
        print("客户端总耗时秒数：", round(perf_counter() - started, 3))
        return 0
    except Exception as error:
        # 包括 ModelCallLimitExceededError：限制退出不能描述为成功回答。
        print("Agent 未完成，异常类型：", type(error).__name__)
        print("HTTP 状态：", getattr(error, "status_code", None))
        print("请按讲义检查模型调用上限、图步数或工具异常；不打印服务错误原文。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
