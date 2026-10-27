"""第 08 课练习：恢复正确线程中的审核，分别验证批准与拒绝。

运行：uv run python exercises/08_checkpoint_resume/exercise.py
顺序：当前文件建图 → 固定草稿 → 暂停 → 你的恢复函数 → 检查分支与最终状态。
全部离线，审核输入和草稿均为手工数据，发布只更新状态；不加载其他示例。
"""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ReviewState(TypedDict):
    question: str
    draft: str
    approved: bool | None
    status: str
    published: str


def build_graph(events: list[str]):
    """给定观察事件列表，返回可暂停的编译图；建图不会执行审核。"""
    def prepare(state: ReviewState) -> dict:
        events.append("prepare")
        return {"draft": f"练习模拟草稿：{state['question']}", "status": "awaiting_review"}

    def review(state: ReviewState) -> dict:
        events.append("review:start")  # 预测此处在一次暂停、一次恢复中执行几次。
        approved = interrupt({"draft": state["draft"], "question": "是否批准？"})
        if not isinstance(approved, bool):
            raise ValueError("审核决定必须是 bool。")
        return {"approved": approved, "status": "approved" if approved else "rejected"}

    def route_after_review(state: ReviewState) -> str:
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
    """用原线程和恢复命令传入审核决定，返回恢复后的状态。

    任务：检查布尔决定及待执行的 review 节点；拒绝错误线程和已完成线程。
    不重新提交 question/draft 初始输入，不返回写死的结果，不新建保存器。
    """
    raise NotImplementedError("请补全 resume_review，检查线程并用 Command 恢复审核。")


def main() -> int:
    try:
        # 批准和拒绝使用各自的新图与线程，互不影响；均不接触外部系统。
        for thread_id, approved in [("practice-approve", True), ("practice-reject", False)]:
            events = []
            graph = build_graph(events)
            config = {"configurable": {"thread_id": thread_id}}
            pending = graph.invoke({
                "question": "请审核本地示例说明。", "draft": "", "approved": None,
                "status": "new", "published": "",
            }, config)
            print("已暂停，待执行：", graph.get_state(config).next)
            print("手工审核输入：", approved)
            result = resume_review(graph, config, approved)
            expected_status = "completed" if approved else "rejected"
            expected_published = pending["draft"] if approved else ""
            if result["status"] != expected_status or result["approved"] is not approved:
                raise ValueError("恢复后的决定或状态不符合预期。")
            if result["published"] != expected_published or graph.get_state(config).next:
                raise ValueError("发布字段不正确或图仍有待执行任务。")
            print("恢复后：", result["status"], "事件：", events)
        print("批准和拒绝分支检查通过；还需确认错误线程、重复恢复及非法决定被拒绝。")
        return 0
    except NotImplementedError as error:
        print("练习尚未完成：", error)
        return 1
    except Exception as error:
        # 本课仅有固定本地数据，没有服务错误或私有模型配置。
        print("本地检查失败：", type(error).__name__, str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
