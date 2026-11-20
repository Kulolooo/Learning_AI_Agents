"""Learning_AI_Agents：从零实现的最小智能体工具箱。

模块地图
--------
================  ==================================================
模块              职责
================  ==================================================
``llm``           模型适配（脚本 / 规则 / OpenAI 兼容）
``trace``         结构化轨迹与 JSONL 落盘
``tools``         工具 schema、注册表、校验、并行执行
``agent``         主循环（ReAct 式）
``memory``        工作 / 情景 / 语义记忆
``rag``           切分、BM25、向量、RRF、引用
``planning``      路由、计划执行、任务图
``reflection``    反思循环、自愈代码、自一致性
``multiagent``    流水线、主管、辩论、黑板
``evaluation``    断言、指标、rubric、pass@k
``guardrails``    预算、审批、白名单、结构化校验
================  ==================================================
"""

from .agent import Agent, AgentResult, run_task
from .guardrails import ApprovalGate, Budget, validate_json
from .llm import (LLM, LLMResponse, OpenAICompatLLM, RuleBasedLLM, ScriptedLLM,
                  ToolCall, Usage)
from .tools import ToolRegistry, tool

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "AgentResult",
    "run_task",
    "ApprovalGate",
    "Budget",
    "validate_json",
    "LLM",
    "LLMResponse",
    "OpenAICompatLLM",
    "RuleBasedLLM",
    "ScriptedLLM",
    "ToolCall",
    "Usage",
    "ToolRegistry",
    "tool",
]
