"""第 02 课：比较同一张串行图中的列表覆盖与累积，不调用模型。"""

from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    question: str
    steps: list[str]
    steps_log: Annotated[list[str], add]


def retrieve(state: State) -> dict[str, list[str]]:
    print("retrieve 读到：", state)
    # 固定标签模拟步骤；节点只提供本次增量，由图按字段规则合并。
    update = {"steps": ["检索"], "steps_log": ["检索"]}
    print("retrieve 返回：", update)
    return update


def answer(state: State) -> dict[str, list[str]]:
    print("answer 读到：", state)
    update = {"steps": ["回答"], "steps_log": ["回答"]}
    print("answer 返回：", update)
    return update


builder = StateGraph(State)
builder.add_node("retrieve", retrieve)
builder.add_node("answer", answer)
builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "answer")
builder.add_edge("answer", END)
graph = builder.compile()


def main() -> None:
    initial_state: State = {
        "question": "什么是 reducer？",
        "steps": [],
        "steps_log": [],
    }
    print("初始状态：", initial_state)
    result = graph.invoke(initial_state)
    print("最终状态：", result)


if __name__ == "__main__":
    main()
