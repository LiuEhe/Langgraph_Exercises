"""第 04 课练习：补全 build_prompt，组织规则、历史与当前问题。

先说明历史占位符和单条用户模板的区别，再替换占位异常。
运行：uv run python exercises/04_prompt_messages/exercise.py
"""

from langchain.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def build_prompt() -> ChatPromptTemplate:
    """返回按系统规则、历史消息、当前问题排列的模板。"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一名{subject}导师。请用简体中文回答。"),
        MessagesPlaceholder("history"),
        ("human", "请用{style}解释：{question}"),
    ])
    return prompt


def main() -> None:
    prompt = build_prompt()
    # 手工示例历史，不是真实模型生成记录。
    history = [
        HumanMessage(content="什么是 Node？"),
        AIMessage(content="示例历史回答：Node 是执行步骤。"),
    ]
    result = prompt.invoke({
        "subject": "LangGraph",
        "history": history,
        "style": "一个生活类比",
        "question": "什么是条件边？",
    })
    print("模板返回对象：", type(result).__name__)
    for message in result.to_messages():
        print(type(message).__name__, message.type, message.content)


if __name__ == "__main__":
    main()
