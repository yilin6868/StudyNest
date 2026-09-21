"""唯一工具注册和执行入口。"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel, ValidationError

from .context import CallSource, ToolExecutionContext, digest_arguments
from .contracts import ToolCallResult, ToolError
from .permissions import (
    PermissionLevel,
    PermissionOutcome,
    ToolPermissionPolicy,
)

logger = logging.getLogger(__name__)
_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


@dataclass(frozen=True)
class ToolAuditEvent:
    request_id: str
    tool_name: str
    permission: str
    outcome: str
    duration_ms: int


ToolHandler = Callable[[BaseModel, ToolExecutionContext], BaseModel]
AuditSink = Callable[[ToolAuditEvent], None]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    side_effect: bool
    permission: PermissionLevel
    timeout_seconds: float
    handler: ToolHandler


def _default_audit_sink(event: ToolAuditEvent) -> None:
    logger.info(
        "agent_tool request_id=%s tool=%s permission=%s outcome=%s duration_ms=%s",
        event.request_id,
        event.tool_name,
        event.permission,
        event.outcome,
        event.duration_ms,
    )


class ToolRegistry:
    def __init__(
        self,
        *,
        policy: ToolPermissionPolicy | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._policy = policy or ToolPermissionPolicy()
        self._audit_sink = audit_sink or _default_audit_sink

    def register(self, definition: ToolDefinition) -> None:
        if not _TOOL_NAME.fullmatch(definition.name):
            raise ValueError("工具名称格式不合法")
        if definition.name in self._tools:
            raise ValueError(f"工具重复注册：{definition.name}")
        if not 0 < definition.timeout_seconds <= 30:
            raise ValueError("工具超时必须在 0 到 30 秒之间")
        if not definition.description.strip():
            raise ValueError("工具用途不能为空")
        if (
            definition.side_effect
            and definition.permission == PermissionLevel.CONFIRMATION_REQUIRED
        ):
            raise ValueError("需要前端确认的工具在本阶段不能直接产生副作用")
        self._tools[definition.name] = definition

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def descriptions(self, source: CallSource | None = None) -> list[dict]:
        return [
            {
                "name": item.name,
                "description": item.description,
                "inputSchema": item.input_model.model_json_schema(by_alias=True),
                "sideEffect": item.side_effect,
                "permission": item.permission.value,
            }
            for item in sorted(self._tools.values(), key=lambda value: value.name)
            if not (
                source == CallSource.AGENT
                and item.permission == PermissionLevel.TRUSTED_SYSTEM_ONLY
            )
        ]

    @staticmethod
    def fingerprint(tool_name: str, arguments: dict) -> str:
        return f"{tool_name}:{digest_arguments(arguments)}"

    def execute(
        self,
        tool_name: str,
        arguments: dict,
        context: ToolExecutionContext,
    ) -> ToolCallResult:
        started = time.monotonic()
        context.tool_call_count += 1
        safe_name = tool_name if _TOOL_NAME.fullmatch(tool_name) else "<invalid>"
        definition = self._tools.get(tool_name)
        if definition is None:
            result = self._error(
                "TOOL_NOT_FOUND", "这个工具不在允许清单中", "deny"
            )
            self._audit(started, context, safe_name, "deny", "not_found")
            return result

        try:
            parsed = definition.input_model.model_validate(arguments)
        except ValidationError:
            result = self._error(
                "TOOL_INVALID_ARGUMENTS", "工具参数不合法", "deny"
            )
            self._audit(started, context, safe_name, "deny", "invalid_arguments")
            return result

        normalized_arguments = parsed.model_dump(
            mode="json", by_alias=True, exclude_none=True
        )
        decision = self._policy.evaluate(
            tool_name=definition.name,
            level=definition.permission,
            context=context,
            arguments=normalized_arguments,
        )
        if decision.outcome == PermissionOutcome.DENY:
            result = self._error(
                "TOOL_PERMISSION_DENIED", "这个操作当前没有权限", "deny"
            )
            self._audit(started, context, safe_name, "deny", decision.reason)
            return result

        if definition.side_effect and definition.name in context.executed_side_effects:
            result = self._error(
                "TOOL_PERMISSION_DENIED", "本次请求已经执行过这个操作", "deny"
            )
            self._audit(started, context, safe_name, "deny", "duplicate_side_effect")
            return result

        permission = decision.outcome.value
        try:
            raw_result = definition.handler(parsed, context)
            validated = definition.output_model.model_validate(raw_result)
            elapsed = time.monotonic() - started
            if elapsed > definition.timeout_seconds:
                self._rollback(context)
                result = self._error("TOOL_TIMEOUT", "工具执行超时", permission)
                self._audit(started, context, safe_name, permission, "timeout")
                return result
            if definition.side_effect:
                context.db.commit()
                context.executed_side_effects.add(definition.name)
        except TimeoutError:
            self._rollback(context)
            result = self._error("TOOL_TIMEOUT", "工具执行超时", permission)
            self._audit(started, context, safe_name, permission, "timeout")
            return result
        except ValidationError:
            self._rollback(context)
            result = self._error(
                "TOOL_INVALID_RESULT", "工具返回结果不合法", permission
            )
            self._audit(started, context, safe_name, permission, "invalid_result")
            return result
        except Exception:  # noqa: BLE001 —— 不向外泄露底层错误
            self._rollback(context)
            result = self._error(
                "TOOL_EXECUTION_FAILED", "工具暂时无法完成", permission
            )
            self._audit(started, context, safe_name, permission, "failed")
            return result

        self._audit(started, context, safe_name, permission, "succeeded")
        return ToolCallResult(
            ok=True,
            permission=permission,
            data=validated.model_dump(mode="json", by_alias=True),
        )

    @staticmethod
    def _error(code: str, message: str, permission: str) -> ToolCallResult:
        return ToolCallResult(
            ok=False,
            permission=permission,
            error=ToolError(code=code, message=message),
        )

    def _audit(
        self,
        started: float,
        context: ToolExecutionContext,
        tool_name: str,
        permission: str,
        outcome: str,
    ) -> None:
        try:
            self._audit_sink(
                ToolAuditEvent(
                    request_id=context.request_id,
                    tool_name=tool_name,
                    permission=permission,
                    outcome=outcome,
                    duration_ms=max(0, round((time.monotonic() - started) * 1000)),
                )
            )
        except Exception:  # noqa: BLE001 —— 审计故障不能打断安全返回
            logger.warning(
                "agent_tool_audit_failed request_id=%s tool=%s",
                context.request_id,
                tool_name,
            )

    @staticmethod
    def _rollback(context: ToolExecutionContext) -> None:
        try:
            context.db.rollback()
        except Exception:  # noqa: BLE001 —— 不把数据库内部错误暴露给调用方
            pass
