"""Agent 主循环、工具层、护栏的核心行为测试。"""

from __future__ import annotations

import unittest

from learning_agents.agent import Agent
from learning_agents.guardrails import ApprovalGate, Budget, validate_json
from learning_agents.llm import LLMResponse, RuleBasedLLM, ScriptedLLM, ToolCall, Usage
from learning_agents.tools import ToolError, ToolRegistry, parallel_execute, tool


@tool
def add(a: int, b: int) -> int:
    """两数相加  a: 被加数  b: 加数"""
    return a + b


@tool
def boom(text: str) -> str:
    """总是抛错，用于验证"错误即观察"  text: 任意文本"""
    raise RuntimeError("故意失败")


@tool(side_effect=True, idempotent=False)
def delete_row(row_id: int) -> str:
    """删除一行（有副作用）  row_id: 行号"""
    return f"deleted {row_id}"


class TestTools(unittest.TestCase):
    def test_schema_from_signature(self) -> None:
        registry = ToolRegistry().register_all([add])
        schema = registry.schemas()[0]["function"]
        self.assertEqual(schema["name"], "add")
        self.assertEqual(schema["parameters"]["properties"]["a"]["type"], "integer")
        self.assertEqual(sorted(schema["parameters"]["required"]), ["a", "b"])

    def test_validation_rejects_bad_args(self) -> None:
        registry = ToolRegistry().register_all([add])
        missing = registry.execute(ToolCall("1", "add", {"a": 1}))
        self.assertFalse(missing.ok)
        self.assertIn("缺少必填参数", missing.error)

        extra = registry.execute(ToolCall("2", "add", {"a": 1, "b": 2, "c": 3}))
        self.assertFalse(extra.ok)
        self.assertIn("未声明的参数", extra.error)

        wrong = registry.execute(ToolCall("3", "add", {"a": "1", "b": 2}))
        self.assertFalse(wrong.ok)
        self.assertIn("应为 integer", wrong.error)

    def test_error_becomes_observation(self) -> None:
        registry = ToolRegistry().register_all([boom])
        result = registry.execute(ToolCall("1", "boom", {"text": "x"}))
        self.assertFalse(result.ok)
        self.assertIn("RuntimeError", result.error)
        self.assertEqual(result.to_message()["role"], "tool")

    def test_parallel_preserves_order(self) -> None:
        registry = ToolRegistry().register_all([add, boom])
        calls = [ToolCall("1", "add", {"a": 1, "b": 2}),
                 ToolCall("2", "boom", {"text": "x"}),
                 ToolCall("3", "add", {"a": 5, "b": 6})]
        results = parallel_execute(registry, calls)
        self.assertEqual([r.call_id for r in results], ["1", "2", "3"])
        self.assertEqual([r.ok for r in results], [True, False, True])


class TestAgent(unittest.TestCase):
    def test_two_step_react(self) -> None:
        registry = ToolRegistry().register_all([add])
        script = [
            LLMResponse(tool_calls=[ToolCall("c1", "add", {"a": 1, "b": 2})], usage=Usage(10, 2)),
            LLMResponse(text="结果是 3", usage=Usage(20, 3)),
        ]
        result = Agent(llm=ScriptedLLM(script), tools=registry, max_steps=4).run("1+2?")
        self.assertEqual(result.stopped_reason, "final")
        self.assertEqual(result.answer, "结果是 3")
        self.assertEqual(result.steps, 2)
        self.assertEqual(result.usage.total, 35)
        self.assertTrue(any(ev.kind == "tool.call" for ev in result.trace.events))

    def test_max_steps_stops(self) -> None:
        registry = ToolRegistry().register_all([add])
        script = [LLMResponse(tool_calls=[ToolCall(f"c{i}", "add", {"a": i, "b": 1})])
                  for i in range(5)]
        result = Agent(llm=ScriptedLLM(script), tools=registry, max_steps=3).run("loop")
        self.assertEqual(result.stopped_reason, "max_steps")
        self.assertEqual(result.steps, 3)

    def test_repeat_detection(self) -> None:
        registry = ToolRegistry().register_all([add])
        same = [LLMResponse(tool_calls=[ToolCall(f"c{i}", "add", {"a": 1, "b": 1})])
                for i in range(8)]
        result = Agent(llm=ScriptedLLM(same), tools=registry, max_steps=8,
                       repeat_limit=2).run("repeat")
        self.assertEqual(result.stopped_reason, "loop_detected")

    def test_budget_stops(self) -> None:
        registry = ToolRegistry().register_all([add])
        script = [LLMResponse(tool_calls=[ToolCall("c", "add", {"a": 1, "b": 1})],
                              usage=Usage(400, 100)),
                  LLMResponse(text="done", usage=Usage(400, 100))]
        result = Agent(llm=ScriptedLLM(script), tools=registry, max_steps=4,
                       budget=Budget(max_tokens=300)).run("budget")
        self.assertEqual(result.stopped_reason, "budget_tokens")

    def test_unknown_tool_is_observation(self) -> None:
        script = [LLMResponse(tool_calls=[ToolCall("c", "nope", {})]),
                  LLMResponse(text="我换一种方式回答")]
        result = Agent(llm=ScriptedLLM(script), tools=ToolRegistry(), max_steps=3).run("x")
        error_msg = [m for m in result.messages if m.get("role") == "tool"][0]["content"]
        self.assertIn("未知工具", error_msg)
        self.assertEqual(result.stopped_reason, "final")


class TestGuardrails(unittest.TestCase):
    def test_approval_denied_by_default(self) -> None:
        registry = ToolRegistry().register_all([delete_row])
        registry.hook = ApprovalGate().hook
        result = registry.execute(ToolCall("1", "delete_row", {"row_id": 7}))
        self.assertFalse(result.ok)
        self.assertIn("审批未通过", result.error)

    def test_approval_allows_when_approver_agrees(self) -> None:
        registry = ToolRegistry().register_all([delete_row])
        registry.hook = ApprovalGate(approver=lambda req: True).hook
        result = registry.execute(ToolCall("1", "delete_row", {"row_id": 7}))
        self.assertTrue(result.ok)

    def test_budget_limits(self) -> None:
        budget = Budget(max_tokens=100)
        self.assertTrue(budget.exceeded(Usage(60, 40)))
        self.assertFalse(budget.exceeded(Usage(10, 10)))

    def test_validate_json(self) -> None:
        schema = {"required": ["intent"], "properties": {
            "intent": {"type": "string", "enum": ["refund", "invoice"]}}}
        self.assertEqual(validate_json('{"intent":"refund"}', schema)["intent"], "refund")
        with self.assertRaises(ValueError):
            validate_json('{"intent":"other"}', schema)
        with self.assertRaises(ValueError):
            validate_json("not json", schema)


class TestRuleBasedLLM(unittest.TestCase):
    def test_calls_matching_tool(self) -> None:
        registry = ToolRegistry().register_all([add])
        result = Agent(llm=RuleBasedLLM(), tools=registry, max_steps=3).run("请把 1 和 2 相加")
        self.assertTrue(any(ev.kind == "tool.call" for ev in result.trace.events))
        self.assertEqual(result.stopped_reason, "final")


if __name__ == "__main__":
    unittest.main()
