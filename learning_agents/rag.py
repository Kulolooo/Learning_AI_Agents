"""检索增强（RAG）：切分、索引、混合检索、重排、带引用的作答。

这里实现的是"可解释的最小 RAG"：每个环节都能单独替换、单独评测。
刻意不引入向量数据库——先用 200 行看清 BM25、向量召回、RRF 融合各自
解决了什么问题，再决定生产环境该换成什么组件。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from .memory import HashingEmbedder, cosine, tokenize

_SENT_SPLIT = re.compile(r"(?<=[。！？；\n])")


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    start: int = 0


@dataclass
class Hit:
    chunk: Chunk
    score: float
    retriever: str = "hybrid"


# --------------------------------------------------------------------------- 切分
def chunk_text(text: str, size: int = 320, overlap: int = 60,
               source: str = "doc") -> list[Chunk]:
    """按句子边界贪心切分，保证语义完整 + 相邻块重叠。"""
    if size <= 0:
        raise ValueError("size 必须为正")
    sentences = [s for s in _SENT_SPLIT.split(text) if s.strip()]
    chunks: list[Chunk] = []
    buf, cursor = "", 0
    for sent in sentences:
        if len(buf) + len(sent) > size and buf:
            chunks.append(Chunk(id=f"{source}#{len(chunks)}", text=buf.strip(),
                                source=source, start=max(cursor - overlap, 0)))
            buf = buf[-overlap:] if overlap else ""
        buf += sent
    if buf.strip():
        chunks.append(Chunk(id=f"{source}#{len(chunks)}", text=buf.strip(),
                            source=source, start=max(len(text) - len(buf), 0)))
    return chunks


# --------------------------------------------------------------------------- 稀疏
class BM25:
    """Okapi BM25：词频饱和 + 文档长度归一化 + IDF。"""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.docs: list[list[str]] = []
        self.df: dict[str, int] = {}
        self.avg_len = 0.0

    def fit(self, texts: Sequence[str]) -> "BM25":
        self.docs = [tokenize(t) for t in texts]
        self.df = {}
        for doc in self.docs:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1
        self.avg_len = sum(len(d) for d in self.docs) / max(len(self.docs), 1)
        return self

    def score(self, query: str, index: int) -> float:
        doc = self.docs[index]
        tf = {}
        for term in doc:
            tf[term] = tf.get(term, 0) + 1
        total = 0.0
        n = len(self.docs)
        for term in tokenize(query):
            if term not in tf:
                continue
            idf = math.log(1 + (n - self.df.get(term, 0) + 0.5) / (self.df.get(term, 0) + 0.5))
            freq = tf[term]
            denom = freq + self.k1 * (1 - self.b + self.b * len(doc) / (self.avg_len or 1))
            total += idf * freq * (self.k1 + 1) / denom
        return total


# --------------------------------------------------------------------------- 混合
class HybridRetriever:
    """BM25 + 向量召回，用 RRF（倒数排名融合）合并两路结果。

    RRF 的好处是不用把两种分数校准到同一量纲：
    ``score = Σ 1 / (k + rank_i)``，k 通常取 60。
    """

    def __init__(self, chunks: Sequence[Chunk], embedder: HashingEmbedder | None = None,
                 rrf_k: int = 60) -> None:
        self.chunks = list(chunks)
        self.embedder = embedder or HashingEmbedder()
        self.rrf_k = rrf_k
        self.bm25 = BM25().fit([c.text for c in self.chunks])
        self.vectors = [self.embedder.embed(c.text) for c in self.chunks]

    def sparse(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        scored = [(i, self.bm25.score(query, i)) for i in range(len(self.chunks))]
        scored = [p for p in scored if p[1] > 0]
        scored.sort(key=lambda p: p[1], reverse=True)
        return scored[:k]

    def dense(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        q = self.embedder.embed(query)
        scored = [(i, cosine(q, v)) for i, v in enumerate(self.vectors)]
        scored.sort(key=lambda p: p[1], reverse=True)
        return scored[:k]

    def search(self, query: str, k: int = 3) -> list[Hit]:
        fused: dict[int, float] = {}
        for rank, (idx, _) in enumerate(self.sparse(query, k * 3)):
            fused[idx] = fused.get(idx, 0) + 1 / (self.rrf_k + rank + 1)
        for rank, (idx, _) in enumerate(self.dense(query, k * 3)):
            fused[idx] = fused.get(idx, 0) + 1 / (self.rrf_k + rank + 1)
        ranked = sorted(fused.items(), key=lambda p: p[1], reverse=True)[:k]
        return [Hit(chunk=self.chunks[i], score=round(s, 6)) for i, s in ranked]

    def rerank(self, query: str, hits: Sequence[Hit], k: int = 3) -> list[Hit]:
        """词项覆盖率重排：便宜、可解释，能修正一部分排序错误。"""
        q_terms = set(tokenize(query))
        rescored = []
        for hit in hits:
            terms = set(tokenize(hit.chunk.text))
            coverage = len(q_terms & terms) / max(len(q_terms), 1)
            rescored.append(Hit(hit.chunk, round(0.5 * hit.score + 0.5 * coverage, 6), "rerank"))
        rescored.sort(key=lambda h: h.score, reverse=True)
        return rescored[:k]


# --------------------------------------------------------------------------- 管道
class RAGPipeline:
    """索引 -> 检索 -> 重排 -> 作答 -> 引用。"""

    def __init__(self, llm: Any = None, embedder: HashingEmbedder | None = None) -> None:
        self.llm = llm
        self.embedder = embedder or HashingEmbedder()
        self.retriever: HybridRetriever | None = None

    def index(self, documents: dict[str, str], size: int = 320, overlap: int = 60) -> "RAGPipeline":
        chunks: list[Chunk] = []
        for source, text in documents.items():
            chunks.extend(chunk_text(text, size=size, overlap=overlap, source=source))
        self.retriever = HybridRetriever(chunks, self.embedder)
        return self

    def index_chunks(self, chunks: Sequence[Chunk]) -> "RAGPipeline":
        self.retriever = HybridRetriever(chunks, self.embedder)
        return self

    def retrieve(self, query: str, k: int = 3) -> list[Hit]:
        if self.retriever is None:
            raise RuntimeError("请先调用 index()")
        return self.retriever.rerank(query, self.retriever.search(query, k * 2), k=k)

    def answer(self, query: str, k: int = 3) -> dict[str, Any]:
        hits = self.retrieve(query, k=k)
        context = "\n\n".join(f"[{i + 1}] ({h.chunk.id}) {h.chunk.text}"
                              for i, h in enumerate(hits))
        if self.llm is not None:
            prompt = [
                {"role": "system", "content": (
                    "你是检索增强问答助手。只依据给定资料回答；资料不足时明确说"
                    "‘资料未覆盖’。每个结论后用 [序号] 标注来源。")},
                {"role": "user", "content": f"资料：\n{context}\n\n问题：{query}"},
            ]
            text = self.llm.complete(prompt).text
        else:
            text = _extractive_answer(query, hits)
        return {
            "answer": text,
            "citations": [{"id": h.chunk.id, "source": h.chunk.source,
                           "score": h.score} for h in hits],
            "context": context,
            "coverage": citation_coverage(text, hits),
        }


def _extractive_answer(query: str, hits: Sequence[Hit]) -> str:
    """无模型时的抽取式作答：按 IDF 加权的词项覆盖率挑一句，并标注来源。"""
    if not hits:
        return "资料未覆盖该问题。"
    candidates: list[tuple[str, int, set[str]]] = []
    for i, hit in enumerate(hits):
        for sent in _SENT_SPLIT.split(hit.chunk.text):
            text = sent.strip().lstrip("#").strip()
            if len(text) >= 12:  # 过滤标题残片与短句
                candidates.append((text, i + 1, set(tokenize(text))))
    if not candidates:
        return "资料未覆盖该问题。"

    df: dict[str, int] = {}
    for _, _, terms in candidates:
        for term in terms:
            df[term] = df.get(term, 0) + 1
    total = len(candidates)
    q_terms = set(tokenize(query))
    scored: list[tuple[float, float, str, int]] = []
    for text, idx, terms in candidates:
        matched = q_terms & terms
        if not matched:
            continue
        coverage = len(matched) / max(len(q_terms), 1)
        idf = sum(math.log(1 + total / (df[t] + 0.5)) for t in matched)
        scored.append((coverage, idf, text, idx))
    if not scored:
        return f"{hits[0].chunk.text[:120]} [1]"
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    picked: list[tuple[str, int]] = []
    used_hits: set[int] = set()
    for coverage, _, text, idx in scored:
        if idx in used_hits or coverage < scored[0][0] * 0.5:
            continue
        if any(text in prev or prev in text for prev, _ in picked):
            continue  # 重叠切分会产生近乎重复的句子，去重
        picked.append((text, idx))
        used_hits.add(idx)
        if len(picked) == 2:
            break
    body = "；".join(text.rstrip("。；; ") for text, _ in picked)
    marks = "".join(f"[{idx}]" for _, idx in picked)
    return f"{body}。 {marks}"


def citation_coverage(answer: str, hits: Sequence[Hit]) -> float:
    """答案里被引用到的检索块比例，衡量"有据可依"的程度。"""
    if not hits:
        return 0.0
    cited = set(re.findall(r"\[(\d+)\]", answer))
    valid = {str(i + 1) for i in range(len(hits))}
    return round(len(cited & valid) / len(hits), 3)


def recall_at_k(expected_ids: Iterable[str], hits: Sequence[Hit]) -> float:
    expected = set(expected_ids)
    if not expected:
        return 0.0
    got = {h.chunk.id for h in hits}
    return round(len(expected & got) / len(expected), 3)
