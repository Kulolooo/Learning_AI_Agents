"""规划、反思、多智能体与评估的测试。"""

from __future__ import annotations

import unittest

from learning_agents.evaluation import (EvalCase, TraceEvaluator, cost, pass_at_k,
                                        rubric_score)
from learning_agents.multiagent import (AgentBase, Blackboard, BlackboardSystem, Debate,
                                        Pipeline, Supervisor, consensus)
from learning_agents.planning import (Plan, PlanAndExecute, PlanStep, Planner, Router,
                                      TaskGraph)
from learning_agents.reflection import CodeHealer, HeuristicCritic, ReflectionLoop, self_consistency
from learning_agents.trace import Tracer
from learning_agents.agent import AgentResult
from learning_agents.llm import Usage


class TestPlanning(unittest.TestCase):
    def test_task_graph_layers_and_cycle(self) -> None:
        graph = TaskGraph()
        graph.add("a", lambda: 1)
        graph.add("b", lambda a: a + 1, deps=["a"])
        graph.add("c", lambda a: a * 2, deps=["a"])
        graph.add("d", lambda b, c: b + c, deps=["b", "c"])
        self.assertEqual(graph.layers(), [["a"], ["b", "c"], ["d"]])
        self.assertEqual(graph.run()["d"], 4)

        cyclic = TaskGraph()
        cyclic.add("x", lambda y: y, deps=["y"])
        cyclic.add("y", lambda x: x, deps=["x"])
        with self.assertRaises(ValueError):
            cyclic.layers()

    def test_plan_and_execute_replans_once(self) -> None:
        plan = Plan([PlanStep("s1", "准备"), PlanStep("s2", "查询"), PlanStep("s3", "汇总")])
        calls = {"s2": 0}

        def executor(step: PlanStep) -> str:
            if step.id == "s2":
                calls["s2"] += 1
                if calls["s2"] == 1:
                    raise TimeoutError("超时")
            return f"ok:{step.id}"

        def replanner(old: Plan, failed: PlanStep, error: str) -> Plan:
            failed.status = "pending"
            failed.goal = "查询（降级）"
            return old

        runner = PlanAndExecute(executor, replanner)
        done = runner.run(plan)
        self.assertTrue(all(s.status == "done" for s in done.steps))
        self.assertEqual(calls["s2"], 2)
        self.assertEqual([row["status"] for row in runner.history],
                         ["done", "failed", "done", "done"])

    def test_router_fallback(self) -> None:
        router = Router({"billing": ["退款"], "tech": ["超时"]})
        self.assertEqual(router.decide("我要退款"), "billing")
        self.assertEqual(router.decide("你好"), "general")

    def test_template_planner_assigns_tools(self) -> None:
        plan = Planner().from_template(["甲", "乙"], tools=["t1"])
        self.assertEqual(plan.steps[1].tool, "")
        self.assertEqual(plan.steps[0].tool, "t1")


class TestReflection(unittest.TestCase):
    def test_reflection_improves_and_stops(self) -> None:
        critic = HeuristicCritic({"min_chars": 50, "require_citation": True,
                                  "required_terms": ["上限"]})

        def revise(draft: str, critique) -> str:
            if "[" not in draft:
                draft += " 参考：[1] 笔记。"
            if "上限" not in draft:
                draft += (" 必须设置步数上限与时间上限，避免在失败路径上无限循环；"
                          "同时把每次重规划的原因写进轨迹，方便事后定位问题。")
            return draft

        loop = ReflectionLoop(lambda task: "智能体需要规划。", revise, critic, max_rounds=3)
        out = loop.run("怎么避免失控")
        self.assertTrue(out["passed"])
        self.assertLessEqual(out["rounds"], 3)
        self.assertIn("[1]", out["final"])

    def test_code_healer_fixes_syntax_error(self) -> None:
        def fixer(code: str, error: str) -> str:
            return "print('fixed')\n"

        healer = CodeHealer(fixer, max_rounds=2)
        result = healer.run("print('broken'\n")
        self.assertTrue(result["ok"])
        self.assertEqual(result["rounds"], 1)
        self.assertIn("fixed", result["output"])

    def test_self_consistency_vote(self) -> None:
        out = self_consistency(["A", "A", "B"])
        self.assertEqual(out["answer"], "A")
        self.assertAlmostEqual(out["agreement"], 0.667, places=3)


