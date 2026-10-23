"""第 01 课：用普通 Python 节点观察状态的部分更新，不调用模型。"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    question: str
    answer: str


def answer_question(state: State) -> dict[str, str]:
    print("节点读到：", state)
    # 只声明本次变化，未返回的 question 由图保留。
    update = {"answer": f"收到问题：{state['question']}"}
    print("节点返回：", update)
    return update


builder = StateGraph(State)
builder.add_node("answer", answer_question)
builder.add_edge(START, "answer")
builder.add_edge("answer", END)
graph = builder.compile()


def main() -> None:
    initial_state: State = {"question": "什么是 State？", "answer": ""}
    print("初始状态：", initial_state)
    result = graph.invoke(initial_state)
    print("最终状态：", result)


if __name__ == "__main__":
    main()
