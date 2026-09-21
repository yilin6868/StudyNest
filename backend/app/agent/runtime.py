"""P1-C 有界 Agent 循环：安全前置、会话记忆、受控记忆和脱敏轨迹。"""

from __future__ import annotations

import asyncio
import time
from datetime import timezone
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from ..conversations.service import ConversationService
from ..core.config import settings
from ..db.models import ChatSession, User
from ..observability.recorder import TraceRecorder
from ..repositories.goals import GoalRepository
from ..repositories.study import StudyRepository
from ..safety.classifier import SafetyClassifier, SafetyResult
from ..safety.output_guard import SafetyOutputGuard
from ..safety.responses import CRISIS_RESPONSE, ELEVATED_RESPONSE, SAFETY_MARKER
from ..services.phrases import local_reply
from .confirmations import ConfirmationService
from .context import CallSource, ToolExecutionContext
from .contracts import (
    AgentResponse,
    FocusState,
    FocusSummaryResponse,
    ModelFinalDecision,
    ModelToolCallDecision,
    ModelToolHistoryItem,
    PendingFrontendAction,
    safe_fallback_response,
)
from .intents import IntentResolver
from .model import AgentModelClient, HttpAgentModelClient
from .observer import StateObserver
from .registry import ToolAuditEvent
from .tools import build_default_registry

pending_action_adapter = TypeAdapter(PendingFrontendAction)


