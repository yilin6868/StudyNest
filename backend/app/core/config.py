"""配置读取：从 backend/.env 或环境变量加载，绝不硬编码密钥。"""
import os
from pathlib import Path

from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
load_dotenv(_BASE_DIR / ".env")


def _get(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


class Settings:
    # 模型配置（默认 GLM-4-Flash，免费；换模型改 .env 即可）
    llm_base_url: str = _get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    llm_api_key: str = _get("LLM_API_KEY", "")
    llm_model: str = _get("LLM_MODEL", "glm-4-flash")
    llm_temperature: float = float(_get("LLM_TEMPERATURE", "0.8") or "0.8")
    llm_max_tokens: int = int(_get("LLM_MAX_TOKENS", "300") or "300")

    # 数据目录（相对路径解析到 backend/ 下）
    data_dir: Path = Path(_get("DATA_DIR", "./data"))
    if not data_dir.is_absolute():
        data_dir = (_BASE_DIR / data_dir).resolve()

    # 登录：邀请码（逗号分隔）+ token 签名密钥
    invite_codes: str = _get("INVITE_CODES", "")
    auth_secret: str = _get("AUTH_SECRET", "dev-secret-change-me")


settings = Settings()
