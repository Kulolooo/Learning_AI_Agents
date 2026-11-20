"""Agent 主循环：一个 while 循环 + 一份上下文 + 一个工具表。

```
思考 -> 选工具 -> 执行 -> 观察 -> 再思考 ... 直到给出最终答复
```

这里刻意不用任何框架：循环、终止条件、预算、去重、轨迹全部可见。
理解了这 120 行，任何 Agent 框架都只是它的工程化包装。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Sequence

from .guardrails import Budget
from .llm import LLM, LLMResponse, Usage, messages_tokens
from .tools import ToolRegistry, parallel_execute
from .trace import Tracer


DEFAULT_SYSTEM = """你是一个可调用工具的任务型智能体。
规则：
1. 先判断是否需要外部信息或计算；需要就调用工具，不要臆造数据。
2. 一次只解决一个子问题；调用工具后用观察结果修正下一步。
3. 工具返回 ERROR 时，先解释原因，再决定换参数重试或换工具。
4. 信息足够时直接给出最终答复，不要为了"显得勤奋"而继续调用工具。
5. 回答使用简体中文，结论在前，过程在后。"""


@dataclass
class AgentResult:
    answer: str
    steps: int
    usage: Usage
    stopped_reason: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    trace: Tracer | None = None

    @property
    def ok(self) -> bool:
        return self.stopped_reason in ("final", "budget_tokens")


class Agent:
    """最小的 ReAct 式智能体。"""

    def __init__(
        self,
        llm: LLM,
        tools: ToolRegistry | None = None,
        system: str = DEFAULT_SYSTEM,
        max_steps: int = 8,
        budget: Budget | None = None,
        tracer: Tracer | None = None,
        repeat_limit: int = 3,
    ) -> None:
        self.llm = llm
        self.tools = tools or ToolRegistry()
        self.system = system
        self.max_steps = max_steps
        self.budget = budget or Budget()
        self.tracer = tracer or Tracer()
        self.repeat_limit = repeat_limit
        self.usage = Usage()

    # ------------------------------------------------------------------ 主循环
    def run(self, task: str, context: str = "") -> AgentResult:
        messages = self._seed(task, context)
        self.tracer.event("agent.start", task=task, tools=len(self.tools))

        seen_calls: dict[str, int] = {}
        stopped = "max_steps"
        answer = ""
        steps_used = 0

        for step in range(1, self.max_steps + 1):
            steps_used = step
            self.tracer.event("agent.step", step=step, tokens=messages_tokens(messages))
            if self.budget.exceeded(self.usage):
                stopped = "budget_tokens"
                self.tracer.event("agent.budget", reason="token_budget", usage=self.usage.total)
                break

            response = self.llm.complete(
                messages, tools=self.tools.schemas() or None
            )
            self.usage = self.usage + response.usage
            self.tracer.event(
                "llm.response", step=step, model=response.model,
                tokens=response.usage.total, tool_calls=[c.name for c in response.tool_calls],
                text_head=response.text[:120],
            )

            if not response.is_tool_call:
                answer = response.text
                messages.append({"role": "assistant", "content": answer})
                stopped = "final"
                break

            messages.append(_assistant_tool_message(response))
            repeat_key = _signature(response)
            seen_calls[repeat_key] = seen_calls.get(repeat_key, 0) + 1
            if seen_calls[repeat_key] > self.repeat_limit:
                stopped = "loop_detected"
                self.tracer.event("agent.loop_detected", signature=repeat_key)
                break

            with self.tracer.span("tools", names=[c.name for c in response.tool_calls]):
                results = parallel_execute(self.tools, response.tool_calls)
                for result in results:
                    self.tracer.event(
                        "tool.call", name=result.name, ok=result.ok,
                        duration_ms=result.duration_ms, truncated=result.truncated,
                        error=result.error[:160], output_head=result.output[:160],
                    )
            for result in results:
                messages.append(result.to_message())
        else:
            stopped = "max_steps"
            self.tracer.event("agent.max_steps", steps=self.max_steps)

        if stopped == "final" and self.budget.exceeded(self.usage):
            stopped = "budget_tokens"

        self.tracer.event("agent.end", stopped=stopped, steps=steps_used,
                          tokens=self.usage.total)
        return AgentResult(answer=answer, steps=steps_used,
                           usage=self.usage, stopped_reason=stopped,
                           messages=messages, trace=self.tracer)

    # ------------------------------------------------------------------ 上下文
    def _seed(self, task: str, context: str) -> list[dict[str, Any]]:
        system = self.system
        if len(self.tools):
            system += f"\n\n可用工具：\n{self.tools.describe()}"
        messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        if context:
            messages.append({"role": "system", "content": f"参考资料：\n{context}"})
        messages.append({"role": "user", "content": task})
        return messages

    # ------------------------------------------------------------------ 便捷方法
    def run_with_trace(self, task: str, trace_path: str = "trace.jsonl", **kw: Any) -> AgentResult:
        result = self.run(task, **kw)
        result.trace.to_jsonl(trace_path)
        return result


def _assistant_tool_message(response: LLMResponse) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": response.text or None,
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name,
                             "arguments": json.dumps(call.arguments, ensure_ascii=False)},
            }
            for call in response.tool_calls
        ],
    }


def _signature(response: LLMResponse) -> str:
    return "|".join(
        f"{c.name}:{json.dumps(c.arguments, sort_keys=True, ensure_ascii=False)}"
        for c in response.tool_calls
    )


def run_task(task: str, tools: Sequence[Any] | None = None, llm: LLM | None = None,
             max_steps: int = 6) -> AgentResult:
    """一行的便捷入口，供示例与快速验证使用。"""
    from .llm import RuleBasedLLM

    registry = ToolRegistry()
    for fn in tools or []:
        registry.register(fn)
    agent = Agent(llm=llm or RuleBasedLLM(), tools=registry, max_steps=max_steps)
    return agent.run(task)
