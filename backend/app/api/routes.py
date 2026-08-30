"""API 路由：统一前缀 /api/v1。除登录外，其余接口均需 Bearer token 鉴权，数据按用户隔离。"""
from fastapi import APIRouter, Depends, Header, HTTPException, Response

from ..core.config import settings
from ..schemas.schemas import (
    ChatRequest,
    ChatResponse,
    CompleteRequest,
    EncourageRequest,
    EncourageResponse,
    GoalBody,
    LoginRequest,
    StatsResponse,
    TTSRequest,
)
from ..services import auth
from ..services.chat import chat
from ..services.history import HistoryService
from ..services.phrases import scene_reply
from ..services.stats import GoalService, StatsService
from ..services.store import JsonStore
from ..services.tts import synthesize

router = APIRouter(prefix="/api/v1")


def _user_store(user_id: str) -> JsonStore:
    """每个用户独立数据目录，实现数据隔离。"""
    return JsonStore(settings.data_dir / user_id)


def get_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    uid = auth.verify(authorization[7:])
    if not uid:
        raise HTTPException(status_code=401, detail="登录已过期")
    return uid


@router.post("/auth/login")
async def login(req: LoginRequest) -> dict:
    result = auth.login(req.code)
    if not result:
        raise HTTPException(status_code=401, detail="邀请码无效")
    return result


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, _: str = Depends(get_user_id)) -> ChatResponse:
    reply, source = await chat(req.message, req.goal)
    return ChatResponse(reply=reply, source=source)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(user_id: str = Depends(get_user_id)) -> StatsResponse:
    return StatsResponse(**StatsService(_user_store(user_id)).get())


@router.post("/stats/complete", response_model=StatsResponse)
async def complete_tomato(
    req: CompleteRequest, user_id: str = Depends(get_user_id)
) -> StatsResponse:
    store = _user_store(user_id)
    HistoryService(store).record(req.minutes)
    return StatsResponse(**StatsService(store).complete(req.minutes))


@router.get("/history")
async def get_history(user_id: str = Depends(get_user_id)) -> dict:
    data = HistoryService(_user_store(user_id)).get()
    days = data["days"]
    total_tomato = sum(int(d.get("tomato", 0)) for d in days.values())
    total_minutes = sum(int(d.get("minutes", 0)) for d in days.values())
    return {"days": days, "totalTomato": total_tomato, "totalMinutes": total_minutes}


@router.post("/encourage", response_model=EncourageResponse)
async def encourage(req: EncourageRequest, _: str = Depends(get_user_id)) -> EncourageResponse:
    return EncourageResponse(reply=scene_reply(req.scene))


@router.get("/goal", response_model=GoalBody)
async def get_goal(user_id: str = Depends(get_user_id)) -> GoalBody:
    return GoalBody(text=GoalService(_user_store(user_id)).get())


@router.put("/goal", response_model=GoalBody)
async def put_goal(req: GoalBody, user_id: str = Depends(get_user_id)) -> GoalBody:
    return GoalBody(text=GoalService(_user_store(user_id)).set(req.text))


@router.post("/tts")
async def tts(req: TTSRequest, _: str = Depends(get_user_id)) -> Response:
    try:
        audio = await synthesize(req.text, req.gender)
        if not audio:
            return Response(status_code=204)
        return Response(content=audio, media_type="audio/mpeg")
    except Exception:  # noqa: BLE001 —— 语音失败不阻断文字体验
        return Response(status_code=204)
