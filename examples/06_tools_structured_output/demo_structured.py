"""第 06 课补充：把订单提取为 Pydantic 字段对象。

运行：uv run python examples/06_tools_structured_output/demo_structured.py
追加 --local-only 只验证本地字段，不读凭据、不请求模型。
默认独立读取 .env，显式用 function_calling 方法请求一次，不执行本地业务工具。
"""

import argparse
from math import isfinite
from pathlib import Path
from time import perf_counter

from dotenv import dotenv_values
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError


class OrderInfo(BaseModel):
    """从订单原文提取商品和购买数量，两项均必需。"""

    product: str = Field(description="订单商品名称")
    quantity: int = Field(ge=1, description="购买数量，必须至少为 1")


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--local-only", action="store_true")
    args = arguments.parse_args()
    if args.local_only:
        # 手工输入验证 schema，不把本地对象当作模型生成结果。
        order = OrderInfo(product="键盘", quantity=2)
        print("本地对象：", type(order).__name__, order.model_dump())
        try:
            OrderInfo(product="键盘", quantity=0)
        except ValidationError as error:
            print("数量 0 被拒绝：", type(error).__name__)
        else:
            print("字段约束未按预期生效。")
            return 1
        print("未发送模型请求。")
        return 0

    # 配置读取和模型构造在当前文件可见，不调用主示例的函数。
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
        # 默认 method 在本版本是 json_schema，本课显式验证 function_calling。
        # include_raw 默认 False，invoke 后直接拿到 OrderInfo，非 AIMessage。
        structured_model = model.with_structured_output(OrderInfo, method="function_calling")
        print("结构化包装对象：", type(structured_model).__name__)
        order = structured_model.invoke([
            SystemMessage(content="只提取用户给出的订单商品和数量，不编造。"),
            HumanMessage(content="订单商品为键盘，数量为 2。"),
        ])
        print("返回对象：", type(order).__name__)
        print("product：", order.product, "类型：", type(order.product).__name__)
        print("quantity：", order.quantity, "类型：", type(order.quantity).__name__)
        print("字段字典：", order.model_dump())
        # 类型有效仍可能事实错误，所以按这条固定输入检查实际字段。
        if not isinstance(order, OrderInfo) or order.product != "键盘" or order.quantity != 2:
            raise ValueError("提取字段与本次输入不一致。")
        print("客户端总耗时秒数：", round(perf_counter() - started, 3))
        print("本模式未保留原始消息，未记录 token 用量；不表示没有消耗。")
        return 0
    except Exception as error:
        print("结构化请求或解析失败，异常类型：", type(error).__name__)
        print("HTTP 状态：", getattr(error, "status_code", None))
        print("不打印可能包含私有值的服务错误原文，请按讲义排查。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
