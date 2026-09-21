"""程序化工具权限；模型字段不能改变权限结论。"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from .context import CallSource, ToolExecutionContext, digest_arguments


class PermissionLevel(StrEnum):
    AUTO = "auto"
    EXPLICIT_INTENT = "explicit_intent"
    CONFIRMATION_REQUIRED = "confirmation_required"
    TRUSTED_SYSTEM_ONLY = "trusted_system_only"


class PermissionOutcome(StrEnum):
    ALLOW = "allow"
    CONFIRMATION_REQUIRED = "confirmation_required"
    DENY = "deny"


@dataclass(frozen=True)
class PermissionDecision:
    outcome: PermissionOutcome
    reason: str


class ToolPermissionPolicy:
    def evaluate(
        self,
        *,
        tool_name: str,
        level: PermissionLevel,
        context: ToolExecutionContext,
        arguments: dict | None = None,
    ) -> PermissionDecision:
        if level == PermissionLevel.AUTO:
            return PermissionDecision(PermissionOutcome.ALLOW, "read_only")

        if level == PermissionLevel.EXPLICIT_INTENT:
            evidence = context.intent_evidence.get(tool_name)
            now = datetime.now(timezone.utc)
            if evidence is not None and evidence.expires_at.tzinfo is None:
                expires_at = evidence.expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at = evidence.expires_at if evidence is not None else None
            matched = (
                evidence is not None
                and evidence.user_id == context.user_id
                and evidence.request_id == context.request_id
                and evidence.tool_name == tool_name
                and expires_at is not None
                and expires_at > now
                and evidence.arguments_digest == digest_arguments(arguments or {})
            )
            if matched:
                return PermissionDecision(PermissionOutcome.ALLOW, "explicit_intent")
            return PermissionDecision(PermissionOutcome.DENY, "explicit_intent_required")

        if level == PermissionLevel.CONFIRMATION_REQUIRED:
            return PermissionDecision(
                PermissionOutcome.CONFIRMATION_REQUIRED,
                "frontend_confirmation_required",
            )

        if level == PermissionLevel.TRUSTED_SYSTEM_ONLY:
            trusted = (
                context.source == CallSource.SYSTEM
                and context.verified_focus_completion is not None
            )
            if trusted:
                return PermissionDecision(PermissionOutcome.ALLOW, "trusted_system")
            return PermissionDecision(PermissionOutcome.DENY, "trusted_system_required")

        return PermissionDecision(PermissionOutcome.DENY, "unsupported_permission")
