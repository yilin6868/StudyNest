"""API 路由：统一前缀 /api/v1，业务数据统一由数据库持久化。"""
from datetime import datetime
import hashlib
import secrets
from datetime import timedelta
import time
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..agent.confirmations import ConfirmationService
from ..agent.contracts import (
    AgentChatRequest,
    AgentResponse,
    FocusSummaryRequest,
    FocusSummaryResponse,
    ResolveAgentActionRequest,
    ResolveAgentActionResponse,
)
from ..agent.runtime import AgentRuntime
from ..conversations.contracts import (
    ConversationCreateResponse,
    ConversationList,
    ConversationMessages,
)
from ..conversations.service import ConversationNotFoundError, ConversationService
from ..db.models import User, ChatSession, ChatMessage, UserMemory, DailyGoal, DailyStudyRecord, StudySession
from ..db.session import get_db
from ..repositories.agent_actions import ActionResolutionError
from ..repositories.goals import GoalRepository
from ..repositories.preferences import PreferenceRepository
from ..repositories.study import StudyRepository
from ..memory.contracts import MemoryBody, MemoryCategory, MemoryItem, MemoryList
from ..memory.policy import MemoryPolicyError
from ..memory.service import MemoryService
from ..observability.recorder import TraceRecorder
from ..observability.metrics import summarize_events
from ..repositories.agent_events import AgentEventRepository
from ..schemas.schemas import (
    CompleteRequest,
    EncourageRequest,
    EncourageResponse,
    GoalBody,
    LegacyClaimRequest,
    LoginRequest,
    DemoLoginRequest,
    RegisterRequest,
    SessionResponse,
    StatsResponse,
    TTSRequest,
    CompanionPreferences,
    ProductEventRequest,
    ProductEventResponse,
    LearningSummaryResponse,
    DataActionRequest,
    FocusOptionsResponse, AchievementResponse,
    RoomCreateRequest, RoomJoinRequest, RoomStatusRequest, RoomReportRequest,
)
from ..services import auth
from ..services.phrases import scene_reply
from ..services.tts import synthesize
from ..summaries.service import generate_summary

router = APIRouter(prefix="/api/v1")
agent_runtime = AgentRuntime()
confirmation_service = ConfirmationService()
conversation_service = ConversationService()
memory_service = MemoryService()


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    return authorization[7:]


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    user = auth.verify(db, _bearer_token(authorization))
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期")
    return user


def _today(user: User):
    try:
        zone = ZoneInfo(user.timezone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("Asia/Shanghai")
    return datetime.now(zone)


def _raise_account_error(exc: auth.AccountError, status_code: int = 400) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    ) from exc


@router.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return auth.register(db, req.invite_code, req.username, req.password)
    except auth.AccountError as exc:
        _raise_account_error(exc)


@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return auth.login(db, req.username, req.password)
    except auth.AccountError as exc:
        _raise_account_error(exc, status_code=401)

