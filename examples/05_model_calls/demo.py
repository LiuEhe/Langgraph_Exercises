"""第 05 课：从模板到真实模型，逐个观察返回类型与调度方式。

运行：uv run python examples/05_model_calls/demo.py
直接读取项目根目录 .env，不需要 --env-file，也不会重启脚本。
顺序：配置校验 → 构造模型 → 格式化模板 → 一次请求 → 观察消息和文本。
默认模式只发一次真实请求，不使用模拟回答。--mode check 完全不发请求；
stream/chain/async 各一次，batch 两次，需分别显式运行。
"""

import argparse
import asyncio
from collections.abc import Mapping
from math import isfinite
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

from dotenv import dotenv_values
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, AIMessageChunk
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


MODEL_ENV_NAMES = (
    "LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY",
    "LLM_BASE_URL", "LLM_TIMEOUT_SECONDS",
)


class ConfigurationError(ValueError):
    """只包含变量名和修正方向的配置错误，不包含私有配置值。"""


def build_model(environ: Mapping[str, str | None] | None = None) -> BaseChatModel:
    """读取并校验五项配置，返回模型客户端；构造对象不会发送生成请求。

    默认直接读取根目录 .env，测试时可传入假配置字典，不必接触真实凭据。
    自定义 LLM_* 必须显式映射，不能期待 LangChain 自动读取这些名字。
    """
    # dotenv_values 返回配置字典，不修改进程环境，也不启动其他脚本。
    env_path = Path(__file__).resolve().parents[2] / ".env"
    source = dotenv_values(env_path) if environ is None else environ
    config = {}
    for name in MODEL_ENV_NAMES:
        value = (source.get(name) or "").strip()
        if not value:
            raise ConfigurationError(f"{name} 缺失或为空；检查项目根目录 .env。")
        config[name] = value

    if config["LLM_PROVIDER"] != "openai_compatible":
        raise ConfigurationError("LLM_PROVIDER 本课仅支持 openai_compatible。")

    try:
        timeout = float(config["LLM_TIMEOUT_SECONDS"])
    except ValueError:
        raise ConfigurationError("LLM_TIMEOUT_SECONDS 必须是有限正数。") from None
    if not isfinite(timeout) or timeout <= 0:
        raise ConfigurationError("LLM_TIMEOUT_SECONDS 必须是有限正数。")

    try:
        url = urlsplit(config["LLM_BASE_URL"])
        valid_url = url.scheme in {"http", "https"} and bool(url.hostname)
    except ValueError:
        valid_url = False
    if not valid_url:
        raise ConfigurationError("LLM_BASE_URL 必须是含主机名的 HTTP(S) 地址。")

    # init_chat_model 是统一初始化入口；本项目标记选择 openai 适配实现，
    # base_url 决定实际服务。返回 ChatOpenAI 对象，并非返回生成的回答。
    return init_chat_model(
        model=config["LLM_MODEL"],
        model_provider="openai",
        api_key=config["LLM_API_KEY"],
        base_url=config["LLM_BASE_URL"],
        timeout=timeout,
        max_tokens=512,             # 有限预算，包含部分模型的推理消耗；不是汉字数。
        max_retries=0,              # 不自动重试，控制首次验证请求数量。
        use_responses_api=False,   # 显式走 Chat Completions 兼容路径。
        stream_usage=False,        # 不假定兼容服务支持流式用量扩展。
        extra_body={"enable_thinking": False},  # Qwen 扩展参数：关闭思考模式。
    )


# 构造模板只定义规则，不生成回答。此处没有历史占位符，输入仅需 concept。
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一名 LangGraph 导师。请用简体中文简短回答。"),
    ("human", "请用一句话解释 {concept}，不超过 40 个汉字。"),
])


def show_response(response: AIMessage) -> None:
    """检查并展示已有模型消息的关键字段；解析已有消息不发第二次请求。"""
    if not isinstance(response, AIMessage):
        raise TypeError("本课预期模型返回 AIMessage。")
    parser = StrOutputParser()
    text = parser.invoke(response)
    print("模型返回对象：", type(response).__name__)
    print("消息角色：", response.type)
    print("content 类型：", type(response.content).__name__)
    print("模型回答：", text)
    print("工具调用数量：", len(response.tool_calls))
    # 只取需要的字段，不打印整个对象或包含服务信息的完整元数据。
    print("结束原因：", response.response_metadata.get("finish_reason", "未提供"))
    print("token 用量：", response.usage_metadata)
    print("解析后类型：", type(text).__name__)
    if not text.strip():
        # 先展示结束原因和用量，避免丢失“预算耗尽但正文为空”的诊断证据。
        raise ValueError("模型返回空文本，需检查服务响应及生成预算。")


