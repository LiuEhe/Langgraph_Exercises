"""第 04 课补充：手工消息的新增和同 ID 更正，不调用模型。"""

from operator import add

from langchain.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.message import add_messages


def draft_reply(state: MessagesState) -> dict[str, list[AIMessage]]:
    # 固定文本模拟回复，显式 ID 让后续节点能够更正同一条消息。
    return {"messages": [AIMessage(content="模拟草稿：State 是共享数据。", id="reply-1")]}


def revise_reply(state: MessagesState) -> dict[str, list[AIMessage]]:
    return {"messages": [AIMessage(
        content="模拟更正：State 保存工作流共享的数据，节点可以只返回部分更新。",
        id="reply-1",
    )]}


builder = StateGraph(MessagesState)
builder.add_node("draft_reply", draft_reply)
builder.add_node("revise_reply", revise_reply)
builder.add_edge(START, "draft_reply")
builder.add_edge("draft_reply", "revise_reply")
builder.add_edge("revise_reply", END)
graph = builder.compile()


def main() -> None:
    original = AIMessage(content="模拟草稿", id="reply-1")
    revision = AIMessage(content="模拟更正", id="reply-1")
    plain = add([original], [revision])
    merged = add_messages([original], [revision])
    print("普通拼接：", [(message.id, message.content) for message in plain])
    print("按 ID 合并：", [(message.id, message.content) for message in merged])

    initial_state = {
        "messages": [HumanMessage(content="什么是 State？", id="question-1")],
    }
    print("下面是模拟消息图的完整状态快照：")
    for state in graph.stream(initial_state, stream_mode="values", version="v1"):
        print([(message.id, message.type, message.content) for message in state["messages"]])


if __name__ == "__main__":
    main()
