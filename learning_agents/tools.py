"""工具层：把普通 Python 函数暴露给模型，并把错误变成"观察"。

三条工程原则
------------
1. **schema 即契约**：名字、描述、参数类型都进 schema；模型只能填参数，
   不能发明参数。校验失败要返回结构化错误，而不是抛异常中断循环。
2. **错误即观察**：工具抛错时不吞掉、也不炸掉整个 Agent，而是把错误文本
   交给模型，让它有机会换参数或换工具重试。
3. **副作用显式声明**：``side_effect=True`` 的工具应当被审批门（见
   guardrails）或幂等键保护，这是 HITL 的接入点。
"""

from __future__ import annotations

import inspect
import json
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from .llm import ToolCall

_JSON_TYPES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., Any]
    side_effect: bool = False
    idempotent: bool = True
    max_output_chars: int = 4000

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolResult:
    call_id: str
    name: str
    ok: bool
    output: str
    error: str = ""
    duration_ms: float = 0.0
    truncated: bool = False

    def to_message(self) -> dict[str, Any]:
        body = self.output if self.ok else f"ERROR: {self.error}"
        return {"role": "tool", "tool_call_id": self.call_id, "name": self.name,
                "content": body}


class ToolError(RuntimeError):
    """工具执行失败。保留类型信息，便于上层区分可重试与不可重试。"""


# --------------------------------------------------------------------------- 装饰器
def tool(
    _func: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    side_effect: bool = False,
    idempotent: bool = True,
) -> Callable[..., Any]:
    """把函数登记为工具。既可 ``@tool``，也可 ``@tool(side_effect=True)``。"""

    def wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
        spec = build_spec(fn, name=name, description=description,
                          side_effect=side_effect, idempotent=idempotent)
        fn.__tool_spec__ = spec  # type: ignore[attr-defined]
        return fn

    return wrap(_func) if _func is not None else wrap


def build_spec(
    fn: Callable[..., Any],
    *,
    name: str | None = None,
    description: str | None = None,
    side_effect: bool = False,
    idempotent: bool = True,
) -> ToolSpec:
    sig = inspect.signature(fn)
    doc = inspect.getdoc(fn) or ""
    doc_lines = [line.strip() for line in doc.splitlines() if line.strip()]
    summary = description or (doc_lines[0] if doc_lines else fn.__name__)

    properties: dict[str, Any] = {}
    required: list[str] = []
    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue
        ann = param.annotation
        py_type = _resolve_type(ann)
        schema: dict[str, Any] = {"type": _JSON_TYPES.get(py_type, "string")}
        if len(doc_lines) > 1:
            for line in doc_lines[1:]:
                if line.startswith(f"{param_name}:") or line.startswith(f"{param_name}："):
                    schema["description"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
                    break
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
        else:
            schema["default"] = param.default
        properties[param_name] = schema

    parameters = {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }
    return ToolSpec(
        name=name or fn.__name__,
        description=summary,
        parameters=parameters,
        func=fn,
        side_effect=side_effect,
        idempotent=idempotent,
    )


def _resolve_type(ann: Any) -> type:
    if ann is inspect.Parameter.empty:
        return str
    if isinstance(ann, str):
        return {"int": int, "float": float, "bool": bool, "list": list, "dict": dict}.get(ann, str)
    return ann if isinstance(ann, type) else str


# --------------------------------------------------------------------------- 注册表
class ToolRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self.hook: Callable[[ToolSpec, dict[str, Any]], None] | None = None

    # ------------------------------------------------------------------ 注册
    def register(self, fn: Callable[..., Any]) -> ToolSpec:
        spec = getattr(fn, "__tool_spec__", None) or build_spec(fn)
        if spec.name in self._specs:
            raise ValueError(f"工具重名：{spec.name}")
        self._specs[spec.name] = spec
        return spec

    def register_all(self, fns: Iterable[Callable[..., Any]]) -> "ToolRegistry":
        for fn in fns:
            self.register(fn)
        return self

    def __contains__(self, name: str) -> bool:
        return name in self._specs

    def __len__(self) -> int:
        return len(self._specs)

    def get(self, name: str) -> ToolSpec:
        if name not in self._specs:
            raise ToolError(f"未知工具：{name}；可用工具：{sorted(self._specs)}")
        return self._specs[name]

    def schemas(self) -> list[dict[str, Any]]:
        return [spec.openai_schema() for spec in self._specs.values()]

    def describe(self) -> str:
        return "\n".join(f"- {s.name}: {s.description}" for s in self._specs.values())

    # ------------------------------------------------------------------ 执行
    def execute(self, call: ToolCall) -> ToolResult:
        started = time.perf_counter()
        try:
            spec = self.get(call.name)
            args = validate_arguments(spec.parameters, call.arguments)
            if self.hook is not None:
                self.hook(spec, args)
            raw = spec.func(**args)
            text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False, default=str)
            truncated = len(text) > spec.max_output_chars
            if truncated:
                text = text[: spec.max_output_chars] + "…[输出已截断]"
            return ToolResult(
                call_id=call.id, name=call.name, ok=True, output=text,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
                truncated=truncated,
            )
        except Exception as exc:  # noqa: BLE001 —— 故意兜底：错误是数据，不是崩溃
            detail = f"{type(exc).__name__}: {exc}"
            if not isinstance(exc, (ToolError, ValueError, TypeError, KeyError)):
                detail += "\n" + traceback.format_exc(limit=2)
            return ToolResult(
                call_id=call.id, name=call.name, ok=False, output="",
                error=detail, duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )


def validate_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    """轻量校验：必填、类型、未知字段。真实项目可换 pydantic/jsonschema。"""
    props: dict[str, Any] = schema.get("properties", {})
    required: list[str] = schema.get("required", [])
    missing = [k for k in required if k not in arguments]
    if missing:
        raise ToolError(f"缺少必填参数：{missing}")
    clean: dict[str, Any] = {}
    for key, value in arguments.items():
        if key not in props:
            raise ToolError(f"未声明的参数：{key}；允许的参数：{sorted(props)}")
        expected = props[key].get("type", "string")
        if not _type_ok(expected, value):
            raise ToolError(f"参数 {key} 应为 {expected}，实际为 {type(value).__name__}")
        clean[key] = value
    return clean


def _type_ok(expected: str, value: Any) -> bool:
    return {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, (list, tuple)),
        "object": isinstance(value, dict),
    }.get(expected, True)


def parallel_execute(registry: ToolRegistry, calls: Sequence[ToolCall]) -> list[ToolResult]:
    """模型一次返回多个工具调用时并行执行；顺序保持与请求一致。"""
    if len(calls) <= 1:
        return [registry.execute(c) for c in calls]
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(4, len(calls))) as pool:
        return list(pool.map(registry.execute, calls))