def run_mode(model: BaseChatModel, mode: str) -> None:
    """按选择的模式执行；输入为已构造模型，输出为控制台观察结果。"""
    if mode == "check":
        print("配置校验通过；模型对象：", type(model).__name__)
        print("未发送模型请求。")
        return

    # 模板 invoke 得到 ChatPromptValue；to_messages 才拿到普通消息列表。
    prompt_value = prompt.invoke({"concept": "State"})
    messages = prompt_value.to_messages()
    print("模板返回对象：", type(prompt_value).__name__)
    print(messages)
    print("输入角色：", [message.type for message in messages])
    started = perf_counter()

    if mode == "invoke":
        response = model.invoke(messages)  # 这里才发送一次真实请求。
        show_response(response)
    elif mode == "stream":
        # 流是迭代器，for 每次取出一个块；空块也要保留供元数据合并。
        combined = None
        first_chunk = None
        first_text = None
        count = 0
        parser = StrOutputParser()
        print("流式文本：", end="", flush=True)
        for chunk in model.stream(messages):
            if not isinstance(chunk, AIMessageChunk):
                raise TypeError("本课预期流式返回 AIMessageChunk。")
            elapsed = perf_counter() - started
            if first_chunk is None:
                first_chunk = elapsed
            # parser.invoke 仅把当前块转成文本；可能得到空字符串。
            text = parser.invoke(chunk)
            if text and first_text is None:
                first_text = elapsed
            print(text, end="", flush=True)
            # + 使用消息块的合并规则，保留内容和可合并的元数据。
            combined = chunk if combined is None else combined + chunk
            count += 1
        print()
        if combined is None:
            raise ValueError("流式请求未产生非空文本。")
        print("块类型：", type(combined).__name__, "块数：", count)
        print("首块秒数：", round(first_chunk, 3))
        print("首个文本块秒数：", None if first_text is None else round(first_text, 3))
        print("结束原因：", combined.response_metadata.get("finish_reason", "未提供"))
        print("流式 token 用量：未启用用量扩展；不能按块数计算。")
        if not parser.invoke(combined).strip():
            raise ValueError("流式请求未产生非空文本。")
    elif mode == "batch":
        concepts = ["State", "Node"]
        inputs = [prompt.invoke({"concept": item}) for item in concepts]
        # 两个独立请求，最多同时运行两个；返回顺序对应输入顺序。
        responses = model.batch(inputs, config={"max_concurrency": 2})
        if len(responses) != 2:
            raise ValueError("批量结果数量与两个输入不一致。")
        print("批量返回类型：", type(responses).__name__, "数量：", len(responses))
        for concept, response in zip(concepts, responses, strict=True):
            print("对应输入：", concept)
            show_response(response)
    elif mode == "chain":
        # | 构造 RunnableSequence，不立即执行。链的 invoke 才依次执行三步。
        chain = prompt | model | StrOutputParser()
        print("管道对象：", type(chain).__name__)
        text = chain.invoke({"concept": "Node"})
        if not text.strip():
            raise ValueError("管道未返回非空文本。")
        print("管道返回类型：", type(text).__name__)
        print("模型回答：", text)
    elif mode == "async":
        async def ask_once() -> AIMessage:
            """等待一次真实请求并返回消息；单个异步请求不代表并发。"""
            return await model.ainvoke(messages)

        # 命令行脚本中用 asyncio.run 运行协程，拿到其返回值。
        show_response(asyncio.run(ask_once()))

    print("本模式客户端总耗时秒数：", round(perf_counter() - started, 3))


def main() -> int:
    """解析模式并执行；保留异常类型与 HTTP 状态，不输出私有错误原文。"""
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument(
        "--mode", choices=["check", "invoke", "stream", "batch", "chain", "async"],
        default="invoke",
    )
    args = arguments.parse_args()
    try:
        model = build_model()
        run_mode(model, args.mode)
    except ConfigurationError as error:
        print("配置错误：", error)
        return 1
    except Exception as error:
        # 服务错误可能携带私有地址、请求体等；不用 str(error) 或 traceback。
        # 类型和状态用于区分认证、限流、超时及内容检查失败；详细方向见讲义。
        print("执行失败类型：", type(error).__name__)
        print("HTTP 状态：", getattr(error, "status_code", None))
        print("未打印异常原文；请按讲义检查网络、权限、兼容参数或空响应。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
