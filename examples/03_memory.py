"""例 3：三层记忆。运行：``python examples/03_memory.py``

看点：低重要度的事实不会被写入；冲突事实带时间戳一起交给模型。
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from learning_agents.memory import (BufferMemory, EpisodicStore, MemoryManager,
                                    VectorMemory)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = EpisodicStore(Path(tmp) / "episodes.jsonl")
        store.append("整理季度退货报表", "输出 CSV + 三条结论", ["sql_query"], True)

        manager = MemoryManager(
            buffer=BufferMemory(max_turns=3),
            semantic=VectorMemory(),
            episodic=store,
            token_budget=800,
        )
        manager.observe("user", "下季度的复盘会要不要叫上财务？")
        manager.observe("assistant", "建议叫上，退货率异常需要财务确认口径。")

        manager.remember("用户偏好邮件通知，重要结论必须书面留档", importance=0.9)
        manager.remember("用户所在团队有 6 人", importance=0.7)
        manager.remember("今天聊到一半去开会了", importance=0.2)  # 低于阈值，丢弃

        # 冲突：旧偏好与新偏好（时间戳不同，模型据此采用较新的一条）
        manager.semantic.add("用户偏好电话通知", importance=0.8, kind="preference",
                             ts=time.time() - 90 * 86400)
        manager.semantic.add("用户偏好邮件通知（电话常漏接）", importance=0.85,
                             kind="preference")

        print(f"语义记忆条数：{len(manager.semantic.items)}（低重要度未写入）")
        print("\n装配后的上下文：\n" + "-" * 60)
        print(manager.build_context("通知偏好 复盘会", k=3))
        print("-" * 60)
        print("\n相似任务召回：", store.similar_tasks("再整理一次退货报表"))


if __name__ == "__main__":
    main()
