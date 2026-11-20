"""结构化轨迹（trace）：Agent 的"飞行记录仪"。

设计要点
--------
1. 事件是一等公民：每个决策、每次工具调用、每次重试都落成一条事件，
   而不是散落在 print 里。这样评估、回放、排障共用同一份数据。
2. 事件带层级：``span`` 生成父子关系，最终可以打印成树，也可以在
   前端渲染成瀑布图。
3. 落盘即 JSONL：一行一个事件，便于 grep、jq、导入数据仓库。
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator


@dataclass
class Event:
    """一条轨迹事件。"""

    seq: int
    ts: float
    kind: str
    name: str = ""
    span_id: str = ""
    parent_id: str = ""
    duration_ms: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Tracer:
    """收集事件，并支持树状打印与 JSONL 落盘。"""

    def __init__(self, echo: bool = False) -> None:
        self.events: list[Event] = []
        self.echo = echo
        self._stack: list[str] = []
        self._start = time.perf_counter()

    # ------------------------------------------------------------------ 基础
    def event(self, kind: str, name: str = "", **data: Any) -> Event:
        ev = Event(
            seq=len(self.events) + 1,
            ts=round(time.perf_counter() - self._start, 6),
            kind=kind,
            name=name,
            span_id=self._stack[-1] if self._stack else "",
            parent_id=self._stack[-2] if len(self._stack) > 1 else "",
            data=data,
        )
        self.events.append(ev)
        if self.echo:
            print(f"[{ev.seq:03d}] {ev.kind:<12} {ev.name:<22} {_brief(data)}")
        return ev

    @contextmanager
    def span(self, name: str, **data: Any) -> Iterator[Event]:
        span_id = uuid.uuid4().hex[:8]
        start = time.perf_counter()
        ev = self.event("span.start", name=name, span=span_id, **data)
        self._stack.append(span_id)
        try:
            yield ev
        finally:
            self._stack.pop()
            self.event(
                "span.end",
                name=name,
                span=span_id,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
            )

    # ------------------------------------------------------------------ 输出
    def to_jsonl(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            for ev in self.events:
                fh.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")
        return p

    def tree(self) -> str:
        """把事件渲染成缩进树；span 内的普通事件缩进一层。"""
        lines: list[str] = []
        depth = 0
        for ev in self.events:
            if ev.kind == "span.end":
                depth = max(depth - 1, 0)
                extra = f" ({ev.duration_ms:.1f}ms)"
                lines.append("  " * depth + f"└─ end {ev.name}{extra}")
                continue
            prefix = "  " * depth
            if ev.kind == "span.start":
                lines.append(prefix + f"┌─ {ev.name} " + _brief(ev.data))
                depth += 1
            elif depth:
                lines.append(prefix + f"│  {ev.kind}: {ev.name} {_brief(ev.data)}")
            else:
                lines.append(f"{ev.kind}: {ev.name} {_brief(ev.data)}")
        return "\n".join(lines)

    def summary(self) -> dict[str, Any]:
        kinds: dict[str, int] = {}
        for ev in self.events:
            kinds[ev.kind] = kinds.get(ev.kind, 0) + 1
        return {
            "events": len(self.events),
            "kinds": kinds,
            "tool_calls": kinds.get("tool.call", 0),
            "steps": kinds.get("agent.step", 0),
        }


def _brief(data: dict[str, Any], limit: int = 72) -> str:
    if not data:
        return ""
    text = json.dumps(data, ensure_ascii=False)
    return text if len(text) <= limit else text[: limit - 1] + "…"
