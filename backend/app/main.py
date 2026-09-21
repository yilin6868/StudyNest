"""FastAPI 入口：纯 API 服务、配置校验和统一错误结构。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .api.routes import router
from .core.config import settings
from .demo_bootstrap import bootstrap_demo
from .db.session import database_ready

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for message in settings.validate():
        logger.warning(message)
    bootstrap_demo()
    yield


app = FastAPI(title="StudyNest API", lifespan=lifespan)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "studynest-api"}


@app.get("/ready", tags=["system"])
def ready() -> JSONResponse:
    available = database_ready()
    return JSONResponse(
        status_code=200 if available else 503,
        content={"status": "ready" if available else "not_ready", "database": available},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": detail.get("code", f"HTTP_{exc.status_code}"),
                "message": detail.get("message", str(exc.detail)),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # 统一错误结构，不向用户泄露内部校验细节
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "请求参数不合法"}},
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error("数据库操作失败，请检查连接状态和数据库版本")
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "服务暂时不可用，请稍后重试",
            }
        },
    )


app.include_router(router)
