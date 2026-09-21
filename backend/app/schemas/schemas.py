"""API 请求 / 响应结构（Pydantic 强校验）。"""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class StatsResponse(BaseModel):
    date: str
    tomato: int
    minutes: int
    streak: int
    weekDays: list[str]


class CompleteRequest(BaseModel):
    session_id: UUID = Field(alias="sessionId")
    minutes: int = Field(default=25, ge=1, le=600)


class SessionResponse(BaseModel):
    authenticated: Literal[True] = True
    userId: str
    username: str | None = None


class EncourageRequest(BaseModel):
    scene: str = Field(..., pattern="^(greet|start|encourage|celebrate|break|breakOver|tired|idle)$")


class EncourageResponse(BaseModel):
    reply: str


class CompanionPreferences(BaseModel):
    mid_session_encouragement_enabled: bool = False
    proactive_reminder_enabled: bool = False
    quiet_hours_start: str | None = Field(default=None, pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    custom_focus_enabled: bool = False
    default_focus_minutes: int = Field(default=25, ge=15, le=60)
    reminder_channel: Literal["in_app"] = "in_app"


class ProductEventRequest(BaseModel):
    event_type: Literal[
        "focus.started", "focus.halfway_shown", "focus.completed",
        "focus.completion_failed", "companion.preference_changed",
        "companion.reminder_shown", "companion.reminder_dismissed",
        "summary.viewed", "data.export.requested", "data.export.completed",
        "data.deletion.requested", "account.deletion.requested",
    ] = Field(alias="eventType")
    session_id: str | None = Field(default=None, alias="sessionId", max_length=64)
    duration_minutes: int | None = Field(default=None, alias="durationMinutes", ge=1, le=120)


class ProductEventResponse(BaseModel):
    accepted: bool = True


class LearningSummaryResponse(BaseModel):
    period: str
    facts: dict[str, object]
    text: str
    source: Literal["model", "local_fallback"]


class DataActionRequest(BaseModel):
    confirmation: str = Field(..., min_length=1, max_length=64)


class FocusOptionsResponse(BaseModel):
    enabled: bool
    options: list[int]
    default_minutes: int


class AchievementResponse(BaseModel):
    code: str
    title: str
    description: str
    awarded_at: str
    hidden: bool = False

class RoomCreateRequest(BaseModel):
    expires_hours: int = Field(default=4, ge=1, le=24)
class RoomJoinRequest(BaseModel):
    invite_token: str = Field(..., min_length=16, max_length=128)
class RoomStatusRequest(BaseModel):
    focus_status: Literal["idle", "focusing"]
class RoomReportRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=255)


class GoalBody(BaseModel):
    text: str = Field(default="", max_length=60)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)
    gender: str | None = Field(default=None, pattern="^(male|female)$")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    invite_code: str = Field(..., alias="inviteCode", min_length=1, max_length=128)
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)

class DemoLoginRequest(BaseModel):
    invite_code: str = Field(..., alias="inviteCode", min_length=1, max_length=128)


class LegacyClaimRequest(BaseModel):
    legacy_token: str = Field(..., alias="legacyToken", min_length=1, max_length=512)
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
