"""第 06 课：观察模型请求 → Python 工具 → 工具结果 → 模型回答。

运行：uv run python examples/06_tools_structured_output/demo.py
本地观察：同一命令追加 --local-only，不读取凭据、不请求模型。
默认直接读取根目录 .env，真实请求最多两次；工具是本地整数乘法，非模拟计算。
本文件完整包含配置、工具和消息往返，不加载其他示例。
"""

import argparse
from math import isfinite
from pathlib import Path
from time import perf_counter

from dotenv import dotenv_values
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, SystemMessage, ToolMessage
from langchain.tools import tool


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers and return their product."""
    # @tool 将函数包装成工具对象；invoke 传入参数字典后才执行这行。
    return a * b


def make_tool_reply(call: dict) -> ToolMessage:
    """读取一个调用字典，执行已知工具，返回与请求 ID 匹配的工具消息。

    输入示例：name=multiply、args={a:7,b:8}、id=call-a。
    返回的 content 为字符串 '56'，tool_call_id 为 call-a；不请求模型。
    """
    if call.get("name") != multiply.name:
        raise ValueError("模型请求了本课未提供的工具。")
    call_id = call.get("id")
    if not isinstance(call_id, str) or not call_id.strip():
        raise ValueError("工具请求缺少有效调用 ID。")
    # 只把 args 交给已知工具；不按字符串动态查找或执行任意函数。
    result = multiply.invoke(call["args"])
    return ToolMessage(content=str(result), tool_call_id=call_id, name=multiply.name)


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--local-only", action="store_true")
    args = arguments.parse_args()
    print("工具对象：", type(multiply).__name__)
    print("工具名：", multiply.name)
    print("工具描述：", multiply.description)
    print("参数说明：", multiply.args)
    if args.local_only:
        result = multiply.invoke({"a": 7, "b": 8})
        print("本地计算：", result, "返回类型：", type(result).__name__)
        print("未发送模型请求。")
        return 0

    # 1. 配置和模型初始化直接写在本文件，沿用已有配置，不打印私有值。
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

    stage = "模型初始化"
    started = perf_counter()
    try:
        model = init_chat_model(
            model=config["LLM_MODEL"], model_provider="openai",
            api_key=config["LLM_API_KEY"], base_url=config["LLM_BASE_URL"],
            timeout=timeout, max_tokens=512, max_retries=0,
            use_responses_api=False, stream_usage=False,
            extra_body={"enable_thinking": False},
        )
        messages = [
            SystemMessage(content="请用简体中文，根据工具结果简短回答，不编造计算结果。"),
            HumanMessage(content="每箱 7 本书，8 箱一共多少本？请调用 multiply 工具计算。"),
        ]

        # 2. 绑定工具定义，不执行工具。具名选择用于本课控制路径。
        bound_model = model.bind_tools([multiply], tool_choice="multiply")
        print("绑定返回对象：", type(bound_model).__name__)
        stage = "第一次模型请求"
        request = bound_model.invoke(messages)
        print("第一次返回：", type(request).__name__)
        print("工具调用请求：", request.tool_calls)
        print("第一次 token 用量：", request.usage_metadata)
        if len(request.tool_calls) != 1:
            raise ValueError("本例要求恰好一个工具调用，服务返回不符合预期。")

        # 3. 执行本地 Python 工具；回复携带与原请求相同的 tool_call_id。
        stage = "本地工具执行"
        reply = make_tool_reply(request.tool_calls[0])
        if reply.content != "56":
            raise ValueError("工具参数未计算出本题预期值 56。")
        print("工具回复：", type(reply).__name__, reply.content)
        print("调用 ID 匹配：", reply.tool_call_id == request.tool_calls[0]["id"])
        messages.append(request)
        messages.append(reply)
        print("第二次请求角色：", [message.type for message in messages])

        # 4. 用原模型读取结果，不再次强制调用工具，因此固定为两次请求。
        stage = "第二次模型请求"
        answer = model.invoke(messages)
        print("第二次返回：", type(answer).__name__)
        print("模型回答：", answer.content)
        print("第二次 token 用量：", answer.usage_metadata)
        if answer.tool_calls or not isinstance(answer.content, str) or "56" not in answer.content:
            raise ValueError("最终回答未按预期包含结果，或再次提出工具调用。")
        messages.append(answer)
        print("最终角色顺序：", [message.type for message in messages])
        print("客户端总耗时秒数：", round(perf_counter() - started, 3))
        return 0
    except Exception as error:
        print("失败阶段：", stage, "异常类型：", type(error).__name__)
        print("HTTP 状态：", getattr(error, "status_code", None))
        print("请按讲义排查；不打印可能包含私有信息的服务错误原文。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
