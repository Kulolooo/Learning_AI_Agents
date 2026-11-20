"""反思与自我修正：让模型给自己打分，再根据评分改稿。

两个必须正视的问题：

1. **自评会漂移**：同一份稿子，模型前后两次评分可能不一致。解法是
   "外部锚点"——可执行测试、检索引用、固定 rubric，而不是让模型凭感觉。
2. **反思会过拟合**：反复改到"评审满意"不等于"用户满意"。所以要有
   轮数上限、收益递减判断，以及最终由规则兜底的验收条件。
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence


@dataclass
class Critique:
    score: float                       # 0-1
    issues: list[str] = field(default_factory=list)
    verdict: str = ""
    raw: str = ""

    @property
    def passed(self) -> bool:
        return self.score >= 0.8 and not self.issues


class HeuristicCritic:
    """可解释的规则评审：长度、结构、引用、关键词覆盖、空话检测。"""

    def __init__(self, rubric: dict[str, Any] | None = None) -> None:
        self.rubric = rubric or {
            "min_chars": 80,
            "require_citation": True,
            "required_terms": [],
            "banned_phrases": ["众所周知", "毋庸置疑", "总而言之"],
        }

    def __call__(self, text: str, task: str = "") -> Critique:
        issues: list[str] = []
        checks = 0
        passed = 0

        checks += 1
        if len(text) >= self.rubric.get("min_chars", 0):
            passed += 1
        else:
            issues.append(f"篇幅不足（{len(text)} 字）")

        if self.rubric.get("require_citation"):
            checks += 1
            if "[" in text and "]" in text:
                passed += 1
            else:
                issues.append("缺少来源引用标记 [n]")

        terms = self.rubric.get("required_terms") or []
        if terms:
            checks += 1
            missing = [t for t in terms if t not in text]
            if not missing:
                passed += 1
            else:
                issues.append(f"缺少要点：{missing}")

        banned = [p for p in self.rubric.get("banned_phrases", []) if p in text]
        checks += 1
        if not banned:
            passed += 1
        else:
            issues.append(f"存在空泛表述：{banned}")

        score = round(passed / max(checks, 1), 3)
        return Critique(score=score, issues=issues,
                        verdict="pass" if score >= 0.8 and not issues else "revise")


class ReflectionLoop:
    """生成 -> 评审 -> 修订，直到通过或触顶。"""

    def __init__(self, generate: Callable[[str], str],
                 revise: Callable[[str, Critique], str],
                 critic: Callable[[str, str], Critique],
                 max_rounds: int = 3,
                 min_gain: float = 0.02) -> None:
        self.generate = generate
        self.revise = revise
        self.critic = critic
        self.max_rounds = max_rounds
        self.min_gain = min_gain
        self.history: list[dict[str, Any]] = []

    def run(self, task: str) -> dict[str, Any]:
        draft = self.generate(task)
        critique = self.critic(draft, task)
        self.history.append({"round": 0, "score": critique.score,
                             "issues": critique.issues, "text": draft})
        best = (critique.score, draft)

        for round_no in range(1, self.max_rounds + 1):
            if critique.passed:
                break
            draft = self.revise(draft, critique)
            critique = self.critic(draft, task)
            self.history.append({"round": round_no, "score": critique.score,
                                 "issues": critique.issues, "text": draft})
            if critique.score < best[0] - self.min_gain:
                break  # 越改越差，回退
            if critique.score > best[0] + self.min_gain:
                best = (critique.score, draft)

        return {
            "final": best[1] if best[0] >= self.history[-1]["score"] else self.history[-1]["text"],
            "score": max(best[0], self.history[-1]["score"]),
            "rounds": len(self.history) - 1,
            "passed": critique.passed,
            "history": self.history,
        }


class CodeHealer:
    """自愈代码：跑、抓错、让模型改、再跑。

    执行发生在独立子进程里，带超时；这是最低限度的隔离，
    生产环境应换成容器或沙箱。
    """

    def __init__(self, fixer: Callable[[str, str], str], max_rounds: int = 3,
                 timeout: float = 5.0) -> None:
        self.fixer = fixer
        self.max_rounds = max_rounds
        self.timeout = timeout
        self.attempts: list[dict[str, Any]] = []

    def run(self, code: str) -> dict[str, Any]:
        current = code
        for round_no in range(self.max_rounds + 1):
            ok, output = self._execute(current)
            self.attempts.append({"round": round_no, "ok": ok, "output": output[:400]})
            if ok:
                return {"ok": True, "code": current, "output": output,
                        "rounds": round_no, "attempts": self.attempts}
            if round_no == self.max_rounds:
                break
            current = self.fixer(current, output)
        return {"ok": False, "code": current, "output": self.attempts[-1]["output"],
                "rounds": self.max_rounds, "attempts": self.attempts}

    def _execute(self, code: str) -> tuple[bool, str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snippet.py"
            path.write_text(code, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [sys.executable, str(path)], capture_output=True, text=True,
                    timeout=self.timeout, cwd=tmp,
                )
            except subprocess.TimeoutExpired:
                return False, f"TimeoutError: 执行超过 {self.timeout}s"
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, output.strip()


def self_consistency(samples: Sequence[str], normalizer: Callable[[str], str] | None = None
                     ) -> dict[str, Any]:
    """多次采样的多数投票：便宜地换取一点稳定性。"""
    norm = normalizer or (lambda s: s.strip())
    votes: dict[str, int] = {}
    for s in samples:
        key = norm(s)
        votes[key] = votes.get(key, 0) + 1
    best = max(votes.items(), key=lambda kv: kv[1])
    return {"answer": best[0], "votes": best[1], "total": len(samples),
            "agreement": round(best[1] / max(len(samples), 1), 3)}
