"""例 5：计划执行 + 反思。运行：``python examples/05_plan_reflect.py``

看点：失败触发的重规划有次数上限；反思循环有回退，不会越改越差。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from learning_agents.planning import Plan, PlanAndExecute, PlanStep, Planner
from learning_agents.reflection import HeuristicCritic, ReflectionLoop


def plan_demo() -> None:
    plan = Planner().from_template(
        ["读取订单表", "计算退货率", "生成结论"],
        tools=["sql_query", "python", ""],
    )
    state = {"tries": 0}

    def executor(step: PlanStep) -> str:
        if step.id == "s1":
            state["tries"] += 1
            if state["tries"] == 1:
                raise ConnectionError("数仓连接超时")
            return "已改为读取本地快照，得到 1.2 万行"
        return f"完成：{step.goal}"

    def replanner(old: Plan, failed: PlanStep, error: str) -> Plan:
        print(f"  ↻ {failed.id} 失败（{error}），切换数据源后重试")
        failed.status = "pending"
        failed.tool = "local_snapshot"
        return old

    result = PlanAndExecute(executor, replanner, max_replans=1).run(plan)
    print(result.describe())


def reflect_demo() -> None:
    critic = HeuristicCritic({"min_chars": 40, "require_citation": True,
                              "required_terms": ["上限"]})

    def revise(draft: str, critique) -> str:
        if "[" not in draft:
            draft += " 参考：[1] 工程笔记。"
        if "上限" not in draft:
            draft += " 必须给重规划设置次数上限，否则失败路径会被反复重写。"
        return draft

    loop = ReflectionLoop(lambda task: "规划要有边界。", revise, critic, max_rounds=3)
    out = loop.run("如何避免重规划失控？")
    for row in out["history"]:
        print(f"  round {row['round']}: score={row['score']} issues={row['issues']}")
    print(f"  passed={out['passed']} final={out['final'][:60]}…")


if __name__ == "__main__":
    print("== 计划执行 ==")
    plan_demo()
    print("\n== 反思循环 ==")
    reflect_demo()
