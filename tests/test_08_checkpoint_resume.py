"""离线验证线程保存、快照读取及中断恢复，无模型或外部发布。"""

from pathlib import Path
import runpy
import unittest

from langgraph.checkpoint.memory import InMemorySaver


ROOT = Path(__file__).resolve().parents[1]


class CheckpointResumeTests(unittest.TestCase):
    def load(self, filename="demo.py"):
        path = ROOT / "examples/08_checkpoint_resume" / filename
        self.assertTrue(path.is_file(), "第 08 课示例尚未创建")
        return runpy.run_path(str(path))

    def pending_review(self):
        demo = self.load("demo_interrupt.py")
        events = []
        graph = demo["build_graph"](events)
        config = {"configurable": {"thread_id": "review-test"}}
        pending = graph.invoke({
            "question": "什么是检查点？", "draft": "", "approved": None,
            "status": "new", "published": "",
        }, config)
        return demo, graph, config, events, pending

    def test_same_thread_accumulates_and_other_thread_starts_separately(self):
        graph = self.load()["build_graph"]()
        config_a = {"configurable": {"thread_id": "a"}}
        config_b = {"configurable": {"thread_id": "b"}}
        self.assertEqual(graph.invoke({"increment": 2, "total": 0}, config_a)["total"], 2)
        self.assertEqual(graph.invoke({"increment": 3}, config_a)["total"], 5)
        self.assertEqual(graph.invoke({"increment": 3}, config_b)["total"], 3)
        self.assertEqual(graph.get_state(config_a).values["total"], 5)

    def test_input_can_overwrite_previously_saved_total(self):
        graph = self.load()["build_graph"]()
        config = {"configurable": {"thread_id": "overwrite"}}
        graph.invoke({"increment": 2, "total": 0}, config)
        result = graph.invoke({"increment": 3, "total": 0}, config)
        self.assertEqual(result["total"], 3)

    def test_history_is_newest_first_and_reading_does_not_execute_nodes(self):
        graph = self.load()["build_graph"]()
        config = {"configurable": {"thread_id": "history"}}
        graph.invoke({"increment": 2, "total": 0}, config)
        graph.invoke({"increment": 3}, config)
        snapshot = graph.get_state(config)
        history = list(graph.get_state_history(config))
        self.assertEqual(type(snapshot).__name__, "StateSnapshot")
        self.assertEqual(snapshot.next, ())
        self.assertEqual(history[0].values, snapshot.values)
        self.assertTrue(any(item.values.get("total") == 2 for item in history))
        self.assertEqual(graph.get_state(config).values, {"increment": 3, "total": 5})

    def test_saved_state_belongs_to_saver_and_can_be_read_by_recompiled_graph(self):
        demo = self.load()
        saver = InMemorySaver()
        config = {"configurable": {"thread_id": "same-name"}}
        demo["build_graph"](saver).invoke({"increment": 2}, config)
        self.assertEqual(demo["build_graph"](saver).get_state(config).values["total"], 2)
        self.assertEqual(demo["build_graph"](InMemorySaver()).get_state(config).values, {})

    def test_approval_pauses_then_restarts_review_node_before_publishing(self):
        demo, graph, config, events, pending = self.pending_review()
        self.assertEqual(graph.get_state(config).next, ("review",))
        self.assertEqual(pending["published"], "")
        self.assertIsNone(pending["approved"])
        self.assertEqual(pending["__interrupt__"][0].value["draft"], pending["draft"])
        self.assertEqual(events, ["prepare", "review:start"])
        result = demo["resume_review"](graph, config, True)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["published"], result["draft"])
        self.assertEqual(events, ["prepare", "review:start", "review:start", "publish"])
        self.assertEqual(graph.get_state(config).next, ())

    def test_rejection_finishes_without_publishing(self):
        demo, graph, config, events, _ = self.pending_review()
        result = demo["resume_review"](graph, config, False)
        self.assertEqual((result["approved"], result["status"], result["published"]), (False, "rejected", ""))
        self.assertNotIn("publish", events)
        self.assertEqual(events.count("review:start"), 2)
        self.assertEqual(graph.get_state(config).next, ())

    def test_nonboolean_decision_is_rejected_while_thread_remains_pending(self):
        demo, graph, config, events, _ = self.pending_review()
        with self.assertRaises(TypeError):
            demo["resume_review"](graph, config, "false")
        self.assertEqual(graph.get_state(config).next, ("review",))
        self.assertEqual(events, ["prepare", "review:start"])

    def test_wrong_thread_and_already_finished_thread_cannot_be_resumed(self):
        demo, graph, config, events, _ = self.pending_review()
        with self.assertRaises(ValueError):
            demo["resume_review"](graph, {"configurable": {"thread_id": "other"}}, True)
        self.assertEqual(graph.get_state(config).next, ("review",))
        result = demo["resume_review"](graph, config, True)
        with self.assertRaises(ValueError):
            demo["resume_review"](graph, config, False)
        self.assertEqual(graph.get_state(config).values["published"], result["draft"])
        self.assertEqual(events.count("publish"), 1)

    def test_checkpointer_requires_thread_configuration(self):
        graph = self.load()["build_graph"]()
        with self.assertRaises(ValueError):
            graph.invoke({"increment": 2})


if __name__ == "__main__":
    unittest.main()
