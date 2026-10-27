"""第 08 课：观察线程状态、快照和历史。

运行：uv run python examples/08_checkpoint_resume/demo.py
顺序：构造内存保存器 → 同线程两次累加 → 对比新线程 → 读取快照与历史。
最后对比共享/全新保存器及输入覆盖。全部为普通 Python，不读取 .env、不请求模型。
"""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph


class CounterState(TypedDict):
    increment: int  # 本次要增加的值，每次输入可覆盖。
    total: int      # 节点返回的新总数；下一次同线程调用可以继续使用。


def add_increment(state: CounterState) -> dict[str, int]:
    """读取已有总数和本次增量，只返回 total 字段更新。"""
    return {"total": state.get("total", 0) + state["increment"]}


def build_graph(checkpointer: InMemorySaver | None = None):
    """返回编译图；传入保存器可共享其内存，不传则为这张图新建一个。"""
    if checkpointer is None:
        checkpointer = InMemorySaver()
    builder = StateGraph(CounterState)
    builder.add_node("add", add_increment)
    builder.add_edge(START, "add")
    builder.add_edge("add", END)
    # 编译时接入保存器，不会执行节点；invoke 时才按线程保存检查点。
    return builder.compile(checkpointer=checkpointer)


def main() -> int:
    checkpointer = InMemorySaver()
    graph = build_graph(checkpointer)
    config_a = {"configurable": {"thread_id": "counter-a"}}
    config_b = {"configurable": {"thread_id": "counter-b"}}

    first = graph.invoke({"increment": 2, "total": 0}, config_a)
    # 第二次不传 total，让节点接着线程 A 保存的总数计算。
    second = graph.invoke({"increment": 3}, config_a)
    separate = graph.invoke({"increment": 3}, config_b)
    print("线程 A 第一次：", first)
    print("线程 A 第二次：", second)
    print("新线程 B：", separate)

    # get_state 只读取 StateSnapshot；values 是业务状态，next 是待执行节点元组。
    snapshot = graph.get_state(config_a)
    print("快照类型：", type(snapshot).__name__)
    print("快照 values：", snapshot.values)
    print("快照 next：", snapshot.next)
    # get_state_history 返回迭代器；本课历史很短，才一次转成 list 观察。
    history = list(graph.get_state_history(config_a))
    print("历史快照数量：", len(history))
    print("历史 total（新到旧）：", [item.values.get("total") for item in history])
    print("历史读取后的 total：", graph.get_state(config_a).values["total"])

    # 状态保存在 checkpointer 中，而不是依附于某一个 graph 变量名。
    recompiled = build_graph(checkpointer)
    fresh = build_graph(InMemorySaver())
    print("重编译但共享保存器：", recompiled.get_state(config_a).values)
    print("换全新保存器：", fresh.get_state(config_a).values)
    print("这里只对比保存器实例，未实际重启进程；内存也不提供重启持久性。")

    # 最后演示输入覆盖：显式传 total=0 就是在要求从零重算。
    overwritten = graph.invoke({"increment": 3, "total": 0}, config_a)
    print("显式覆盖 total 后：", overwritten)
    if (first["total"], second["total"], separate["total"], overwritten["total"]) != (2, 5, 3, 3):
        raise ValueError("状态累积或覆盖结果不符合预期。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