@router.post("/auth/demo-login")
def demo_login(req: DemoLoginRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return auth.demo_login(db, req.invite_code)
    except auth.AccountError as exc:
        _raise_account_error(exc, status_code=401)


@router.post("/auth/logout", status_code=204)
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Response:
    token = _bearer_token(authorization)
    if not auth.verify(db, token):
        raise HTTPException(status_code=401, detail="登录已过期")
    auth.logout(db, token)
    return Response(status_code=204)


@router.post("/auth/legacy-claim")
def legacy_claim(req: LegacyClaimRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return auth.claim_legacy_account(
            db, req.legacy_token, req.username, req.password
        )
    except auth.AccountError as exc:
        _raise_account_error(exc)


@router.get("/auth/session", response_model=SessionResponse)
def get_session(user: User = Depends(get_current_user)) -> SessionResponse:
    return SessionResponse(userId=user.id, username=user.username)


@router.post("/chat", response_model=AgentResponse)
async def chat_endpoint(
    req: AgentChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentResponse:
    try:
        return await agent_runtime.chat(
            db,
            user,
            message=req.message,
            focus=req.focus,
            session_id=req.session_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="没有找到这个会话") from exc


@router.post("/chat/sessions", response_model=ConversationCreateResponse)
def create_chat_session(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ConversationCreateResponse:
    return conversation_service.create(db, user.id)


@router.get("/chat/sessions", response_model=ConversationList)
def list_chat_sessions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ConversationList:
    return conversation_service.list(db, user.id)


@router.get(
    "/chat/sessions/{session_id}/messages", response_model=ConversationMessages
)
def get_chat_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationMessages:
    try:
        return conversation_service.messages(db, user.id, session_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="没有找到这个会话") from exc


@router.delete("/chat/sessions/{session_id}", status_code=204)
def delete_chat_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        conversation_service.delete(db, user.id, session_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="没有找到这个会话") from exc
    return Response(status_code=204)


@router.get("/memories", response_model=MemoryList)
def list_memories(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MemoryList:
    return memory_service.list(db, user.id)


@router.put("/memories/{category}", response_model=MemoryItem)
def put_memory(
    category: MemoryCategory,
    req: MemoryBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemoryItem:
    try:
        result = memory_service.save(
            db, user.id, category, req.content, source="user_ui"
        )
        db.commit()
        trace = TraceRecorder("req_" + uuid4().hex, user.id)
        trace.record(
            "memory.changed",
            outcome="succeeded",
            category=category,
            operation="upsert",
        )
        trace.flush(db)
        return result
    except MemoryPolicyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail={"code": "MEMORY_NOT_ALLOWED", "message": str(exc)},
        ) from exc


@router.delete("/memories/{category}", status_code=204)
def delete_memory(
    category: MemoryCategory,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    memory_service.delete(db, user.id, category)
    db.commit()
    trace = TraceRecorder("req_" + uuid4().hex, user.id)
    trace.record(
        "memory.changed",
        outcome="succeeded",
        category=category,
        operation="delete",
    )
    trace.flush(db)
    return Response(status_code=204)


@router.post("/agent/actions/resolve", response_model=ResolveAgentActionResponse)
def resolve_agent_action(
    req: ResolveAgentActionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResolveAgentActionResponse:
    try:
        result = confirmation_service.resolve(
            db,
            user_id=user.id,
            token=req.confirmation_token,
            decision=req.decision,
        )
        trace = TraceRecorder("req_" + uuid4().hex, user.id)
        trace.record(
            "agent.action.resolved",
            outcome="succeeded",
            actionType=result.action.type if result.action else "rejected",
            decision=req.decision,
        )
        trace.flush(db)
        return result
    except ActionResolutionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.post("/agent/focus-summary", response_model=FocusSummaryResponse)
async def focus_summary(
    req: FocusSummaryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FocusSummaryResponse:
    result = await agent_runtime.focus_summary(
        db, user, session_id=req.session_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="没有找到这次已完成的专注")
    return result


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> StatsResponse:
    return StatsResponse(
        **StudyRepository(db).get_stats(user.id, today=_today(user).date())
    )


@router.post("/stats/complete", response_model=StatsResponse)
def complete_tomato(
    req: CompleteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatsResponse:
    completed_at = _today(user)
    repository = StudyRepository(db)
    repository.complete(
        user_id=user.id,
        client_session_id=str(req.session_id),
        minutes=req.minutes,
        completed_at=completed_at,
    )
    # P3-A: determine non-competitive achievements from persisted facts.
    from ..db.models import AchievementDefinition, UserAchievement, new_id
    definitions = [
        ("first_focus", "第一次专注", "完成了第一次有效专注"),
        ("five_focus_sessions", "专注五次", "累计完成五次有效专注"),
    ]
    for code, title, description in definitions:
        definition = db.scalar(select(AchievementDefinition).where(AchievementDefinition.code == code))
        if definition is None:
            definition = AchievementDefinition(id=new_id(), code=code, title=title, description=description, created_at=completed_at, rule_version=1, active=True)
            db.add(definition); db.flush()
        count = db.query(StudySession).filter(StudySession.user_id == user.id, StudySession.status == "completed").count()
        eligible = (code == "first_focus" and count >= 1) or (code == "five_focus_sessions" and count >= 5)
        if eligible and not db.scalar(select(UserAchievement).where(UserAchievement.user_id == user.id, UserAchievement.achievement_code == code, UserAchievement.rule_version == 1)):
            db.add(UserAchievement(id=new_id(), user_id=user.id, achievement_code=code, rule_version=1, awarded_at=completed_at, created_at=completed_at))
    db.commit()
    return StatsResponse(**repository.get_stats(user.id, today=completed_at.date()))


@router.get("/history")
def get_history(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    days = StudyRepository(db).get_days(user.id)
    total_tomato = sum(int(d.get("tomato", 0)) for d in days.values())
    total_minutes = sum(int(d.get("minutes", 0)) for d in days.values())
    return {"days": days, "totalTomato": total_tomato, "totalMinutes": total_minutes}


@router.post("/encourage", response_model=EncourageResponse)
async def encourage(
    req: EncourageRequest, _: User = Depends(get_current_user)
) -> EncourageResponse:
    return EncourageResponse(reply=scene_reply(req.scene))


@router.get("/companion/preferences", response_model=CompanionPreferences)
def get_companion_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CompanionPreferences:
    data = PreferenceRepository(db).get(user.id, include_companion=True)
    return CompanionPreferences(**{k: data[k] for k in CompanionPreferences.model_fields})


@router.put("/companion/preferences", response_model=CompanionPreferences)
def put_companion_preferences(req: CompanionPreferences, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CompanionPreferences:
    data = PreferenceRepository(db).update(
        user.id,
        buddy_gender=None,
        voice_enabled=None,
        mid_session_encouragement_enabled=req.mid_session_encouragement_enabled,
        proactive_reminder_enabled=req.proactive_reminder_enabled,
        quiet_hours_start=req.quiet_hours_start,
        quiet_hours_end=req.quiet_hours_end,
        custom_focus_enabled=req.custom_focus_enabled,
        default_focus_minutes=req.default_focus_minutes,
        reminder_channel=req.reminder_channel,
        now=_today(user),
        include_companion=True,
    )
    db.commit()
    return CompanionPreferences(**{k: data[k] for k in CompanionPreferences.model_fields})


@router.get("/focus/options", response_model=FocusOptionsResponse)
def focus_options(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> FocusOptionsResponse:
    prefs = PreferenceRepository(db).get(user.id, include_companion=True)
    return FocusOptionsResponse(enabled=bool(prefs["custom_focus_enabled"]), options=[15, 25, 45, 60], default_minutes=int(prefs["default_focus_minutes"]))


def _room_payload(room, members):
    return {"roomId": room.id, "status": room.status, "expiresAt": room.expires_at.isoformat(), "members": [{"userId": m.user_id, "focusStatus": m.focus_status} for m in members if m.status == "active"]}

@router.post("/rooms")
def create_room(req: RoomCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from ..db.models import StudyRoom, StudyRoomMember, new_id
    token = secrets.token_urlsafe(24); now = _today(user); room = StudyRoom(id=new_id(), owner_id=user.id, invite_token_digest=hashlib.sha256(token.encode()).hexdigest(), status="active", expires_at=now + timedelta(hours=req.expires_hours), created_at=now)
    db.add(room); db.add(StudyRoomMember(id=new_id(), room_id=room.id, user_id=user.id, status="active", focus_status="idle", last_seen_at=now, created_at=now)); db.commit()
    return {"roomId": room.id, "inviteToken": token, "expiresAt": room.expires_at.isoformat()}

@router.post("/rooms/join")
def join_room(req: RoomJoinRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from ..db.models import StudyRoom, StudyRoomMember, new_id
    room = db.scalar(select(StudyRoom).where(StudyRoom.invite_token_digest == hashlib.sha256(req.invite_token.encode()).hexdigest(), StudyRoom.status == "active"))
    if room is None or room.expires_at < _today(user): raise HTTPException(status_code=404, detail="自习室不存在或已过期")
    member = db.scalar(select(StudyRoomMember).where(StudyRoomMember.room_id == room.id, StudyRoomMember.user_id == user.id))
    if member is None: db.add(StudyRoomMember(id=new_id(), room_id=room.id, user_id=user.id, status="active", focus_status="idle", last_seen_at=_today(user), created_at=_today(user))); db.commit()
    members = db.scalars(select(StudyRoomMember).where(StudyRoomMember.room_id == room.id)).all(); return _room_payload(room, members)

@router.get("/rooms/{room_id}")
def get_room(room_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from ..db.models import StudyRoom, StudyRoomMember
    room = db.scalar(select(StudyRoom).where(StudyRoom.id == room_id)); member = db.scalar(select(StudyRoomMember).where(StudyRoomMember.room_id == room_id, StudyRoomMember.user_id == user.id, StudyRoomMember.status == "active"))
    if room is None or member is None or room.status != "active": raise HTTPException(status_code=404, detail="无权访问该自习室")
    members = db.scalars(select(StudyRoomMember).where(StudyRoomMember.room_id == room_id)).all(); return _room_payload(room, members)

@router.put("/rooms/{room_id}/status")
def update_room_status(room_id: str, req: RoomStatusRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from ..db.models import StudyRoomMember
    member = db.scalar(select(StudyRoomMember).where(StudyRoomMember.room_id == room_id, StudyRoomMember.user_id == user.id, StudyRoomMember.status == "active"))
    if member is None: raise HTTPException(status_code=404, detail="无权访问该自习室")
    member.focus_status = req.focus_status; member.last_seen_at = _today(user); db.commit(); return {"status": member.focus_status}

@router.post("/rooms/{room_id}/leave", status_code=204)
def leave_room(room_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    from ..db.models import StudyRoomMember
    member = db.scalar(select(StudyRoomMember).where(StudyRoomMember.room_id == room_id, StudyRoomMember.user_id == user.id));
    if member is None: raise HTTPException(status_code=404, detail="无权访问该自习室")
    member.status = "left"; db.commit(); return Response(status_code=204)

@router.post("/rooms/{room_id}/reports")
def report_room(room_id: str, req: RoomReportRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from ..db.models import StudyRoomMember, StudyRoomReport, new_id
    if db.scalar(select(StudyRoomMember).where(StudyRoomMember.room_id == room_id, StudyRoomMember.user_id == user.id, StudyRoomMember.status == "active")) is None: raise HTTPException(status_code=404, detail="无权访问该自习室")
    db.add(StudyRoomReport(id=new_id(), room_id=room_id, reporter_id=user.id, reason=req.reason, created_at=_today(user))); db.commit(); return {"accepted": True}


@router.get("/achievements", response_model=list[AchievementResponse])
def achievements(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[AchievementResponse]:
    from ..db.models import UserAchievement, AchievementDefinition
    rows = db.execute(select(UserAchievement, AchievementDefinition).join(AchievementDefinition, AchievementDefinition.code == UserAchievement.achievement_code).where(UserAchievement.user_id == user.id).order_by(UserAchievement.awarded_at.desc())).all()
    return [AchievementResponse(code=d.code, title=d.title, description=d.description, awarded_at=a.awarded_at.isoformat(), hidden=a.hidden_at is not None) for a, d in rows if a.hidden_at is None]


@router.get("/companion/inbox")
def companion_inbox(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """P3-C 首版仅提供站内、确定性提醒，不发送站外通知。"""
    prefs = PreferenceRepository(db).get(user.id, include_companion=True)
    if not prefs["proactive_reminder_enabled"]:
        return {"items": []}
    end = _today(user).date()
    recent = db.scalar(select(StudySession).where(StudySession.user_id == user.id, StudySession.status == "completed").order_by(StudySession.completed_at.desc()).limit(1))
    if recent is not None and (end - recent.completed_at.date()).days < 2:
        return {"items": []}
    return {"items": [{"id": "inactive-study", "type": "study.inactive", "message": "最近还好吗？如果今天有空，可以从一小段专注开始。"}]}


@router.post("/analytics/events", response_model=ProductEventResponse)
def record_product_event(req: ProductEventRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProductEventResponse:
    trace = TraceRecorder("evt_" + uuid4().hex, user.id)
    trace.record(req.event_type, outcome="succeeded", sessionId=req.session_id, durationMinutes=req.duration_minutes)
    trace.flush(db)
    return ProductEventResponse()


@router.get("/analytics/me")
def personal_analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return summarize_events(AgentEventRepository(db).since(24 * 30))


@router.get("/summaries/daily", response_model=LearningSummaryResponse)
async def daily_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> LearningSummaryResponse:
    day = _today(user).date()
    facts, text, source = await generate_summary(db, user, day, day, agent_runtime.model)
    return LearningSummaryResponse(period=facts["period"], facts=facts, text=text, source=source)


@router.get("/summaries/weekly", response_model=LearningSummaryResponse)
async def weekly_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> LearningSummaryResponse:
    end = _today(user).date()
    start = end.fromordinal(end.toordinal() - end.weekday())
    facts, text, source = await generate_summary(db, user, start, end, agent_runtime.model)
    return LearningSummaryResponse(period=facts["period"], facts=facts, text=text, source=source)


@router.get("/summaries/weekly/broadcast", response_model=LearningSummaryResponse)
async def weekly_broadcast(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> LearningSummaryResponse:
    """P3-D 文字播报接口；TTS 仍需由用户开启语音后主动调用 /tts。"""
    return await weekly_summary(user, db)


@router.get("/data/export")
def export_user_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user.id)).all()
    session_ids = [item.id for item in sessions]
    messages = db.scalars(select(ChatMessage).where(ChatMessage.chat_session_id.in_(session_ids))).all() if session_ids else []
    memories = db.scalars(select(UserMemory).where(UserMemory.user_id == user.id)).all()
    goals = db.scalars(select(DailyGoal).where(DailyGoal.user_id == user.id)).all()
    days = db.scalars(select(DailyStudyRecord).where(DailyStudyRecord.user_id == user.id)).all()
    return {
        "schemaVersion": 1,
        "account": {"username": user.username, "timezone": user.timezone},
        "goals": [{"date": item.goal_date.isoformat(), "text": item.text} for item in goals],
        "study": [{"date": item.study_date.isoformat(), "tomato": item.tomato_count, "minutes": item.minutes} for item in days],
        "memories": [{"category": item.category, "content": item.content, "updatedAt": item.updated_at.isoformat()} for item in memories],
        "chat": [{"sessionId": item.chat_session_id, "role": item.role, "content": item.content, "createdAt": item.created_at.isoformat()} for item in messages],
    }


@router.post("/data/delete-study")
def delete_study_data(req: DataActionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if req.confirmation != "DELETE STUDY DATA":
        raise HTTPException(status_code=400, detail="确认短语不正确")
    db.query(DailyStudyRecord).filter(DailyStudyRecord.user_id == user.id).delete(synchronize_session=False)
    db.query(StudySession).filter(StudySession.user_id == user.id).delete(synchronize_session=False)
    db.commit()
    return {"status": "completed"}


@router.post("/data/delete-account")
def delete_account(req: DataActionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if req.confirmation != "DELETE ACCOUNT":
        raise HTTPException(status_code=400, detail="确认短语不正确")
    db.delete(user)
    db.commit()
    return {"status": "completed"}


@router.get("/goal", response_model=GoalBody)
def get_goal(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> GoalBody:
    return GoalBody(text=GoalRepository(db).get(user.id, _today(user).date()))


@router.put("/goal", response_model=GoalBody)
def put_goal(
    req: GoalBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalBody:
    now = _today(user)
    text = GoalRepository(db).set(user.id, now.date(), req.text.strip(), now=now)
    db.commit()
    return GoalBody(text=text)


@router.post("/tts")
async def tts(
    req: TTSRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    started = time.monotonic()
    trace = TraceRecorder("req_" + uuid4().hex, user.id)
    try:
        audio = await synthesize(req.text, req.gender)
        if not audio:
            trace.record(
                "tts.call.completed",
                outcome="fallback",
                duration_ms=max(0, round((time.monotonic() - started) * 1000)),
            )
            trace.flush(db)
            return Response(status_code=204)
        trace.record(
            "tts.call.completed",
            outcome="succeeded",
            duration_ms=max(0, round((time.monotonic() - started) * 1000)),
        )
        trace.flush(db)
        return Response(content=audio, media_type="audio/mpeg")
    except Exception:  # noqa: BLE001 —— 语音失败不阻断文字体验
        trace.record(
            "tts.call.completed",
            outcome="failed",
            duration_ms=max(0, round((time.monotonic() - started) * 1000)),
        )
        trace.flush(db)
        return Response(status_code=204)
