"""第 05 课练习：补全 build_chain，组合模板、模型、文本解析器。

运行：uv run --env-file .env python exercises/05_model_calls/exercise.py
顺序：先补全构造函数 → 校验配置并构造模型 → 组合链 → 调用一次 → 读文本。
模板是本地格式化；完成后执行 chain.invoke 会发送一次真实模型请求。
本课目标是组合管道，配置函数直接从导师示例加载，不修改 sys.path。
"""

from pathlib import Path
import runpy

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
    raise NotImplementedError("请补全 build_chain，组合模板、模型和文本解析器。")


def main() -> int:
    # 用明确文件路径复用同课配置教学代码；模块加载本身不发请求。
    # run_path 返回脚本命名空间字典，不会触发它的 __main__ 入口。
    demo_path = Path(__file__).resolve().parents[2] / "examples/05_model_calls/demo.py"
    demo = runpy.run_path(str(demo_path))
    try:
        model = demo["build_model"]()
        chain = build_chain(model)
        text = chain.invoke({"concept": "条件边"})  # 完成后发送一次请求。
        if not isinstance(text, str) or not text.strip():
            raise ValueError("练习应返回非空 str。")
        print("返回类型：", type(text).__name__)
        print("模型回答：", text)
    except demo["ConfigurationError"] as error:
        print("配置错误：", error)
        return 1
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
