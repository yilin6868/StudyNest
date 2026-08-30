"""API 请求 / 响应结构（Pydantic 强校验）。"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=200)
    goal: str | None = Field(default=None, max_length=60)


class ChatResponse(BaseModel):
    reply: str
    source: str  # "llm" | "local"


class StatsResponse(BaseModel):
    date: str
    tomato: int
    minutes: int
    streak: int
    weekDays: list[str]


class CompleteRequest(BaseModel):
    minutes: int = Field(default=25, ge=1, le=600)


class EncourageRequest(BaseModel):
    scene: str = Field(..., pattern="^(greet|start|encourage|celebrate|break|breakOver|tired|idle)$")


class EncourageResponse(BaseModel):
    reply: str


class GoalBody(BaseModel):
    text: str = Field(default="", max_length=60)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)
    gender: str | None = Field(default=None, pattern="^(male|female)$")


class LoginRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
