"""多智能体：把"一个大脑"拆成"一组角色 + 一套协议"。

本模块提供四种最常见拓扑，复杂度递增：

* ``Pipeline``    线性流水线（写 -> 审 -> 改），无协商。
* ``Supervisor``  主管拆解、分派、汇总，星型结构。
* ``Debate``      正反方 + 裁判，适合作出有争议的判断。
* ``Blackboard``  共享黑板，事件驱动，适合长任务与异步协作。

判据很简单：**如果单个 Agent 加两个工具就能做完，就别上多智能体。**
多智能体的收益来自"角色专业化 + 独立上下文"，代价是通信开销与错误传播。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence


@dataclass
class AgentMessage:
    sender: str
    recipient: str
    content: str
    kind: str = "result"        # task | result | critique | decision
    ts: float = field(default_factory=time.time)
    meta: dict[str, Any] = field(default_factory=dict)


class AgentBase:
    """统一的智能体接口：``handle(task, context) -> str``。"""

    def __init__(self, name: str, fn: Callable[[str, str], str],
                 role: str = "") -> None:
        self.name = name
        self.fn = fn
        self.role = role or name
        self.inbox: list[AgentMessage] = []

    def handle(self, task: str, context: str = "") -> str:
        return self.fn(task, context)

    def send(self, to: "AgentBase", content: str, kind: str = "task") -> AgentMessage:
        msg = AgentMessage(sender=self.name, recipient=to.name, content=content, kind=kind)
        to.inbox.append(msg)
        return msg


# --------------------------------------------------------------------------- 流水线
class Pipeline:
    """严格顺序，上一步的输出是下一步的输入。最容易调试，也最容易级联错误。"""

    def __init__(self, stages: Sequence[tuple[str, Callable[[str], str]]]) -> None:
        self.stages = list(stages)
        self.log: list[dict[str, Any]] = []

    def run(self, task: str) -> dict[str, Any]:
        current = task
        for name, fn in self.stages:
            started = time.perf_counter()
            try:
                current = fn(current)
                self.log.append({"stage": name, "ok": True,
                                 "ms": round((time.perf_counter() - started) * 1000, 1)})
            except Exception as exc:  # noqa: BLE001
                self.log.append({"stage": name, "ok": False, "error": str(exc)})
                return {"ok": False, "failed_stage": name, "output": current, "log": self.log}
        return {"ok": True, "output": current, "log": self.log}


# --------------------------------------------------------------------------- 主管
class Supervisor:
    """主管持有全局目标，把子任务分给专家，最后合并。

    ``assign`` 决定"谁做哪一步"；``merge`` 决定"怎么把碎片拼回整体"。
    这两处是最容易出错的地方，务必可替换、可测试。
    """

    def __init__(self, workers: Sequence[AgentBase],
                 plan: Callable[[str], list[str]],
                 assign: Callable[[str], str] | None = None,
                 merge: Callable[[str, list[tuple[str, str]]], str] | None = None) -> None:
        if not workers:
            raise ValueError("Supervisor 至少需要一个 worker；空列表会让分派无解")
        self.workers = {w.name: w for w in workers}
        self.plan = plan
        self.assign = assign or self._round_robin
        self.merge = merge or self._default_merge
        self.transcript: list[AgentMessage] = []

    def _round_robin(self, subtask: str) -> str:
        index = len(self.transcript) % len(self.workers)
        return list(self.workers)[index]

    def _default_merge(self, task: str, parts: list[tuple[str, str]]) -> str:
        return "\n\n".join(f"## {name}\n{text}" for name, text in parts)

    def run(self, task: str) -> dict[str, Any]:
        subtasks = self.plan(task)
        parts: list[tuple[str, str]] = []
        for sub in subtasks:
            worker_name = self.assign(sub)
            worker = self.workers[worker_name]
            msg = AgentMessage(sender="supervisor", recipient=worker_name, content=sub)
            self.transcript.append(msg)
            try:
                result = worker.handle(sub, context=task)
            except Exception as exc:  # noqa: BLE001
                result = f"[{worker_name} 失败] {type(exc).__name__}: {exc}"
            self.transcript.append(AgentMessage(sender=worker_name, recipient="supervisor",
                                                content=result))
            parts.append((worker_name, result))
        return {"ok": all(not p[1].startswith("[") for p in parts),
                "output": self.merge(task, parts), "parts": parts,
                "subtasks": subtasks, "transcript": self.transcript}


# --------------------------------------------------------------------------- 辩论
class Debate:
    """正反方交替发言，裁判在第 N 轮后裁决。

    适用于"没有唯一正确答案、但需要压测论证"的判断类任务。
    这里用可替换的角色函数，真实场景通常各自绑定一个 Agent。
    """

    def __init__(self, proposer: Callable[[str, str], str],
                 critic: Callable[[str, str], str],
                 judge: Callable[[str, Sequence[str]], str],
                 rounds: int = 2) -> None:
        self.proposer = proposer
        self.critic = critic
        self.judge = judge
        self.rounds = rounds
        self.transcript: list[dict[str, str]] = []

    def run(self, topic: str) -> dict[str, Any]:
        pro = self.proposer(topic, "")
        self.transcript.append({"role": "proposer", "content": pro})
        con = ""
        for round_no in range(self.rounds):
            con = self.critic(topic, pro)
            self.transcript.append({"role": "critic", "content": con})
            pro = self.proposer(topic, con)
            self.transcript.append({"role": "proposer", "content": pro})
        decision = self.judge(topic, [t["content"] for t in self.transcript])
        return {"decision": decision, "transcript": self.transcript,
                "rounds": self.rounds}


# --------------------------------------------------------------------------- 黑板
class Blackboard:
    """共享状态：任何 Agent 可读，写入带版本号，便于审计与回放。"""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._versions: dict[str, int] = {}
        self.events: list[dict[str, Any]] = []

    def write(self, key: str, value: Any, author: str = "system") -> int:
        if key in self._data and self._data[key] == value:
            return self._versions[key]  # 值未变则不产生新版本，便于判断收敛
        self._versions[key] = self._versions.get(key, 0) + 1
        self._data[key] = value
        event = {"key": key, "version": self._versions[key], "author": author, "value": value}
        self.events.append(event)
        return self._versions[key]

    def read(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def history(self, key: str) -> list[dict[str, Any]]:
        return [e for e in self.events if e["key"] == key]

    def snapshot(self) -> dict[str, Any]:
        return dict(self._data)


class BlackboardSystem:
    """极简事件循环：每轮让所有 Agent 读黑板、写结论，直到没有新事件。"""

    def __init__(self, agents: Sequence[AgentBase], board: Blackboard | None = None,
                 max_rounds: int = 4) -> None:
        self.agents = list(agents)
        self.board = board or Blackboard()
        self.max_rounds = max_rounds

    def run(self, task: str) -> dict[str, Any]:
        self.board.write("task", task, "user")
        rounds = 0
        for round_no in range(self.max_rounds):
            before = len(self.board.events)
            for agent in self.agents:
                snapshot = self.board.snapshot()
                try:
                    out = agent.handle(task, context=str(snapshot))
                except Exception as exc:  # noqa: BLE001
                    out = f"[error] {type(exc).__name__}: {exc}"
                agent.inbox.append(AgentMessage(sender="blackboard", recipient=agent.name,
                                                content=out))
                self.board.write(f"note:{agent.name}", out, agent.name)
            rounds = round_no + 1
            if len(self.board.events) == before:
                break
        return {"board": self.board.snapshot(), "events": self.board.events,
                "rounds": rounds}


def consensus(votes: Iterable[str]) -> tuple[str, float]:
    counts: dict[str, int] = {}
    items = list(votes)
    for v in items:
        counts[v] = counts.get(v, 0) + 1
    if not items:
        return "", 0.0
    top = max(counts.items(), key=lambda kv: kv[1])
    return top[0], round(top[1] / len(items), 3)
