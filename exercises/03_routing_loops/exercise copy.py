"""第 03 课练习：只补全 route_after_retrieve，实现最多三次检索。

先描述读取的字段与判断顺序，再替换占位异常。
运行：uv run python exercises/03_routing_loops/exercise.py
"""

from operator import add
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


MAX_ATTEMPTS = 3
RUN_CONFIG = {"recursion_limit": 20}


class State(TypedDict):
    question: str
    find_on_attempt: int
    attempts: int
    found: bool
    attempts_log: Annotated[list[str], add]
    answer: str


def retrieve(state: State) -> dict[str, int | bool | list[str]]:
    attempt = state["attempts"] + 1
    found = state["find_on_attempt"] > 0 and attempt >= state["find_on_attempt"]
    return {
        "attempts": attempt,
        "found": found,
        "attempts_log": [f"第{attempt}次：{'找到' if found else '未找到'}"],
    }


def route_after_retrieve(state: State) -> Literal["answer", "retry", "stop"]:
    """读取检索后的状态，返回映射中的分支标签，不返回字典更新。"""
    # TODO：实现命中、重试、达到上限三种情况，并考虑第三次恰好命中。
    raise NotImplementedError("请补全 route_after_retrieve，返回分支标签。")


def answer(state: State) -> dict[str, str]:
    return {"answer": f"模拟回答：{state['question']}（检索{state['attempts']}次后找到资料）"}


def stop(state: State) -> dict[str, str]:
    return {"answer": f"停止：已检索{state['attempts']}次，仍未找到资料。"}


builder = StateGraph(State)
builder.add_node("retrieve", retrieve)
builder.add_node("answer", answer)
builder.add_node("stop", stop)
builder.add_edge(START, "retrieve")
builder.add_conditional_edges(
    "retrieve",
    route_after_retrieve,
    {"answer": "answer", "retry": "retrieve", "stop": "stop"},
)
builder.add_edge("answer", END)
builder.add_edge("stop", END)
graph = builder.compile()


def main() -> None:
    for target in (1, 2, 3, 0):
        initial_state: State = {
            "question": "什么是条件路由？",
            "find_on_attempt": target,
            "attempts": 0,
            "found": False,
            "attempts_log": [],
            "answer": "",
        }
        print("模拟条件 find_on_attempt =", target)
        print("最终状态：", graph.invoke(initial_state, RUN_CONFIG))


if __name__ == "__main__":
    main()