class TestMultiAgent(unittest.TestCase):
    def test_pipeline_reports_failed_stage(self) -> None:
        pipe = Pipeline([("ok", lambda t: t + "!"), ("bad", lambda t: 1 / 0)])
        result = pipe.run("x")
        self.assertFalse(result["ok"])
        self.assertEqual(result["failed_stage"], "bad")

    def test_supervisor_assigns_and_merges(self) -> None:
        workers = [AgentBase("甲", lambda task, ctx: f"甲:{task}"),
                   AgentBase("乙", lambda task, ctx: f"乙:{task}")]
        sup = Supervisor(workers, plan=lambda t: ["一", "二"],
                         assign=lambda sub: {"一": "甲", "二": "乙"}[sub],
                         merge=lambda task, parts: "|".join(p[1] for p in parts))
        out = sup.run("任务")
        self.assertEqual(out["output"], "甲:一|乙:二")
        self.assertEqual(len(out["transcript"]), 4)

    def test_supervisor_rejects_empty_workers(self) -> None:
        with self.assertRaises(ValueError):
            Supervisor([], plan=lambda t: ["子任务"])

    def test_debate_produces_decision(self) -> None:
        debate = Debate(lambda t, c: "正方", lambda t, p: "反方",
                        lambda t, texts: f"裁判看过 {len(texts)} 条发言", rounds=2)
        out = debate.run("议题")
        self.assertEqual(out["rounds"], 2)
        self.assertIn("裁判", out["decision"])

    def test_blackboard_versions_and_rounds(self) -> None:
        board = Blackboard()
        board.write("k", 1, "a")
        board.write("k", 2, "b")
        self.assertEqual(board.history("k")[1]["version"], 2)

        system = BlackboardSystem([AgentBase("甲", lambda t, c: "笔记")], board, max_rounds=3)
        out = system.run("任务")
        self.assertEqual(out["rounds"], 2)  # 第二轮写入与第一轮相同 -> 收敛
        self.assertEqual(consensus(["x", "x", "y"])[1], 0.667)


class TestEvaluation(unittest.TestCase):
    def _result(self, answer: str, tools: list[str], tokens: int = 100) -> AgentResult:
        tracer = Tracer()
        for name in tools:
            tracer.event("tool.call", name=name, ok=True)
        return AgentResult(answer=answer, steps=2, usage=Usage(tokens // 2, tokens // 2),
                           stopped_reason="final", trace=tracer)

    def test_evaluator_pass_and_fail(self) -> None:
        cases = [EvalCase("c1", "任务", expected_terms=["答案"], required_tools=["calc"]),
                 EvalCase("c2", "任务", expected_terms=["缺失"], required_tools=["calc"])]
        results = {"c1": self._result("这是答案", ["calc"]),
                   "c2": self._result("这是答案", ["calc"])}
        report = TraceEvaluator(cases).run_suite(results)
        self.assertEqual(report["cases"], 2)
        self.assertEqual(report["rows"][0]["passed"], True)
        self.assertEqual(report["rows"][1]["passed"], False)

    def test_pass_at_k_bounds(self) -> None:
        self.assertEqual(pass_at_k(0, 10, 1), 0.0)
        self.assertEqual(pass_at_k(10, 10, 1), 1.0)
        self.assertGreater(pass_at_k(5, 10, 3), pass_at_k(5, 10, 1))

    def test_rubric_and_cost(self) -> None:
        out = rubric_score("包含 引用 与 覆盖率 的答案", {"引用 覆盖率": 1.0, "缺少项": 1.0})
        self.assertEqual(out["score"], 0.5)
        self.assertGreater(cost(1_000_000), 0)


if __name__ == "__main__":
    unittest.main()
