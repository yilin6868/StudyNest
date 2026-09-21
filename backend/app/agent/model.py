"""兼容 OpenAI Chat Completions 形态的 Agent 模型适配器。"""

from __future__ import annotations

import json
from typing import Protocol

import httpx

from ..core.config import settings
from .contracts import AgentInput, ModelDecision, ModelToolHistoryItem, parse_model_decision
from .prompt import CONVERSATION_SUMMARY_PROMPT, SUMMARY_PROMPT, SYSTEM_PROMPT


class AgentModelError(RuntimeError):
    pass


class AgentModelClient(Protocol):
    @property
    def available(self) -> bool: ...

    async def decide(
        self,
        agent_input: AgentInput,
        tools: list[dict],
        history: list[ModelToolHistoryItem],
        *,
        timeout_seconds: float,
    ) -> ModelDecision: ...

    async def summarize(self, facts: dict, *, timeout_seconds: float) -> str: ...

    async def summarize_conversation(
        self, facts: dict, *, timeout_seconds: float
    ) -> str: ...


class HttpAgentModelClient:
    @property
    def available(self) -> bool:
        return bool(settings.llm_api_key)

    async def _completion(
        self, messages: list[dict], *, timeout_seconds: float
    ) -> str:
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    settings.llm_base_url.rstrip("/") + "/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + settings.llm_api_key,
                    },
                    json={
                        "model": settings.llm_model,
                        "messages": messages,
                        "temperature": settings.llm_temperature,
                        "max_tokens": settings.llm_max_tokens,
                    },
                )
            response.raise_for_status()
            content = (
                ((response.json().get("choices") or [{}])[0].get("message") or {})
                .get("content", "")
                .strip()
            )
            if not content:
                raise AgentModelError("模型返回为空")
            return content
        except Exception as exc:  # noqa: BLE001
            raise AgentModelError("模型暂时不可用") from exc

    async def decide(
        self,
        agent_input: AgentInput,
        tools: list[dict],
        history: list[ModelToolHistoryItem],
        *,
        timeout_seconds: float,
    ) -> ModelDecision:
        payload = {
            "input": agent_input.model_dump(mode="json", by_alias=True),
            "allowedTools": tools,
            "toolHistory": [
                item.model_dump(mode="json", by_alias=True) for item in history
            ],
        }
        content = await self._completion(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            timeout_seconds=timeout_seconds,
        )
        try:
            return parse_model_decision(content)
        except Exception as exc:  # noqa: BLE001
            raise AgentModelError("模型输出协议不合法") from exc

    async def summarize(self, facts: dict, *, timeout_seconds: float) -> str:
        return await self._completion(
            [
                {"role": "system", "content": SUMMARY_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(facts, ensure_ascii=False),
                },
            ],
            timeout_seconds=timeout_seconds,
        )

    async def summarize_conversation(
        self, facts: dict, *, timeout_seconds: float
    ) -> str:
        return await self._completion(
            [
                {"role": "system", "content": CONVERSATION_SUMMARY_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(facts, ensure_ascii=False),
                },
            ],
            timeout_seconds=timeout_seconds,
        )
