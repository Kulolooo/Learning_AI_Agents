"""记忆与检索的行为测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from learning_agents.memory import (BufferMemory, EpisodicStore, MemoryManager,
                                    SummaryMemory, VectorMemory, tokenize)
from learning_agents.rag import (BM25, RAGPipeline, chunk_text, citation_coverage,
                                 recall_at_k)

DOCS = {
    "a": "智能体的核心是循环。循环由上下文驱动，终止条件包括步数上限与预算耗尽。"
         "工具失败应当作为观察回灌，而不是直接抛出异常。",
    "b": "检索增强把模型记忆换成可核验的资料。切分粒度影响召回质量，"
         "块长通常控制在两百到四百字，相邻块保留百分之十到二十的重叠。",
    "c": "评估需要固定用例。召回率衡量资料是否被检出，引用覆盖率衡量答案是否有据。",
}


class TestMemory(unittest.TestCase):
    def test_buffer_window(self) -> None:
        buf = BufferMemory(max_turns=2)
        for i in range(5):
            buf.add("user", f"m{i}")
        self.assertEqual([m["content"] for m in buf.messages()], ["m1", "m2", "m3", "m4"])

    def test_summary_memory_compresses(self) -> None:
        mem = SummaryMemory(trigger_turns=4, keep_recent=2)
        for i in range(6):
            mem.add("user", f"第 {i} 条消息，包含一些需要保留的细节内容")
        self.assertTrue(mem.summary)
        self.assertLessEqual(len(mem.turns), 4)

    def test_vector_memory_ranks_by_similarity(self) -> None:
        vm = VectorMemory()
        vm.add("客户的退款申请需要财务审批")
        vm.add("服务器磁盘使用率达到百分之九十需要告警")
        hits = vm.search("退款审批流程", k=1)
        self.assertIn("退款", hits[0][1].text)

    def test_importance_filters_writes(self) -> None:
        manager = MemoryManager()
        manager.remember("门店 A 退货率异常", importance=0.9)
        manager.remember("今天天气不错", importance=0.1)
        self.assertEqual(len(manager.semantic.items), 1)
        self.assertIn("门店 A", manager.build_context("退货率"))

    def test_episodic_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ep.jsonl"
            store = EpisodicStore(path)
            store.append("统计退货率", "3.2%", ["sql"], True)
            reopened = EpisodicStore(path)
            self.assertEqual(len(reopened.episodes), 1)
            self.assertEqual(reopened.similar_tasks("再统计一次退货率")[0]["answer"], "3.2%")

    def test_tokenize_drops_stopwords(self) -> None:
        tokens = tokenize("这是一个关于智能体的测试")
        self.assertNotIn("的", tokens)
        self.assertIn("智", tokens)


class TestChunking(unittest.TestCase):
    def test_chunks_cover_text(self) -> None:
        text = "。".join(f"第{i}句话讲述了智能体循环的一个细节" for i in range(20)) + "。"
        chunks = chunk_text(text, size=60, overlap=10)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c.text) <= 90 for c in chunks))
        self.assertTrue(all(c.id.startswith("doc#") for c in chunks))

    def test_invalid_size(self) -> None:
        with self.assertRaises(ValueError):
            chunk_text("abc", size=0)


class TestRetrieval(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = RAGPipeline().index(DOCS, size=80, overlap=10)

    def test_bm25_prefers_exact_terms(self) -> None:
        bm25 = BM25().fit(list(DOCS.values()))
        scores = [bm25.score("引用覆盖率", i) for i in range(len(DOCS))]
        self.assertEqual(scores.index(max(scores)), 2)

    def test_hybrid_returns_hits(self) -> None:
        hits = self.pipeline.retrieve("切分粒度怎么设置", k=2)
        self.assertEqual(len(hits), 2)
        self.assertTrue(all(h.score > 0 for h in hits))

    def test_answer_has_citation(self) -> None:
        result = self.pipeline.answer("切分粒度怎么设置", k=2)
        self.assertIn("[", result["answer"])
        self.assertGreater(result["coverage"], 0)

    def test_recall_at_k(self) -> None:
        hits = self.pipeline.retrieve("切分粒度", k=3)
        self.assertGreater(recall_at_k([h.chunk.id for h in hits[:1]], hits), 0)

    def test_coverage_metric(self) -> None:
        hits = self.pipeline.retrieve("切分", k=2)
        self.assertEqual(citation_coverage("没有引用", hits), 0.0)
        self.assertEqual(citation_coverage("[1] 与 [2]", hits), 1.0)


if __name__ == "__main__":
    unittest.main()
