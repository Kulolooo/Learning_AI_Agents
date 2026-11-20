"""记忆：工作记忆、情景记忆、语义记忆三层，加一个统一的装配器。

关键取舍（对应 ``read_vs_write_cost`` 教程的结论）：
写入越贵，越要想清楚"什么值得记"；读取越贵，越要控制"召回多少"。
本模块把两侧都做成显式参数：``token_budget`` 控制读，``importance`` 控制写。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

_TOKEN = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+")

# 极简停用词表：检索与抽取式作答都受益于去掉这些高频虚词。
_STOP = {
    "的", "了", "是", "在", "和", "与", "及", "或", "为", "把", "被", "对", "中",
    "上", "下", "吗", "呢", "啊", "这", "那", "个", "我", "你", "他", "她", "它",
    "们", "有", "会", "要", "可", "以", "就", "都", "而", "也", "很", "更", "最",
    "不", "没", "请", "帮", "问", "一", "起", "用", "怎", "么", "什", "如", "何",
    "哪", "些", "能", "需", "让", "给", "从", "到", "还", "又", "再", "但", "若",
}


def tokenize(text: str) -> list[str]:
    """中文按字、英文按词切分，并过滤停用词；无第三方分词器也能工作。"""
    return [t.lower() for t in _TOKEN.findall(text) if t.lower() not in _STOP]


# --------------------------------------------------------------------------- 向量化
class HashingEmbedder:
    """无依赖的哈希向量化（feature hashing）。

    把 token 及其二元组哈希到固定维度，再做 L2 归一化。它不是语义模型，
    但保留了词面相似性，足以演示"向量召回"的完整链路。
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        toks = tokenize(text)
        for tok in toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            vec[h % self.dim] += 1.0 if (h >> 8) % 2 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


# --------------------------------------------------------------------------- 记录
@dataclass
class MemoryItem:
    text: str
    kind: str = "semantic"
    importance: float = 0.5
    ts: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = dict(self.__dict__)
        data.pop("embedding", None)
        return data


# --------------------------------------------------------------------------- 短期
class BufferMemory:
    """滑动窗口：只保留最近 N 轮，避免上下文被历史淹没。"""

    def __init__(self, max_turns: int = 6) -> None:
        self.max_turns = max_turns
        self.turns: list[dict[str, str]] = []

    def add(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content})
        self.turns = self.turns[-self.max_turns * 2:]

    def messages(self) -> list[dict[str, str]]:
        return list(self.turns)

    def clear(self) -> None:
        self.turns.clear()


class SummaryMemory:
    """把早期对话压成摘要：牺牲细节换上下文预算。"""

    def __init__(self, llm: Any = None, trigger_turns: int = 8, keep_recent: int = 4) -> None:
        self.llm = llm
        self.trigger_turns = trigger_turns
        self.keep_recent = keep_recent
        self.summary = ""
        self.turns: list[dict[str, str]] = []

    def add(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content})
        if len(self.turns) > self.trigger_turns:
            self._compress()

    def _compress(self) -> None:
        head, tail = self.turns[:-self.keep_recent], self.turns[-self.keep_recent:]
        joined = "\n".join(f"{t['role']}: {t['content']}" for t in head)
        if self.llm is not None:
            prompt = [
                {"role": "system", "content": "把对话压缩成不超过 120 字的事实清单，保留人名、数字、结论。"},
                {"role": "user", "content": joined},
            ]
            try:
                self.summary = self.llm.complete(prompt).text.strip()
            except Exception:  # noqa: BLE001 —— 摘要失败不能影响主流程
                self.summary = _truncate(joined, 200)
        else:
            self.summary = _truncate((self.summary + "\n" + joined).strip(), 400)
        self.turns = tail

    def context(self) -> str:
        parts = []
        if self.summary:
            parts.append(f"[历史摘要] {self.summary}")
        parts.extend(f"{t['role']}: {t['content']}" for t in self.turns)
        return "\n".join(parts)


