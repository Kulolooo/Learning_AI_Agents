"""例 4：检索增强与引用。运行：``python examples/04_rag.py``

看点：稀疏 + 稠密两路召回、RRF 融合、重排、引用覆盖率。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from learning_agents.rag import RAGPipeline, recall_at_k


def main() -> None:
    docs = {p.stem: p.read_text(encoding="utf-8") for p in sorted((ROOT / "data/corpus").glob("*.md"))}
    pipeline = RAGPipeline().index(docs, size=220, overlap=40)

    for query in ["切分粒度怎么选，重叠留多少？",
                  "记忆写入为什么昂贵？",
                  "工具描述应该写什么？"]:
        result = pipeline.answer(query, k=3)
        print(f"\n问：{query}")
        print(f"答：{result['answer']}")
        print("引用：", ", ".join(f"[{i + 1}] {c['id']} ({c['score']:.3f})"
                                 for i, c in enumerate(result["citations"])))
        print(f"覆盖率：{result['coverage']}")

    # 召回率示例：期望命中包含该句的块
    hits = pipeline.retrieve("引用覆盖率", k=3)
    print("\nrecall@3 =", recall_at_k([hits[0].chunk.id], hits))


if __name__ == "__main__":
    main()
