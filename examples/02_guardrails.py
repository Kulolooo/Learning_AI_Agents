"""例 2：工具校验 + 审批门。运行：``python examples/02_guardrails.py``

看点：参数错误不会终止循环，审批拒绝也只是"又一个观察"。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from learning_agents.guardrails import ApprovalGate, Budget
from learning_agents.llm import LLMResponse, ScriptedLLM, ToolCall, Usage
from learning_agents.agent import Agent
from learning_agents.tools import ToolRegistry, tool


@tool(side_effect=True, idempotent=False)
def transfer(account: str, amount: int) -> str:
    """向账户转账（不可逆）  account: 账户  amount: 金额（元）"""
    return f"已向 {account} 转账 {amount} 元"


def main() -> None:
    registry = ToolRegistry().register_all([transfer])
    registry.hook = ApprovalGate(approver=lambda req: req.arguments.get("amount", 0) <= 500).hook

    def run(amount: int) -> None:
        script = ScriptedLLM([
            LLMResponse(tool_calls=[ToolCall(f"c{amount}", "transfer",
                                             {"account": "A-1001", "amount": amount})],
                        usage=Usage(80, 12)),
            LLMResponse(text="已按流程处理。", usage=Usage(120, 10)),
        ])
        result = Agent(llm=script, tools=registry, max_steps=3,
                       budget=Budget(max_tokens=4000)).run(f"转账 {amount} 元给 A-1001")
        obs = [m["content"] for m in result.messages if m.get("role") == "tool"]
        print(f"金额 {amount:>5} -> stop={result.stopped_reason:<8} 观察={obs[0][:48]}")

    # 参数错误：金额传成字符串，校验层拦截
    bad = registry.execute(ToolCall("x", "transfer", {"account": "A-1001", "amount": "500"}))
    print(f"类型错误 -> ok={bad.ok} error={bad.error[:40]}")

    run(300)    # 审批通过
    run(800)    # 审批拒绝


if __name__ == "__main__":
    main()
