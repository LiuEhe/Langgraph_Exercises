"""验证路由、检索次数上限与状态流；使用真实离线图，无模型请求。"""

from pathlib import Path
import runpy
import unittest


DEMO_PATH = Path(__file__).resolve().parents[1] / "examples/03_routing_loops/demo.py"
RUN_CONFIG = {"recursion_limit": 20}


class RoutingLoopTests(unittest.TestCase):
    def load_demo(self):
        self.assertTrue(DEMO_PATH.is_file(), "第 03 课示例尚未创建")
        return runpy.run_path(str(DEMO_PATH))

    def test_success_stops_on_first_second_or_third_attempt(self):
        demo = self.load_demo()
        for target in (1, 2, 3):
            with self.subTest(find_on_attempt=target):
                result = demo["graph"].invoke(demo["make_initial_state"](target), RUN_CONFIG)
                self.assertEqual(result["attempts"], target)
                self.assertTrue(result["found"])
                self.assertEqual(len(result["attempts_log"]), target)
                self.assertTrue(result["answer"].startswith("模拟回答："))
                self.assertEqual(result["question"], "什么是条件路由？")

    def test_no_hit_stops_at_three_even_if_hit_is_scheduled_for_four(self):
        demo = self.load_demo()
        for target in (0, 4):
            with self.subTest(find_on_attempt=target):
                result = demo["graph"].invoke(demo["make_initial_state"](target), RUN_CONFIG)
                self.assertEqual(result["attempts"], 3)
                self.assertFalse(result["found"])
                self.assertEqual(len(result["attempts_log"]), 3)
                self.assertTrue(result["answer"].startswith("停止："))

    def test_router_prioritizes_success_then_checks_the_limit(self):
        demo = self.load_demo()
        state = demo["make_initial_state"](0)
        for attempts, found, expected in ((1, False, "retry"), (3, False, "stop"), (4, False, "stop"), (3, True, "answer")):
            with self.subTest(attempts=attempts, found=found):
                state.update(attempts=attempts, found=found)
                self.assertEqual(demo["route_after_retrieve"](state), expected)

    def test_retrieve_returns_one_attempt_and_one_log_entry(self):
        demo = self.load_demo()
        state = demo["make_initial_state"](2)
        state.update(attempts=1, attempts_log=["第1次：未找到"])
        update = demo["retrieve"](state)
        self.assertEqual(update["attempts"], 2)
        self.assertTrue(update["found"])
        self.assertEqual(update["attempts_log"], ["第2次：找到"])
        self.assertEqual(state["attempts"], 1)
        self.assertEqual(state["attempts_log"], ["第1次：未找到"])

    def test_updates_stream_exposes_each_node_delta(self):
        demo = self.load_demo()
        chunks = list(demo["graph"].stream(demo["make_initial_state"](2), RUN_CONFIG, stream_mode="updates", version="v1"))
        self.assertEqual([next(iter(chunk)) for chunk in chunks], ["retrieve", "retrieve", "answer"])
        self.assertEqual([chunk["retrieve"]["attempts"] for chunk in chunks[:2]], [1, 2])
        for chunk in chunks[:2]:
            self.assertEqual(len(chunk["retrieve"]["attempts_log"]), 1)
            self.assertNotIn("question", chunk["retrieve"])

    def test_values_stream_includes_initial_and_accumulated_state(self):
        demo = self.load_demo()
        snapshots = list(demo["graph"].stream(demo["make_initial_state"](2), RUN_CONFIG, stream_mode="values", version="v1"))
        self.assertEqual(len(snapshots), 4)
        self.assertEqual(snapshots[0]["attempts"], 0)
        self.assertEqual(snapshots[-1]["attempts"], 2)
        self.assertEqual(snapshots[-1]["attempts_log"], ["第1次：未找到", "第2次：找到"])
        self.assertTrue(snapshots[-1]["answer"].startswith("模拟回答："))
        self.assertTrue(all(state["question"] == "什么是条件路由？" for state in snapshots))


if __name__ == "__main__":
    unittest.main()
