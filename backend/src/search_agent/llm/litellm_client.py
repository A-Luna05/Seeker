from __future__ import annotations

from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

try:
    from litellm import acompletion
except ImportError as e:  # pragma: no cover
    raise ImportError("litellm is required") from e


def normalize_litellm_model(model: str) -> str:
    """LiteLLM needs a provider prefix (e.g. ``openai/gpt-4o-mini``). Bare names default to OpenAI."""
    m = (model or "").strip()
    if not m:
        return m
    if "/" in m:
        prefix, sep, body = m.partition("/")
        prefix = f"{prefix}{sep}"  # "openai/"
    else:
        prefix = "openai/"
        body = m
    # Common typo for OpenAI GPT-4.1 family
    if body.startswith("gpt-4_1"):
        body = "gpt-4.1" + body[7:]
    return prefix + body


def _to_openai_messages(messages: Sequence[BaseMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            role = "user"
        elif isinstance(m, AIMessage):
            role = "assistant"
        elif isinstance(m, SystemMessage):
            role = "system"
        else:
            role = "user"
        content = m.content
        if not isinstance(content, str):
            content = str(content)
        out.append({"role": role, "content": content})
    return out


class LiteLLMClient:
    def __init__(self, default_model: str) -> None:
        self._default_model = normalize_litellm_model(default_model)

    async def complete(
        self,
        messages: Sequence[BaseMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
    ) -> AIMessage:
        use_model = normalize_litellm_model(model or self._default_model)
        kwargs: dict[str, Any] = {
            "model": use_model,
            "messages": _to_openai_messages(messages),
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        resp = await acompletion(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        content = getattr(msg, "content", None)
        if content is None and isinstance(msg, dict):
            content = msg.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                else:
                    parts.append(str(block))
            content = "".join(parts)
        if not isinstance(content, str):
            content = str(content or "")
        return AIMessage(content=content)
