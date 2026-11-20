"""可执行的演示集：不联网、不需要 API Key，直接看控制流。

    python -m learning_agents.demo            # 全部跑一遍
    python -m learning_agents.demo rag        # 只跑某个场景

每个场景都会打印结构化轨迹，便于对照文档里的流程图。
"""

from __future__ import annotations

import ast
import operator
import sys
import tempfile
from pathlib import Path
from typing import Any

from .agent import Agent
from .evaluation import EvalCase, TraceEvaluator, format_table
from .guardrails import ApprovalGate, Budget
from .llm import LLMResponse, RuleBasedLLM, ScriptedLLM, ToolCall, Usage
from .memory import BufferMemory, EpisodicStore, MemoryManager, VectorMemory
from .multiagent import AgentBase, Debate, Pipeline, Supervisor
from .planning import Plan, PlanAndExecute, PlanStep, Router, TaskGraph, Planner
from .rag import RAGPipeline
from .reflection import HeuristicCritic, ReflectionLoop
from .tools import ToolRegistry, tool
from .trace import Tracer

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "corpus"


# --------------------------------------------------------------------------- 工具
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
        ast.USub: operator.neg}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("表达式包含不允许的语法")


@tool
def calculator(expression: str) -> str:
    """计算四则运算表达式  expression: 仅含数字与 + - * / ( ) 的表达式"""
    tree = ast.parse(expression, mode="eval")
    value = _eval_node(tree.body)
    return f"{expression} = {value:g}"


@tool
def lookup_faq(topic: str) -> str:
    """查询内部知识库中的常见问题，topic: 主题关键词"""
    db = {
        "退款": "退款需在签收后 7 天内申请，原路退回，3-5 个工作日到账。",
        "发票": "电子发票在订单完成后 24 小时内开具，可在订单页下载。",
        "物流": "默认顺丰，偏远地区转邮政，发货后 48 小时内有轨迹。",
    }
    for key, value in db.items():
        if key in topic:
            return value
    return f"知识库未收录「{topic}」，建议转人工。"


@tool(side_effect=True, idempotent=False)
def send_notice(channel: str, message: str) -> str:
    """向指定渠道发送通知（有副作用，需要人工审批）  channel: 渠道名  message: 内容"""
    return f"已向 {channel} 发送：{message}"


# --------------------------------------------------------------------------- 场景 1
def demo_basic() -> None:
    print("\n=== 场景 1 · 最小闭环：思考 -> 工具 -> 观察 -> 答复 ===")
    registry = ToolRegistry().register_all([calculator])
    agent = Agent(llm=RuleBasedLLM(), tools=registry, max_steps=4)
    result = agent.run("请帮我计算 (128*7+36)/4 的结果")
    print(result.trace.tree())
    print(f"\n[stop={result.stopped_reason}] {result.answer[:200]}")


# --------------------------------------------------------------------------- 场景 2
def demo_react() -> None:
    print("\n=== 场景 2 · 两步推理：先算单价，再算总价（脚本模型，可复现）===")
    script = [
        LLMResponse(tool_calls=[ToolCall("c1", "calculator",
                                         {"expression": "128*7+36"})],
                    usage=Usage(120, 20)),
        LLMResponse(tool_calls=[ToolCall("c2", "calculator",
                                         {"expression": "932/4"})],
                    usage=Usage(180, 24)),
        LLMResponse(text="总价为 233。第一步算出小计 932，第二步除以 4 得到单价。",
                    usage=Usage(210, 30)),
    ]
    registry = ToolRegistry().register_all([calculator])
    agent = Agent(llm=ScriptedLLM(script), tools=registry, max_steps=5)
    result = agent.run("四件装总价按公式 128*7+36 计算，求单件价格")
    for ev in result.trace.events:
        if ev.kind in ("tool.call", "llm.response"):
            print(f"  [{ev.seq:02d}] {ev.kind:<12} {ev.data.get('tool_calls') or ev.data.get('output_head', '')}")
    print(f"\n[stop={result.stopped_reason}] {result.answer}")


