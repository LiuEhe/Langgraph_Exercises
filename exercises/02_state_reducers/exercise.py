"""第 02 课练习：调整 steps 的合并规则，保留完整步骤历史。

先描述应修改哪里以及原因，再修改状态声明。
未修改时脚本可以运行，但只保留最后一条记录，不符合练习目标。
运行：uv run python exercises/02_state_reducers/exercise.py
"""

from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    question: str
    steps: Annotated[list[str], add]
    # steps_log: Annotated[list[str], add]

def retrieve(state: State) -> dict[str, list[str]]:
    return {"steps": ["检索"]}

def answer(state: State) -> dict[str, list[str]]:
    return {"steps": ["回答"]}

builder = StateGraph(State)
builder.add_node("retrieve", retrieve)
builder.add_node("answer", answer)
builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "answer")
builder.add_edge("answer", END)

graph = builder.compile()

def main() -> None:
    initial_state: State = {"question": "State", "steps": ["开始"]}
    print("初始状态：", initial_state)
    result = graph.invoke(initial_state)
    print("最终状态：", result)

if __name__ == "__main__":
    main()