class AgentRuntime:
    def __init__(
        self,
        *,
        model: AgentModelClient | None = None,
        observer: StateObserver | None = None,
        intent_resolver: IntentResolver | None = None,
        confirmation_service: ConfirmationService | None = None,
        conversation_service: ConversationService | None = None,
        safety_classifier: SafetyClassifier | None = None,
        output_guard: SafetyOutputGuard | None = None,
    ) -> None:
        self.model = model or HttpAgentModelClient()
        self.observer = observer or StateObserver()
        self.intent_resolver = intent_resolver or IntentResolver()
        self.confirmations = confirmation_service or ConfirmationService()
        self.conversations = conversation_service or ConversationService()
        self.safety = safety_classifier or SafetyClassifier()
        self.output_guard = output_guard or SafetyOutputGuard()

    async def chat(
        self,
        db: Session,
        user: User,
        *,
        message: str,
        focus: FocusState,
        session_id: str | None = None,
    ) -> AgentResponse:
        request_id = "req_" + uuid4().hex
        started = time.monotonic()
        session, _ = self.conversations.resolve(db, user.id, session_id)
        trace = TraceRecorder(
            request_id, user.id, max_events=settings.agent_trace_max_events
        )
        trace.record(
            "agent.request.started", outcome="started", protocolVersion="1.2"
        )

        try:
            safety = self.safety.classify(message)
        except Exception:  # noqa: BLE001 —— 分类异常时采用更保守流程
            safety = SafetyResult("crisis", "classifier_error")
        trace.record(
            "safety.input.classified",
            outcome="blocked" if safety.level != "normal" else "succeeded",
            level=safety.level,
            ruleId=safety.rule_id,
            rulesVersion=safety.rules_version,
        )

        if safety.level == "crisis":
            response = safe_fallback_response(
                request_id,
                CRISIS_RESPONSE,
                session_id=session.id,
                response_mode="safety",
            )
            self.conversations.save_exchange(
                db,
                session,
                user_text=SAFETY_MARKER,
                assistant_text=response.reply,
                safety_marker=True,
            )
            self._complete_trace(trace, started, response, outcome="blocked")
            trace.flush(db)
            return response

        if safety.level == "elevated":
            response = safe_fallback_response(
                request_id,
                ELEVATED_RESPONSE,
                session_id=session.id,
                response_mode="safety",
            )
            self.conversations.save_exchange(
                db,
                session,
                user_text=message,
                assistant_text=response.reply,
                response_safety=True,
            )
            self._complete_trace(trace, started, response, outcome="blocked")
            trace.flush(db)
            return response

        context = self.conversations.context(db, user.id, session)
        trace.record(
            "memory.context.loaded",
            outcome="succeeded",
            recentMessageCount=len(context.recent_messages),
            memoryCount=len(context.memories),
            summaryUsed=bool(context.summary),
        )
        fallback = local_reply(message)
        progress = {"wrote_goal": False, "wrote_memory": False}

        if not self.model.available:
            trace.record("agent.fallback.used", outcome="fallback", reasonCode="no_model")
            response = safe_fallback_response(
                request_id, fallback, session_id=session.id
            )
        else:
            try:
                async with asyncio.timeout(settings.agent_total_timeout_seconds):
                    response = await self._run_loop(
                        db,
                        user,
                        session=session,
                        request_id=request_id,
                        message=message,
                        focus=focus,
                        fallback=fallback,
                        progress=progress,
                        trace=trace,
                        conversation_summary=context.summary,
                        recent_messages=context.recent_messages,
                        memories=context.memories,
                    )
            except Exception:  # noqa: BLE001 —— 模型/协议/总超时均安全降级
                db.rollback()
                trace.record(
                    "agent.fallback.used", outcome="fallback", reasonCode="runtime_error"
                )
                response = self._fallback_after_tools(
                    request_id,
                    session.id,
                    fallback,
                    progress["wrote_goal"],
                    progress["wrote_memory"],
                )

        self.conversations.save_exchange(
            db,
            session,
            user_text=message,
            assistant_text=response.reply,
            response_safety=response.response_mode == "safety",
        )
        await self._maybe_summarize(db, session)
        self._complete_trace(trace, started, response, outcome="succeeded")
        trace.flush(db)
        return response

    async def _run_loop(
        self,
        db: Session,
        user: User,
        *,
        session: ChatSession,
        request_id: str,
        message: str,
        focus: FocusState,
        fallback: str,
        progress: dict[str, bool],
        trace: TraceRecorder,
        conversation_summary: str,
        recent_messages: list,
        memories: list,
    ) -> AgentResponse:
        agent_input = self.observer.build(
            db,
            user,
            message=message,
            focus_state=focus,
            conversation_summary=conversation_summary,
            recent_messages=recent_messages,
            memories=memories,
        )

        def audit_tool(event: ToolAuditEvent) -> None:
            trace.record(
                "tool.permission.evaluated",
                outcome="blocked" if event.permission == "deny" else "succeeded",
                toolName=event.tool_name,
                permission=event.permission,
            )
            trace.record(
                "tool.call.completed",
                outcome="succeeded" if event.outcome == "succeeded" else "failed",
                duration_ms=event.duration_ms,
                toolName=event.tool_name,
                result=event.outcome,
            )

        registry = build_default_registry(audit_sink=audit_tool)
        context = ToolExecutionContext(
            user_id=user.id,
            request_id=request_id,
            source=CallSource.AGENT,
            db=db,
            timezone_name=user.timezone,
            focus_state=focus,
            intent_evidence=self.intent_resolver.resolve(
                message, user_id=user.id, request_id=request_id
            ),
        )
        history: list[ModelToolHistoryItem] = []
        pending: list[PendingFrontendAction] = []
        fingerprints: set[str] = set()
        wrote_goal = False
        wrote_memory = False

        for turn in range(1, settings.agent_max_model_turns + 1):
            call_started = time.monotonic()
            try:
                decision = await asyncio.wait_for(
                    self.model.decide(
                        agent_input,
                        registry.descriptions(CallSource.AGENT),
                        history,
                        timeout_seconds=settings.agent_model_timeout_seconds,
                    ),
                    timeout=settings.agent_model_timeout_seconds,
                )
                trace.record(
                    "model.call.completed",
                    outcome="succeeded",
                    duration_ms=self._elapsed_ms(call_started),
                    modelAlias="configured",
                    turn=turn,
                )
            except Exception:
                trace.record(
                    "model.call.completed",
                    outcome="failed",
                    duration_ms=self._elapsed_ms(call_started),
                    modelAlias="configured",
                    turn=turn,
                )
                raise

            if isinstance(decision, ModelFinalDecision):
                expected = [
                    item.model_dump(mode="json", by_alias=True) for item in pending
                ]
                actual = [
                    item.model_dump(mode="json", by_alias=True)
                    for item in decision.actions
                ]
                if actual != expected:
                    return self._fallback_after_tools(
                        request_id, session.id, fallback, wrote_goal, wrote_memory
                    )
                if not self.output_guard.allows(decision.reply):
                    trace.record(
                        "output_guard.blocked", outcome="blocked", reasonCode="unsafe_output"
                    )
                    return safe_fallback_response(
                        request_id,
                        ELEVATED_RESPONSE,
                        session_id=session.id,
                        response_mode="safety",
                    )
                public_actions = [
                    self.confirmations.issue(
                        db,
                        user_id=user.id,
                        request_id=request_id,
                        action=action,
                    )
                    for action in pending
                ]
                for action in public_actions:
                    trace.record(
                        "agent.action.issued",
                        outcome="succeeded",
                        actionType=action.type,
                        expiresInSeconds=settings.agent_action_ttl_seconds,
                    )
                db.commit()
                return AgentResponse(
                    request_id=request_id,
                    session_id=session.id,
                    reply=decision.reply,
                    source="llm",
                    response_mode="normal",
                    actions=public_actions,
                )

            if not isinstance(decision, ModelToolCallDecision):
                return self._fallback_after_tools(
                    request_id, session.id, fallback, wrote_goal, wrote_memory
                )
            if len(history) >= settings.agent_max_tool_calls:
                return self._fallback_after_tools(
                    request_id,
                    session.id,
                    "这次可执行的操作太多了，请分开告诉我吧。",
                    wrote_goal,
                    wrote_memory,
                )
            fingerprint = registry.fingerprint(
                decision.tool_name, decision.arguments
            )
            if fingerprint in fingerprints:
                return self._fallback_after_tools(
                    request_id,
                    session.id,
                    "这个操作刚才已经处理过了。",
                    wrote_goal,
                    wrote_memory,
                )
            fingerprints.add(fingerprint)
            result = registry.execute(
                decision.tool_name, decision.arguments, context
            )
            history.append(
                ModelToolHistoryItem(
                    tool_name=decision.tool_name,
                    arguments=decision.arguments,
                    result=result,
                )
            )
            if result.ok and decision.tool_name == "set_today_goal":
                wrote_goal = progress["wrote_goal"] = True
            if result.ok and decision.tool_name == "save_learning_memory":
                wrote_memory = progress["wrote_memory"] = True
                trace.record(
                    "memory.changed",
                    outcome="succeeded",
                    category=decision.arguments.get("category", "unknown"),
                    operation="upsert",
                )
            if result.ok and result.data and "action" in result.data:
                pending.append(
                    pending_action_adapter.validate_python(result.data["action"])
                )

        return self._fallback_after_tools(
            request_id,
            session.id,
            "我这次没能安全完成判断，请把需求分成一句再试试。",
            wrote_goal,
            wrote_memory,
        )

    async def _maybe_summarize(self, db: Session, session: ChatSession) -> None:
        candidates, count = self.conversations.summary_candidates(db, session)
        if not candidates or not self.model.available:
            return
        method = getattr(self.model, "summarize_conversation", None)
        if method is None:
            return
        facts = {
            "previousSummary": session.summary or "",
            "messages": [
                {"role": item.role, "content": item.content}
                for item in candidates
                if item.role in {"user", "assistant"}
            ],
        }
        try:
            summary = await asyncio.wait_for(
                method(facts, timeout_seconds=settings.agent_model_timeout_seconds),
                timeout=settings.agent_model_timeout_seconds,
            )
            if summary and self.output_guard.allows(summary):
                self.conversations.update_summary(db, session, summary, count)
        except Exception:  # noqa: BLE001 —— 摘要失败不阻断已保存的聊天
            db.rollback()

    @staticmethod
    def _fallback_after_tools(
        request_id: str,
        session_id: str,
        fallback: str,
        wrote_goal: bool,
        wrote_memory: bool,
    ) -> AgentResponse:
        if wrote_goal:
            fallback = "今天的目标已经保存，不过我这次没能继续生成回复。"
        elif wrote_memory:
            fallback = "这条学习偏好已经记住了。"
        return safe_fallback_response(request_id, fallback, session_id=session_id)

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, round((time.monotonic() - started) * 1000))

    def _complete_trace(
        self,
        trace: TraceRecorder,
        started: float,
        response: AgentResponse,
        *,
        outcome: str,
    ) -> None:
        trace.record(
            "agent.request.completed",
            outcome=outcome,
            duration_ms=self._elapsed_ms(started),
            source=response.source,
            responseMode=response.response_mode,
        )

    async def focus_summary(
        self, db: Session, user: User, *, session_id: str
    ) -> FocusSummaryResponse | None:
        record = StudyRepository(db).get_completed_session(user.id, session_id)
        if record is None:
            return None
        try:
            zone = ZoneInfo(user.timezone)
        except ZoneInfoNotFoundError:
            zone = ZoneInfo(settings.app_timezone)
        completed_at = record.completed_at
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        day = completed_at.astimezone(zone).date()
        goal = GoalRepository(db).get(user.id, day)
        stats = StudyRepository(db).get_stats(user.id, today=day)
        facts = {
            "minutes": record.minutes,
            "goal": goal,
            "todayTomato": stats["tomato"],
            "todayMinutes": stats["minutes"],
        }
        local = (
            f"你刚完成了 {record.minutes} 分钟专注"
            + (f"，离今天的目标“{goal}”又近了一步" if goal else "")
            + f"。今天已累计 {stats['minutes']} 分钟，辛苦啦！"
        )
        if not self.model.available:
            return FocusSummaryResponse(
                session_id=session_id, reply=local, source="local"
            )
        try:
            reply = await asyncio.wait_for(
                self.model.summarize(
                    facts, timeout_seconds=settings.agent_model_timeout_seconds
                ),
                timeout=settings.agent_model_timeout_seconds,
            )
            if not self.output_guard.allows(reply):
                raise ValueError("总结输出未通过安全检查")
            return FocusSummaryResponse(
                session_id=session_id, reply=reply, source="llm"
            )
        except Exception:  # noqa: BLE001
            return FocusSummaryResponse(
                session_id=session_id, reply=local, source="local"
            )
