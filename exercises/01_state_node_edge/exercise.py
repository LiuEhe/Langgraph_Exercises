"""第 01 课练习：只补全 measure_question，保留其他字段。

先描述输入、输出与字段保留规则，再替换 NotImplementedError。
运行：uv run python exercises/01_state_node_edge/exercise.py
"""

from typing import TypedDict
from langgraph.graph import END, START, StateGraph

class State(TypedDict):
    question: str
    answer: str
    question_length: int 

def answer_question(state: State) -> dict[str, str]:
    return {"answer": f"收到问题：{state['question']}"}

def measure_question(state: State) -> dict[str, int]:
    return{"question_length": len(state["question"])}

builder = StateGraph(State)
builder.add_node("answer", answer_question)
builder.add_node("measure", measure_question)
builder.add_edge(START, "answer")
builder.add_edge("answer", "measure")
builder.add_edge("measure", END)
graph = builder.compile()

def main() -> None:
    initial_state: State = {
        "question": "State",
        "answer": "",
        "question_length": 0,
    }
    print("初始状态：", initial_state)
    result = graph.invoke(initial_state)
    print("最终状态：", result)

if __name__ == "__main__":
    main()