# --------------------------------------------------------------------------- 场景 3
def demo_guardrails() -> None:
    print("\n=== 场景 3 · 审批门：副作用工具默认拒绝 ===")
    registry = ToolRegistry().register_all([send_notice])
    registry.hook = ApprovalGate(approver=lambda req: "退款" in str(req.arguments)).hook

    def script(channel: str, message: str) -> ScriptedLLM:
        return ScriptedLLM([
            LLMResponse(tool_calls=[ToolCall("c1", "send_notice",
                                             {"channel": channel, "message": message})],
                        usage=Usage(90, 16)),
            LLMResponse(text="通知已发出，流程结束。", usage=Usage(120, 12)),
        ])

    agent = Agent(llm=script("短信", "您的退款已受理，3 个工作日内到账"), tools=registry,
                  max_steps=3, budget=Budget(max_tokens=5000))
    allowed = agent.run("通知客户退款进度")
    denied = Agent(llm=script("短信", "双十一大促开始啦"), tools=registry, max_steps=3,
                   budget=Budget(max_tokens=5000)).run("通知客户营销活动")
    print(f"审批通过 -> {allowed.stopped_reason}：{allowed.answer}")
    err = next(m["content"] for m in denied.messages if m.get("role") == "tool")
    print(f"审批拒绝 -> 观察回灌：{err[:70]}…")


# --------------------------------------------------------------------------- 场景 4
def demo_memory() -> None:
    print("\n=== 场景 4 · 三层记忆：工作 / 语义 / 情景 ===")
    with tempfile.TemporaryDirectory() as tmp:
        store = EpisodicStore(Path(tmp) / "episodes.jsonl")
        store.append("统计上季度退货率", "退货率 3.2%，低于阈值 5%", ["sql"], True)
        manager = MemoryManager(buffer=BufferMemory(max_turns=2),
                                semantic=VectorMemory(),
                                episodic=store, token_budget=600)
        manager.observe("user", "我们上季度的退货率是多少？")
        manager.observe("assistant", "3.2%，来源：订单表按月聚合。")
        manager.remember("门店 A 的退货率连续两季高于均值", importance=0.8)
        manager.remember("用户偏好简洁的回答", importance=0.7)
        manager.remember("临时闲聊内容", importance=0.2)
        print(manager.build_context("退货率 门店 A 的对比", k=2))


# --------------------------------------------------------------------------- 场景 5
def demo_rag() -> None:
    print("\n=== 场景 5 · RAG：混合检索 + 引用 ===")
    docs = {p.stem: p.read_text(encoding="utf-8") for p in sorted(CORPUS_DIR.glob("*.md"))}
    pipeline = RAGPipeline().index(docs, size=220, overlap=40)
    query = "记忆写入为什么昂贵？"
    result = pipeline.answer(query, k=3)
    for i, cite in enumerate(result["citations"], 1):
        print(f"  [{i}] {cite['id']}  score={cite['score']}")
    print(f"\n答案：{result['answer']}")
    print(f"引用覆盖率：{result['coverage']}")


# --------------------------------------------------------------------------- 场景 6
def demo_plan() -> None:
    print("\n=== 场景 6 · 计划执行 + 失败重规划 ===")
    planner = Planner()
    plan = planner.from_template(
        ["确认数据口径", "拉取明细数据", "生成汇总报告"],
        tools=["spec_lookup", "sql_query", ""],
    )
    attempts: dict[str, int] = {}

    def executor(step: PlanStep) -> str:
        attempts[step.id] = attempts.get(step.id, 0) + 1
        if step.id == "s2" and attempts[step.id] == 1:
            raise TimeoutError("数仓查询超时（30s）")
        if step.id == "s2":
            return "已改为抽样查询并缓存，得到 1.2 万行"
        return f"完成：{step.goal}"

    def replanner(old: Plan, failed: PlanStep, error: str) -> Plan:
        print(f"  ↻ 重规划：{failed.id} 失败（{error}），插入降级步骤")
        steps = old.steps
        failed.goal = "降级：抽样 + 缓存"
        failed.status = "pending"
        return Plan(steps)

    runner = PlanAndExecute(executor=executor, replanner=replanner)
    done = runner.run(plan)
    print(done.describe())
    for row in runner.history:
        print(f"  {row['step']} {row['status']:<8} {row['result'][:60]}")


# --------------------------------------------------------------------------- 场景 7
def demo_reflection() -> None:
    print("\n=== 场景 7 · 反思循环：评审 -> 修订 -> 再评审 ===")
    critic = HeuristicCritic({
        "min_chars": 120,
        "require_citation": True,
        "required_terms": ["重规划", "上限"],
        "banned_phrases": ["众所周知"],
    })

    def generate(task: str) -> str:
        return "智能体需要规划能力。规划就是把目标拆成步骤。"

    def revise(draft: str, critique_) -> str:
        if "重规划" not in draft:
            draft += " 重规划必须有上限，否则会在失败路径上无限循环。"
        if "[" not in draft:
            draft += " 参考：[1] 工程实践笔记。"
        if len(draft) < 120:
            draft += (" 工程上通常同时设置步数上限与时间上限，并在轨迹里记录每次"
                      "重规划的原因，便于事后定位是模型选错了工具，还是工具本身不稳定。")
        return draft

    loop = ReflectionLoop(generate, revise, critic, max_rounds=3)
    out = loop.run("如何避免智能体在失败路径上失控？")
    for row in out["history"]:
        print(f"  round {row['round']}: score={row['score']} issues={row['issues']}")
    print(f"\n通过={out['passed']} 轮数={out['rounds']}\n{out['final'][:160]}")


