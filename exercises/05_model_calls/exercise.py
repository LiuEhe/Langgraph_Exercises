"""第 05 课练习：补全 build_chain，组合模板、模型、文本解析器。

运行：uv run python exercises/05_model_calls/exercise.py
顺序：直接读取根目录 .env → 构造模型 → 组合链 → 调用一次 → 读文本。
模板是本地格式化；完成后执行 chain.invoke 会发送一次真实模型请求。
本文件独立运行；配置读取、模型初始化和管道执行都在下面，不加载 demo.py。
"""

from math import isfinite
from pathlib import Path

from dotenv import dotenv_values
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable


prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一名 LangGraph 导师。请用简体中文简短回答。"),
    ("human", "请用一句话解释 {concept}，不超过 40 个汉字。"),
])


def build_chain(model: BaseChatModel) -> Runnable:
    """返回可运行管道；接收变量字典，执行后输出 str，构造时不请求模型。

    任务：使用给定 prompt、传入的 model 和 StrOutputParser 组合。
    不在这里调用 invoke，不返回固定回答；核心组合留给学习者实现。
    """
    return prompt | model | StrOutputParser()


def main() -> int:
    # 1. 从当前文件向上两级找到项目根目录，直接把 .env 读成字典。
    # 不打印 config，其中包含密钥和私有服务地址。
    env_path = Path(__file__).resolve().parents[2] / ".env"
    config = dotenv_values(env_path)
    required = ("LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY", "LLM_BASE_URL", "LLM_TIMEOUT_SECONDS")
    missing = [name for name in required if not (config.get(name) or "").strip()]
    if missing:
        print("根目录 .env 缺少配置：", ", ".join(missing))
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

    try:
        # 2. 将本项目的 LLM_* 显式映射为模型参数；此步不发送请求。
        model = init_chat_model(
            model=config["LLM_MODEL"],
            model_provider="openai",
            api_key=config["LLM_API_KEY"],
            base_url=config["LLM_BASE_URL"],
            timeout=timeout,
            max_tokens=512,
            max_retries=0,
            use_responses_api=False,
            stream_usage=False,
            extra_body={"enable_thinking": False},  # 默认关闭思考模式。
        )
        # 3. 保留你完成的组合函数；构造管道与执行管道是两步。
        chain = build_chain(model)
        if not isinstance(chain, Runnable):
            print("练习未通过：build_chain 需要返回 Runnable 管道，当前没有返回管道。")
            print("请组合模板、模型与解析器并返回；把 invoke 留在 main 中执行。")
            return 1
        # 4. 在这里发送一次真实请求，解析器把模型消息转成文本。
        text = chain.invoke({"concept": "python"})
        if not isinstance(text, str) or not text.strip():
            raise ValueError("练习应返回非空 str。")
        print("返回类型：", type(text).__name__)
        print("模型回答：", text)
    except NotImplementedError as error:
        print("练习尚未完成：", error)
        return 1
    except Exception as error:
        print("执行失败类型：", type(error).__name__)
        print("HTTP 状态：", getattr(error, "status_code", None))
        print("请按讲义检查；不打印可能包含私有信息的异常原文。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
