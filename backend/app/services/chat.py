"""旧兼容入口；正式 /chat 已由 AgentRuntime 接管。"""

from ..core.config import settings  # 兼容旧调用方读取同一配置实例
from .phrases import local_reply


async def chat(message: str, goal: str | None = None) -> tuple[str, str]:
    """仅供旧代码兼容；不再在这里进行第二套模型调用。"""
    return local_reply(message), "local"