# --------------------------------------------------------------------------- 长期
class VectorMemory:
    """语义记忆：写入即向量化，读取按相似度 top-k。"""

    def __init__(self, embedder: HashingEmbedder | None = None, threshold: float = 0.15) -> None:
        self.embedder = embedder or HashingEmbedder()
        self.threshold = threshold
        self.items: list[MemoryItem] = []

    def add(self, text: str, *, importance: float = 0.5, kind: str = "semantic",
            tags: Iterable[str] | None = None, meta: dict[str, Any] | None = None,
            ts: float | None = None) -> MemoryItem:
        item = MemoryItem(
            text=text, kind=kind, importance=importance,
            tags=list(tags or []), meta=dict(meta or {}),
            ts=ts if ts is not None else time.time(),
            embedding=self.embedder.embed(text),
        )
        self.items.append(item)
        return item

    def search(self, query: str, k: int = 3) -> list[tuple[float, MemoryItem]]:
        q = self.embedder.embed(query)
        scored = [(cosine(q, it.embedding or []), it) for it in self.items]
        scored = [pair for pair in scored if pair[0] >= self.threshold]
        scored.sort(key=lambda p: p[0], reverse=True)
        return scored[:k]


class EpisodicStore:
    """情景记忆：把"哪次任务、用了哪些工具、结果如何"落盘，供跨会话复用。"""

    def __init__(self, path: str | Path = "memory/episodes.jsonl") -> None:
        self.path = Path(path)
        self.episodes: list[dict[str, Any]] = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.episodes.append(json.loads(line))

    def append(self, task: str, answer: str, tools: list[str],
               success: bool, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "task": task, "answer": answer, "tools": tools,
            "success": success, "ts": time.time(), "meta": meta or {},
        }
        self.episodes.append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def similar_tasks(self, task: str, k: int = 2) -> list[dict[str, Any]]:
        q = Counter(tokenize(task))
        scored = []
        for ep in self.episodes:
            c = Counter(tokenize(ep["task"]))
            overlap = sum(min(q[t], c[t]) for t in q.keys() & c.keys())
            scored.append((overlap / (sum(q.values()) or 1), ep))
        scored.sort(key=lambda p: p[0], reverse=True)
        return [ep for score, ep in scored[:k] if score > 0.2]


# --------------------------------------------------------------------------- 装配
class MemoryManager:
    """把三层记忆装配成一段可注入的上下文。"""

    def __init__(self, buffer: BufferMemory | None = None,
                 semantic: VectorMemory | None = None,
                 episodic: EpisodicStore | None = None,
                 token_budget: int = 1200) -> None:
        self.buffer = buffer or BufferMemory()
        self.semantic = semantic or VectorMemory()
        self.episodic = episodic
        self.token_budget = token_budget

    def observe(self, role: str, content: str) -> None:
        self.buffer.add(role, content)

    def remember(self, fact: str, importance: float = 0.7) -> None:
        if importance >= 0.6:  # 低价值信息不写入长期记忆
            self.semantic.add(fact, importance=importance)

    def build_context(self, query: str, k: int = 3) -> str:
        blocks: list[str] = []
        hits = self.semantic.search(query, k=k)
        if hits:
            # 时间戳随事实一起注入：模型才能在冲突时采用较新的一条
            blocks.append("[长期事实]\n" + "\n".join(
                f"- ({time.strftime('%Y-%m-%d', time.localtime(it.ts))}) {it.text}"
                for _, it in hits))
        if self.episodic is not None:
            past = self.episodic.similar_tasks(query)
            if past:
                blocks.append("[相似任务]\n" + "\n".join(
                    f"- {ep['task']} => {_truncate(ep['answer'], 80)}" for ep in past))
        blocks.append("[近期对话]\n" + "\n".join(
            f"{m['role']}: {m['content']}" for m in self.buffer.messages()))
        text = "\n\n".join(blocks)
        return _truncate(text, self.token_budget)


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
