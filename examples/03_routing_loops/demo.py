"""第 03 课：模拟最多三次检索，观察条件路由和图状态流。"""

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
    # 使用固定次数模拟命中，不访问真实知识库。
    found = state["find_on_attempt"] > 0 and attempt >= state["find_on_attempt"]
    return {
        "attempts": attempt,
        "found": found,
        "attempts_log": [f"第{attempt}次：{'找到' if found else '未找到'}"],
    }


def route_after_retrieve(state: State) -> Literal["answer", "retry", "stop"]:
    # 第三次恰好找到时仍应回答，所以成功条件优先。
    if state["found"]:
        return "answer"
    if state["attempts"] >= MAX_ATTEMPTS:
        return "stop"
    return "retry"


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


def make_initial_state(find_on_attempt: int) -> State:
    """构造新一轮运行的初始状态；传入 0 表示始终未命中。"""
    return {
        "question": "什么是条件路由？",
        "find_on_attempt": find_on_attempt,
        "attempts": 0,
        "found": False,
        "attempts_log": [],
        "answer": "",
    }


def main() -> None:
    for target in (1, 2, 3, 0):
        print("模拟条件 find_on_attempt =", target)
        result = graph.invoke(make_initial_state(target), RUN_CONFIG)
        print("最终状态：", result)

    # 每个模式重新运行一次图，分别比较节点增量与完整状态。
    for mode in ("updates", "values"):
        print("流式模式：", mode)
        for chunk in graph.stream(
            make_initial_state(2), RUN_CONFIG, stream_mode=mode, version="v1"
        ):
            print(chunk)


if __name__ == "__main__":
    main()
