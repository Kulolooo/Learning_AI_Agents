"""评估：把"感觉还行"变成可复现的分数。

三层评估，成本递增：

1. **规则断言**（毫秒级）：是否调用了指定工具、是否超出步数、是否包含关键词。
2. **轨迹指标**（毫秒级）：步数、工具调用数、错误率、token、时延分布。
3. **评审打分**（需要模型）：rubric 逐项打分，用于开放性任务。

前两层应当在 CI 里每次提交都跑；第三层按发布节奏跑。
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from .agent import AgentResult


@dataclass
class EvalCase:
    id: str
    task: str
    expected_terms: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    max_steps: int = 8
    max_tokens: int = 40_000

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


class TraceEvaluator:
    """基于一次运行的轨迹做断言。"""

    def __init__(self, cases: Sequence[EvalCase]) -> None:
        self.cases = {c.id: c for c in cases}

    def evaluate(self, result: AgentResult, case: EvalCase) -> dict[str, Any]:
        tools_called = [
            ev.name for ev in result.trace.events if ev.kind == "tool.call"
        ] if result.trace else []
        answer = result.answer or ""
        checks = [
            Check("最终有答复", bool(answer.strip()), f"{len(answer)} 字"),
            Check("未超步数", result.steps <= case.max_steps or result.steps == 0,
                  f"steps={result.steps}"),
            Check("工具齐全", all(t in tools_called for t in case.required_tools),
                  f"required={case.required_tools}, called={tools_called}"),
            Check("无禁用工具", not any(t in tools_called for t in case.forbidden_tools),
                  f"forbidden={case.forbidden_tools}"),
            Check("关键词覆盖", all(t in answer for t in case.expected_terms),
                  f"missing={[t for t in case.expected_terms if t not in answer]}"),
            Check("token 预算", result.usage.total <= case.max_tokens,
                  f"tokens={result.usage.total}"),
            Check("正常终止", result.stopped_reason in ("final",), result.stopped_reason),
        ]
        return {
            "case": case.id,
            "passed": all(c.passed for c in checks),
            "score": round(sum(c.passed for c in checks) / len(checks), 3),
            "checks": [c.__dict__ for c in checks],
            "tools_called": tools_called,
            "tokens": result.usage.total,
        }

    def run_suite(self, results: dict[str, AgentResult]) -> dict[str, Any]:
        rows = [self.evaluate(results[cid], case) for cid, case in self.cases.items()
                if cid in results]
        return summarize(rows)


def summarize(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"cases": 0, "pass_rate": 0.0, "rows": []}
    return {
        "cases": len(rows),
        "pass_rate": round(sum(r["passed"] for r in rows) / len(rows), 3),
        "avg_score": round(statistics.mean(r["score"] for r in rows), 3),
        "avg_tokens": round(statistics.mean(r["tokens"] for r in rows), 1),
        "rows": list(rows),
    }


def pass_at_k(successes: int, total: int, k: int = 1) -> float:
    """pass@k 的无偏估计（Chen et al., 2021 的数值稳定写法）。"""
    if total <= 0 or successes <= 0:
        return 0.0
    if total - successes < k:
        return 1.0
    ratio = 1.0
    for i in range(k):
        ratio *= (total - successes - i) / (total - i)
    return round(1 - ratio, 4)


def rubric_score(answer: str, rubric: dict[str, float]) -> dict[str, Any]:
    """按 rubric 关键词加权打分；每项分数 = 命中关键词比例 × 权重。"""
    total_weight = sum(rubric.values()) or 1.0
    detail, got = [], 0.0
    for item, weight in rubric.items():
        terms = [t for t in item.replace("|", " ").split() if t]
        hit = sum(1 for t in terms if t in answer)
        score = (hit / len(terms)) if terms else 0.0
        got += score * weight
        detail.append({"criterion": item, "score": round(score, 2), "weight": weight})
    return {"score": round(got / total_weight, 3), "detail": detail}


def latency_percentiles(values: Sequence[float]) -> dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "max": 0.0}
    ordered = sorted(values)
    idx = min(int(len(ordered) * 0.95), len(ordered) - 1)
    return {"p50": round(statistics.median(ordered), 2),
            "p95": round(ordered[idx], 2), "max": round(ordered[-1], 2)}


def cost(tokens: int, price_per_mtok: float = 0.6) -> float:
    """按每百万 token 单价估算成本，默认值只是示例量级。"""
    return round(tokens / 1_000_000 * price_per_mtok, 6)


def load_trace(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def format_table(result: dict[str, Any]) -> str:
    """把评估结果渲染成等宽表格，方便贴进 PR 或终端。"""
    lines = [
        f"{'case':<28}{'pass':<8}{'score':<8}{'tokens':<10}失败项",
        "-" * 78,
    ]
    for row in result.get("rows", []):
        failed = [c["name"] for c in row["checks"] if not c["passed"]]
        lines.append(
            f"{row['case']:<28}{str(row['passed']):<8}{row['score']:<8}"
            f"{row['tokens']:<10}{','.join(failed) or '-'}"
        )
    lines.append("-" * 78)
    lines.append(f"通过率 {result.get('pass_rate', 0):.1%}  "
                 f"平均分 {result.get('avg_score', 0):.2f}  "
                 f"平均 token {result.get('avg_tokens', 0):.0f}")
    return "\n".join(lines)