# --------------------------------------------------------------------------- 场景 8
def demo_multiagent() -> None:
    print("\n=== 场景 8 · 多智能体：主管分派 + 正反辩论 ===")
    workers = [
        AgentBase("研究员", lambda task, ctx: f"调研要点：{task[:18]}…（3 条来源）"),
        AgentBase("撰稿人", lambda task, ctx: f"成稿：围绕「{task[:12]}」给出 500 字结构稿"),
        AgentBase("审校", lambda task, ctx: f"审校意见：术语一致，补充 1 处引用"),
    ]
    supervisor = Supervisor(workers, plan=lambda t: ["梳理事实", "撰写初稿", "审校定稿"],
                            assign=lambda sub: {"梳": "研究员", "撰": "撰稿人",
                                                "审": "审校"}.get(sub[0], "撰稿人"))
    result = supervisor.run("写一篇关于智能体评估的短文")
    for sender, recipient, content in [(m.sender, m.recipient, m.content)
                                       for m in result["transcript"]]:
        print(f"  {sender:>10} -> {recipient:<8} {content[:48]}")

    debate = Debate(
        proposer=lambda topic, critique: "应当优先做评估基建：没有度量就没有迭代。",
        critic=lambda topic, prop: "反对：过早建设评估会拖慢探索，先用人工抽检。",
        judge=lambda topic, texts: "先建最小断言集（工具/步数/预算），再逐步扩充 rubric。",
        rounds=1,
    )
    verdict = debate.run("团队应当先做评估还是先做功能？")
    print(f"\n  裁决：{verdict['decision']}")


# --------------------------------------------------------------------------- 场景 9
def demo_pipelines() -> None:
    print("\n=== 场景 9 · 编排：流水线、路由、任务图 ===")
    pipe = Pipeline([
        ("抽取", lambda t: f"要点：{t}"),
        ("扩写", lambda t: t + " -> 扩写为 200 字"),
        ("校对", lambda t: t + "（已校对）"),
    ])
    print("  流水线:", pipe.run("季度复盘")["output"])

    router = Router({"billing": ["退款", "发票"], "tech": ["报错", "超时"]})
    print("  路由:", {q: router.decide(q) for q in ["我要退款", "接口超时", "随便聊聊"]})

    graph = TaskGraph()
    graph.add("抓取", lambda: ["doc1", "doc2"])
    graph.add("抽取1", lambda 抓取: len(抓取), deps=["抓取"])
    graph.add("抽取2", lambda **_: "摘要", deps=["抓取"])
    graph.add("汇总", lambda 抽取1, 抽取2: f"{抽取1} 篇 + {抽取2}", deps=["抽取1", "抽取2"])
    print("  分层:", graph.layers())
    print("  结果:", graph.run()["汇总"])


# --------------------------------------------------------------------------- 场景 10
def demo_eval() -> None:
    print("\n=== 场景 10 · 评估：断言 + 指标 ===")
    registry = ToolRegistry().register_all([calculator, lookup_faq])
    agent = Agent(llm=RuleBasedLLM(), tools=registry, max_steps=4)
    runs = {
        "calc": agent.run("请计算 (128*7+36)/4"),
        "faq": agent.run("客户问退款政策，请查询知识库"),
    }
    cases = [
        EvalCase("calc", "请计算 (128*7+36)/4", expected_terms=["233"],
                 required_tools=["calculator"], max_steps=4),
        EvalCase("faq", "客户问退款政策，请查询知识库", expected_terms=["7 天"],
                 required_tools=["lookup_faq"], max_steps=4),
    ]
    report = TraceEvaluator(cases).run_suite(runs)
    print(format_table(report))


SCENARIOS = {
    "basic": demo_basic,
    "react": demo_react,
    "guardrails": demo_guardrails,
    "memory": demo_memory,
    "rag": demo_rag,
    "plan": demo_plan,
    "reflection": demo_reflection,
    "multiagent": demo_multiagent,
    "pipelines": demo_pipelines,
    "eval": demo_eval,
}


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    names = argv or list(SCENARIOS)
    if names == ["all"]:
        names = list(SCENARIOS)
    unknown = [n for n in names if n not in SCENARIOS]
    if unknown:
        print(f"未知场景：{unknown}\n可用：{list(SCENARIOS)}")
        return 2
    for name in names:
        SCENARIOS[name]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
