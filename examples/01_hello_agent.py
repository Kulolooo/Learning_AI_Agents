"""例 1：最小闭环。运行：``python examples/01_hello_agent.py``

观察三件事：调用了哪个工具、花了多少 token、为什么停。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from learning_agents.agent import Agent
from learning_agents.llm import RuleBasedLLM
from learning_agents.tools import ToolRegistry, tool


@tool
def word_count(text: str) -> str:
    """统计中文字符数  text: 待统计的文本"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return f"共 {len(text)} 个字符，其中中文 {cjk} 个"


def main() -> None:
    registry = ToolRegistry().register_all([word_count])
    agent = Agent(llm=RuleBasedLLM(), tools=registry, max_steps=4)
    result = agent.run("请统计这句话的字数：把不确定性关进循环，把循环关进预算")

    print(result.trace.tree())
    print(f"\n[stop={result.stopped_reason}] tokens={result.usage.total}")
    print(result.answer)


if __name__ == "__main__":
    main()
