"""第 06 课练习：把一个工具请求变成匹配的 ToolMessage。

运行：uv run python exercises/06_tools_structured_output/exercise.py
默认顺序：手工助手调用消息 → 你的回复函数 → 检查工具消息，不请求模型。
完成后可追加 --live：直接读取根目录 .env，模型请求 → 工具回复 → 模型回答。
本文件独立包含工具、配置和消息流程，不加载导师示例；只有回复函数待补全。
"""

import argparse
from math import isfinite
from pathlib import Path

from dotenv import dotenv_values
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain.tools import tool


@tool
def add_numbers(a: int, b: int) -> int:
    """Add two integers and return their sum."""
    return a + b


def make_tool_reply(call: dict) -> ToolMessage:
    """输入一个工具请求字典，执行已知工具，返回 ID 匹配的工具结果消息。

    任务：检查名称和调用 ID，使用请求中的参数计算，不写死结果。
    框架已经提供 add_numbers；返回值应为 ToolMessage，而不是整数或字符串。
    """
    raise NotImplementedError("请补全 make_tool_reply，执行工具并返回匹配的 ToolMessage。")


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--live", action="store_true", help="完成练习后选择真实模型往返")
    args = arguments.parse_args()
    try:
        if not args.live:
            # 这条消息是手工准备的模拟输入，不能当作模型调用能力的证据。
            request = AIMessage(content="", tool_calls=[{
                "name": "add_numbers", "args": {"a": 37, "b": 58}, "id": "practice-1",
            }])
            reply = make_tool_reply(request.tool_calls[0])
            if not isinstance(reply, ToolMessage):
                raise ValueError("练习必须返回 ToolMessage。")
            if reply.content != "95" or reply.tool_call_id != "practice-1" or reply.name != "add_numbers":
                raise ValueError("工具结果、调用 ID 或工具名不符合练习要求。")
            print("本地手工消息检查通过：", reply.type, reply.content, reply.tool_call_id)
            print("未发送模型请求；还需检查更换数字和错误输入时的行为。")
            return 0

        # 真实模式的配置与初始化直接写在当前文件，不隐藏到其他示例里。
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
        messages = [
            SystemMessage(content="请使用工具计算，然后根据工具结果用简体中文简短回答。"),
            HumanMessage(content="请用 add_numbers 计算 37 加 58。"),
        ]
        bound_model = model.bind_tools([add_numbers], tool_choice="add_numbers")
        request = bound_model.invoke(messages)  # 第一次真实请求，模型只提出工具调用。
        print("真实工具请求：", request.tool_calls)
        if len(request.tool_calls) != 1:
            raise ValueError("本课要求恰好一个工具调用。")
        reply = make_tool_reply(request.tool_calls[0])  # 运行你的实现。
        messages.extend([request, reply])
        answer = model.invoke(messages)  # 第二次真实请求，读取结果后生成回答。
        print("模型回答：", answer.content)
        if answer.tool_calls or not isinstance(answer.content, str) or "95" not in answer.content:
            raise ValueError("模型未按预期给出本题结果。")
        return 0
    except NotImplementedError as error:
        print("练习尚未完成：", error)
        return 1
    except Exception as error:
        print("练习或请求失败，异常类型：", type(error).__name__)
        print("HTTP 状态：", getattr(error, "status_code", None))
        print("检查返回类型、计算结果、调用 ID 与配置；不打印服务错误原文。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
