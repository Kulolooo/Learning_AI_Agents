"""规划：先想清楚再做，还是边做边想。

三种常见形态，复杂度递增：

* ``Router``          —— 一步决策：把请求分给最合适的处理器。
* ``PlanAndExecute``  —— 先出计划，再逐步执行，失败可重规划。
* ``TaskGraph``       —— 显式依赖图，支持拓扑排序与并行层。

工程经验：能路由解决的不要规划，能规划解决的不要多智能体。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


# --------------------------------------------------------------------------- 计划
@dataclass
class PlanStep:
    id: str
    goal: str
    tool: str = ""
    status: str = "pending"      # pending | running | done | failed
    result: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "goal": self.goal, "tool": self.tool,
                "status": self.status, "result": self.result}


@dataclass
class Plan:
    steps: list[PlanStep] = field(default_factory=list)

    def next_pending(self) -> PlanStep | None:
        return next((s for s in self.steps if s.status == "pending"), None)

    def describe(self) -> str:
        return "\n".join(f"{s.id}. [{s.status}] {s.goal}" for s in self.steps)


class Planner:
    """两种模式：给定模板（离线、可控）或让模型产出 JSON 计划。"""

    def __init__(self, llm: Any = None) -> None:
        self.llm = llm

    def from_template(self, goals: Sequence[str], tools: Sequence[str] | None = None) -> Plan:
        tools = list(tools or [])
        steps = [
            PlanStep(id=f"s{i + 1}", goal=goal, tool=tools[i] if i < len(tools) else "")
            for i, goal in enumerate(goals)
        ]
        return Plan(steps)

    def from_llm(self, task: str, tools: Sequence[str], max_steps: int = 5) -> Plan:
        if self.llm is None:
            raise RuntimeError("未提供模型，无法自动规划")
        prompt = [
            {"role": "system", "content": (
                "把任务拆成 2-5 个有序子步骤。只输出 JSON："
                '{"steps":[{"goal":"...","tool":"工具名或空串"}]}。'
                f"可用工具：{', '.join(tools)}")},
            {"role": "user", "content": task},
        ]
        raw = self.llm.complete(prompt).text
        data = json.loads(_strip_fence(raw))
        steps = [
            PlanStep(id=f"s{i + 1}", goal=str(item.get("goal", "")),
                     tool=str(item.get("tool", "")))
            for i, item in enumerate(data.get("steps", [])[:max_steps])
        ]
        return Plan(steps)


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    return text.strip()


# --------------------------------------------------------------------------- 执行
class PlanAndExecute:
    """逐步执行计划；某步失败时，把错误交给重规划器（可选用模型）。"""

    def __init__(self, executor: Callable[[PlanStep], str],
                 replanner: Callable[[Plan, PlanStep, str], Plan] | None = None,
                 max_replans: int = 1) -> None:
        self.executor = executor
        self.replanner = replanner
        self.max_replans = max_replans
        self.history: list[dict[str, Any]] = []

    def run(self, plan: Plan, stop_on_failure: bool = False) -> Plan:
        replans = 0
        while (step := plan.next_pending()) is not None:
            step.status = "running"
            try:
                step.result = self.executor(step)
                step.status = "done"
            except Exception as exc:  # noqa: BLE001
                step.status = "failed"
                step.result = f"{type(exc).__name__}: {exc}"
                self.history.append({"step": step.id, "status": "failed",
                                     "result": step.result[:200]})
                if stop_on_failure or self.replanner is None or replans >= self.max_replans:
                    break
                plan = self.replanner(plan, step, step.result)
                replans += 1
                continue
            self.history.append({"step": step.id, "status": step.status,
                                 "result": step.result[:200]})
        return plan


# --------------------------------------------------------------------------- 路由
class Router:
    """一步决策路由：用关键词或模型判断请求该交给谁。"""

    def __init__(self, routes: dict[str, Sequence[str]], fallback: str = "general",
                 llm: Any = None) -> None:
        self.routes = {name: list(kws) for name, kws in routes.items()}
        self.fallback = fallback
        self.llm = llm
        self.log: list[tuple[str, str, str]] = []

    def decide(self, text: str) -> str:
        best, best_score = self.fallback, 0
        for name, keywords in self.routes.items():
            score = sum(1 for kw in keywords if kw and kw in text)
            if score > best_score:
                best, best_score = name, score
        self.log.append((text, best, "keyword"))
        return best

    def dispatch(self, text: str, handlers: dict[str, Callable[[str], Any]]) -> Any:
        route = self.decide(text)
        if route not in handlers:
            raise KeyError(f"路由 {route} 没有对应处理器")
        return handlers[route](text)


# --------------------------------------------------------------------------- 图
class TaskGraph:
    """显式依赖图：``add(a, deps=['b'])`` 表示 a 依赖 b。"""

    def __init__(self) -> None:
        self.nodes: dict[str, list[str]] = {}
        self.funcs: dict[str, Callable[..., Any]] = {}

    def add(self, name: str, fn: Callable[..., Any], deps: Sequence[str] = ()) -> "TaskGraph":
        self.nodes[name] = list(deps)
        self.funcs[name] = fn
        return self

    def layers(self) -> list[list[str]]:
        """拓扑分层：同一层的节点互不依赖，可以并行。"""
        remaining = dict(self.nodes)
        layers: list[list[str]] = []
        while remaining:
            ready = [n for n, deps in remaining.items() if not (set(deps) & set(remaining))]
            if not ready:
                raise ValueError(f"检测到循环依赖：{sorted(remaining)}")
            layers.append(sorted(ready))
            for n in ready:
                remaining.pop(n)
        return layers

    def run(self, parallel: bool = False) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for layer in self.layers():
            if parallel and len(layer) > 1:
                from concurrent.futures import ThreadPoolExecutor

                with ThreadPoolExecutor(max_workers=len(layer)) as pool:
                    futures = {
                        name: pool.submit(self.funcs[name],
                                          **{dep: results[dep] for dep in self.nodes[name]})
                        for name in layer
                    }
                    for name, fut in futures.items():
                        results[name] = fut.result()
            else:
                for name in layer:
                    results[name] = self.funcs[name](
                        **{dep: results[dep] for dep in self.nodes[name]})
        return results
