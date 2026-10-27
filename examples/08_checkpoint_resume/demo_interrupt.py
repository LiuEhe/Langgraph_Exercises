"""第 08 课补充：审核时暂停，再用外部决定恢复。

运行：uv run python examples/08_checkpoint_resume/demo_interrupt.py
拒绝：同一命令追加 --reject。布尔决定由程序模拟人员输入，无审批界面。
顺序：固定草稿 → interrupt 暂停并返回 → 查看快照 → Command 恢复 → 批准/拒绝。
全部离线；发布只更新状态字段，不读取 .env、不请求模型、不发送消息。
"""

import argparse
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ReviewState(TypedDict):
    question: str
    draft: str
    approved: bool | None  # None 表示尚无审核决定，不能与拒绝混淆。
    status: str
    published: str         # 仅表示模拟发布的文本，无外部副作用。


def build_graph(events: list[str]):
    """返回带内存保存器的审核图，events 仅用于观察节点重跑。"""
    def prepare(state: ReviewState) -> dict:
        events.append("prepare")
        return {"draft": f"模拟草稿：关于“{state['question']}”，请人工复核后使用。",
                "status": "awaiting_review"}

    def review(state: ReviewState) -> dict:
        # 这条观察记录位于中断之前，恢复时会再执行一次；不要在这里真实发布。
        events.append("review:start")
        approved = interrupt({"draft": state["draft"], "question": "是否批准这份草稿？"})
        # 第一次执行到 interrupt 时图暂停；恢复后此调用才得到外部传入的值。
        if not isinstance(approved, bool):
            raise ValueError("审核决定必须是 bool。")
        return {"approved": approved, "status": "approved" if approved else "rejected"}

    def route_after_review(state: ReviewState) -> str:
        """读取已返回的审核决定，输出分支标签，不修改状态。"""
        return "publish" if state["approved"] else "reject"

    def publish(state: ReviewState) -> dict:
        events.append("publish")
        return {"published": state["draft"], "status": "completed"}

    def reject(state: ReviewState) -> dict:
        events.append("reject")
        return {"published": "", "status": "rejected"}

    builder = StateGraph(ReviewState)
    builder.add_node("prepare", prepare)
    builder.add_node("review", review)
    builder.add_node("publish", publish)
    builder.add_node("reject", reject)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "review")
    builder.add_conditional_edges("review", route_after_review, {"publish": "publish", "reject": "reject"})
    builder.add_edge("publish", END)
    builder.add_edge("reject", END)
    return builder.compile(checkpointer=InMemorySaver())


def resume_review(graph, config: dict, approved: bool) -> dict:
    """读取原线程待执行任务，使用同一配置恢复；不新建一次审核。"""
    if not isinstance(approved, bool):
        raise TypeError("审核决定必须是 bool，不能传字符串或数字。")
    snapshot = graph.get_state(config)
    if "review" not in snapshot.next:
        raise ValueError("该线程没有待恢复的审核，检查线程 ID 或是否已完成。")
    return graph.invoke(Command(resume=approved), config)


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--reject", action="store_true")
    args = arguments.parse_args()
    events = []
    graph = build_graph(events)
    config = {"configurable": {"thread_id": "review-demo"}}
    pending = graph.invoke({
        "question": "什么是检查点？", "draft": "", "approved": None,
        "status": "new", "published": "",
    }, config)
    # __interrupt__ 是 invoke 返回给调用者的暂停信息，不是最终审核答案。
    notice = pending["__interrupt__"][0]
    print("中断对象：", type(notice).__name__)
    print("中断 payload：", notice.value)
    snapshot = graph.get_state(config)
    print("暂停状态：", snapshot.values["status"], "待执行：", snapshot.next)
    print("暂停时 published：", repr(snapshot.values["published"]))
    print("暂停时事件：", events)

    approved = not args.reject
    print("模拟外部审核输入：", approved)
    result = resume_review(graph, config, approved)
    print("恢复后状态：", result["status"], "approved：", result["approved"])
    print("恢复后 published：", repr(result["published"]))
    print("恢复后 next：", graph.get_state(config).next)
    print("恢复后事件：", events)
    print("review 入口次数：", events.count("review:start"))
    print("prepare 次数：", events.count("prepare"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
