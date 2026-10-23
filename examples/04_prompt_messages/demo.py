"""第 04 课主示例：格式化消息模板，不初始化或调用模型。"""

from langchain.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一名{subject}导师。请用简体中文回答。"),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
])


def main() -> None:
    # 这两条是手工准备的示例历史，AIMessage 不是本次模型生成的回复。
    history = [
        HumanMessage(content="什么是 State？"),
        AIMessage(content="示例历史回答：State 保存工作流共享的数据。"),
    ]
    print("必需变量：", prompt.input_variables)
    result = prompt.invoke({
        "subject": "LangGraph",
        "history": history,
        "question": "那 Node 怎样更新它？",
    })
    print("模板返回对象：", type(result).__name__)
    print("以下是格式化消息，不是本次生成的模型回答：")
    for message in result.to_messages():
        print(type(message).__name__, message.type, message.content)


if __name__ == "__main__":
    main()
