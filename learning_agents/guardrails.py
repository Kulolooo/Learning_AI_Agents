"""护栏：预算、审批、白名单、输出校验。

护栏不是"限制能力"，而是把不可逆的风险变成可观测、可中断的控制点。
四个组件彼此独立，按需组合：

* ``Budget``       —— token / 时间 / 工具调用次数三条硬上限。
* ``ApprovalGate`` —— 副作用工具执行前的人工确认（HITL）。
* ``Allowlist``    —— 文件、网络、命令的作用域约束。
* ``validate_json``—— 结构化输出的最小 schema 校验。
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .llm import Usage
from .tools import ToolSpec


class ApprovalDenied(RuntimeError):
    """审批被拒绝；Agent 应把它当作观察结果，而不是崩溃。"""


# --------------------------------------------------------------------------- 预算
@dataclass
class Budget:
    max_tokens: int = 60_000
    max_seconds: float = 300.0
    max_tool_calls: int = 40
    started_at: float = field(default_factory=time.perf_counter)
    tool_calls: int = 0

    def exceeded(self, usage: Usage) -> bool:
        return (
            usage.total >= self.max_tokens
            or self.tool_calls >= self.max_tool_calls
            or (time.perf_counter() - self.started_at) >= self.max_seconds
        )

    def charge_tool(self) -> None:
        self.tool_calls += 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "max_tool_calls": self.max_tool_calls,
            "max_seconds": self.max_seconds,
            "elapsed": round(time.perf_counter() - self.started_at, 2),
            "tool_calls": self.tool_calls,
        }


# --------------------------------------------------------------------------- 审批
@dataclass
class ApprovalRequest:
    tool: str
    arguments: dict[str, Any]
    reason: str = "该工具可能产生不可逆副作用"


class ApprovalGate:
    """副作用工具的人工审批门。

    ``approver`` 返回 True 放行，False 拒绝。默认实现直接拒绝——安全的默认值
    必须是"不做"，而不是"默默做了"。
    """

    def __init__(self, approver: Callable[[ApprovalRequest], bool] | None = None,
                 require_for: Iterable[str] | None = None) -> None:
        self.approver = approver or (lambda req: False)
        self.require_for = set(require_for) if require_for else None
        self.log: list[tuple[ApprovalRequest, bool]] = []

    def hook(self, spec: ToolSpec, arguments: dict[str, Any]) -> None:
        if not spec.side_effect:
            return
        if self.require_for is not None and spec.name not in self.require_for:
            return
        request = ApprovalRequest(tool=spec.name, arguments=arguments)
        decision = bool(self.approver(request))
        self.log.append((request, decision))
        if not decision:
            raise ApprovalDenied(f"审批未通过：{spec.name} {arguments}")


# --------------------------------------------------------------------------- 白名单
class Allowlist:
    """作用域约束：只允许访问列举内的资源。支持前缀匹配。"""

    def __init__(self, allowed: Iterable[str], kind: str = "path") -> None:
        self.allowed = [item.rstrip("/\\") for item in allowed]
        self.kind = kind

    def check(self, value: str) -> str:
        normalized = value.replace("\\", "/")
        for prefix in (item.replace("\\", "/") for item in self.allowed):
            if normalized == prefix or normalized.startswith(prefix + "/"):
                return value
        raise PermissionError(f"{self.kind} 不在白名单内：{value}")


# --------------------------------------------------------------------------- 校验
def validate_json(text: str, schema: dict[str, Any]) -> dict[str, Any]:
    """最小 JSON schema 校验：type / required / properties / enum。

    够用于"模型必须返回结构化字段"的场景；复杂约束请换 jsonschema。
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"不是合法 JSON：{exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("顶层必须是 JSON 对象")
    for key in schema.get("required", []):
        if key not in data:
            raise ValueError(f"缺少字段：{key}")
    for key, rule in schema.get("properties", {}).items():
        if key not in data:
            continue
        expected = rule.get("type")
        if expected and not _type_ok(expected, data[key]):
            raise ValueError(f"字段 {key} 类型应为 {expected}")
        if "enum" in rule and data[key] not in rule["enum"]:
            raise ValueError(f"字段 {key} 必须是 {rule['enum']} 之一")
    return data


def _type_ok(expected: str, value: Any) -> bool:
    return {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
    }.get(expected, True)


# --------------------------------------------------------------------------- 幂等
def idempotency_key(tool: str, arguments: dict[str, Any]) -> str:
    """同一工具 + 同一参数 => 同一键；用于副作用去重。"""
    payload = json.dumps({"tool": tool, "arguments": arguments}, sort_keys=True,
                         ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
