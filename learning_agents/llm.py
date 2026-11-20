"""模型适配层。

把"模型"抽象成一次 ``complete(messages, tools) -> LLMResponse`` 调用，
上层 Agent 不关心背后是脚本、规则引擎还是远端 API。三档实现：

* ``ScriptedLLM``   —— 按脚本逐条返回，用来写可复现的测试。
* ``RuleBasedLLM``  —— 极小的规则引擎，让示例在完全离线时也能跑通闭环。
* ``OpenAICompatLLM`` —— 任何兼容 /chat/completions 的服务（OpenAI、vLLM、
  Ollama、以及绝大多数国内厂商的兼容端点）。

刻意不做的事：不做自动重试的"魔法"、不隐式截断上下文。重试策略与预算
控制放在调用方（见 guardrails.Budget），这样行为可观测、可测试。
"""

from __future__ import annotations

import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Sequence

Message = dict[str, Any]


# --------------------------------------------------------------------------- 数据结构
@dataclass
class ToolCall:
    """模型请求的一次工具调用。"""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
        )


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    model: str = "scripted"
    latency_ms: float = 0.0

    @property
    def is_tool_call(self) -> bool:
        return bool(self.tool_calls)


class LLM(Protocol):
    def complete(
        self,
        messages: Sequence[Message],
        tools: Sequence[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse: ...


# --------------------------------------------------------------------------- 工具函数
def estimate_tokens(text: str) -> int:
    """粗略 token 估算：CJK 字符按 1 token，其余按 4 字符 1 token。

    只用于预算与截断判断，不追求与真实分词器一致。
    """
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return cjk + max((len(text) - cjk) // 4, 1)


def messages_tokens(messages: Sequence[Message]) -> int:
    total = 0
    for m in messages:
        total += 4 + estimate_tokens(str(m.get("content", "")))
        for tc in m.get("tool_calls", []) or []:
            total += estimate_tokens(json.dumps(tc, ensure_ascii=False))
    return total


# --------------------------------------------------------------------------- 脚本模型
class ScriptExhausted(RuntimeError):
    """脚本模型被调用次数超过预设，通常意味着 Agent 陷入死循环。"""


class ScriptedLLM:
    """按顺序返回预设响应；支持用函数动态生成，便于断言中间状态。"""

    def __init__(self, script: Sequence[LLMResponse | Callable[[Sequence[Message]], LLMResponse]],
                 model: str = "scripted") -> None:
        self._script = list(script)
        self._cursor = 0
        self.model = model
        self.calls: list[list[Message]] = []

    def complete(self, messages, tools=None, **kwargs) -> LLMResponse:  # noqa: D401
        self.calls.append(list(messages))
        if self._cursor >= len(self._script):
            raise ScriptExhausted(f"脚本已耗尽（第 {self._cursor + 1} 次调用）")
        item = self._script[self._cursor]
        self._cursor += 1
        resp = item(messages) if callable(item) else item
        resp.model = self.model
        return resp


# --------------------------------------------------------------------------- 规则模型
class RuleBasedLLM:
    """离线规则引擎。

    它只做三件事，足以演示完整闭环：

    1. 有工具且任务命中工具名/描述里的关键词 -> 发一次工具调用；
    2. 上一条消息是工具结果 -> 把结果整理成最终答复；
    3. 其余情况 -> 直接回答。

    这是教学占位实现，不代表任何真实模型的能力边界。
    """

    def __init__(self, model: str = "rule-based") -> None:
        self.model = model

    def complete(self, messages, tools=None, **kwargs) -> LLMResponse:
        last = messages[-1]
        role = last.get("role")

        if role == "tool":
            observed = str(last.get("content", ""))
            question = _first_user(messages)
            text = (
                f"根据工具返回的结果，关于「{question}」的答复如下：\n"
                f"{observed.strip()}\n"
                "（本条由离线规则模型生成，用于演示控制流；接入真实模型后语义能力由模型决定。）"
            )
            return LLMResponse(text=text, model=self.model,
                               usage=Usage(messages_tokens(messages), estimate_tokens(text)))

        question = _first_user(messages)
        if tools:
            picked = _match_tool(question, tools)
            if picked is not None and not _already_called(messages, picked["function"]["name"]):
                name = picked["function"]["name"]
                args = _guess_args(question, picked)
                return LLMResponse(
                    tool_calls=[ToolCall(id=f"call_{name}", name=name, arguments=args)],
                    model=self.model,
                    usage=Usage(messages_tokens(messages), 12),
                )

        text = (
            f"（离线演示）已收到任务：「{question}」。\n"
            "当前没有可用的外部工具，因此直接给出结论：这是一次未调用工具的直答。"
        )
        return LLMResponse(text=text, model=self.model,
                           usage=Usage(messages_tokens(messages), estimate_tokens(text)))


def _first_user(messages: Sequence[Message]) -> str:
    for m in messages:
        if m.get("role") == "user":
            return str(m.get("content", ""))
    return ""


def _already_called(messages: Sequence[Message], name: str) -> bool:
    return any(m.get("role") == "tool" and m.get("name") == name for m in messages)


def _match_tool(question: str, tools: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    """用字符二元组做粗糙的语义匹配：中文没有空格，按 bigram 重叠更稳。"""
    q_grams = _bigrams(question)
    best, best_score = None, 0
    for spec in tools:
        fn = spec.get("function", {})
        name = str(fn.get("name", ""))
        desc = str(fn.get("description", ""))
        score = len(_bigrams(desc) & q_grams)
        if name and name.lower() in question.lower():
            score += 3
        if score > best_score:
            best, best_score = spec, score
    return best if best_score >= 1 else None


def _bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text)
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


_EXPR = re.compile(r"[-+*/()0-9.\s]{5,}")


def _guess_args(question: str, spec: dict[str, Any]) -> dict[str, Any]:
    """把自然语言里最像参数的一段塞进去：够用即可，真实模型由 schema 约束。"""
    params = spec.get("function", {}).get("parameters", {})
    props: dict[str, Any] = params.get("properties", {})
    args: dict[str, Any] = {}
    for name, schema in props.items():
        if name in ("expression", "expr", "formula"):
            match = _EXPR.search(question)
            args[name] = match.group().strip() if match else question
        elif schema.get("type") == "integer":
            digits = "".join(ch for ch in question if ch.isdigit())
            args[name] = int(digits[:3]) if digits else 3
        elif schema.get("type") == "number":
            args[name] = 1.0
        elif schema.get("type") == "boolean":
            args[name] = True
        else:
            args[name] = question
    return args


# --------------------------------------------------------------------------- 远端模型
class LLMError(RuntimeError):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class OpenAICompatLLM:
    """兼容 OpenAI Chat Completions 的最小客户端（仅标准库）。

    环境变量：``OPENAI_API_KEY``、``OPENAI_BASE_URL``（默认官方地址）、
    ``OPENAI_MODEL``。超时与重试都显式暴露，便于在本地网关下调参。
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        temperature: float = 0.2,
    ) -> None:
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL",
                                                    "https://api.openai.com/v1")).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature

    def complete(self, messages, tools=None, **kwargs) -> LLMResponse:
        if not self.api_key:
            raise LLMError("缺少 OPENAI_API_KEY；离线场景请改用 ScriptedLLM 或 RuleBasedLLM")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "temperature": kwargs.get("temperature", self.temperature),
        }
        if tools:
            payload["tools"] = list(tools)
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]

        started = time.perf_counter()
        raw = self._post("/chat/completions", payload)
        latency = (time.perf_counter() - started) * 1000
        choice = raw["choices"][0]["message"]
        calls = [
            ToolCall(
                id=tc.get("id", f"call_{i}"),
                name=tc["function"]["name"],
                arguments=_loads(tc["function"].get("arguments", "{}")),
            )
            for i, tc in enumerate(choice.get("tool_calls") or [])
        ]
        usage = raw.get("usage", {})
        return LLMResponse(
            text=choice.get("content") or "",
            tool_calls=calls,
            usage=Usage(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)),
            model=raw.get("model", self.model),
            latency_ms=round(latency, 2),
        )

    # ------------------------------------------------------------------ 传输层
    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(
                self.base_url + path,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:  # 429 / 5xx 才重试
                detail = exc.read().decode("utf-8", "ignore")[:400]
                last_error = LLMError(f"HTTP {exc.code}: {detail}", exc.code)
                if exc.code not in (408, 409, 429) and exc.code < 500:
                    raise last_error from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = LLMError(f"网络错误: {exc}")
            if attempt < self.max_retries:
                time.sleep(min(2 ** attempt * 0.5 + random.random() * 0.2, 8))
        raise last_error or LLMError("未知错误")


def _loads(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {"value": value}
    except json.JSONDecodeError:
        return {"_raw": text}
