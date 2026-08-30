"""对话服务：默认模型调用 + 失败回退内置引擎。

强制底线：模型调用集中在此层，处理超时、失败与有限重试；
无 Key / 非 2xx / 网络错误 / 空内容一律回退本地引擎，绝不抛出到 API 层。
"""
import httpx

from ..core.config import settings
from .phrases import local_reply

SYSTEM_PROMPT = (
    "你是用户的学习搭子「小悟」，一个像真人朋友一样的陪伴者。"
    "你和用户是一起学习、互相陪伴的关系：用户学习时你安静陪着，"
    "用户累了、想聊天时你自然陪聊。"
    "聊的内容：学习压力、情绪、日常小事、心态、放松方式等日常话题。"
    "【硬性规则】绝不输出专业知识：用户问具体学科题目、具体知识点、"
    "某道题怎么做、某个概念怎么理解时，一律不回答、不讲解、不给答案，"
    "礼貌拒绝并自然转移话题，例如「这个我就不掺和啦，我主要是陪你唠唠、放松心情的～」。"
    "但「学不进去、压力大、没动力、好累」这类学习情绪/心态问题，要好好陪聊。"
    "说话风格：像真人朋友，自然、口语化、有温度、有幽默感，"
    "不要每句都喊口号式鼓励，不要端着，偶尔反问用户把话题聊下去。"
    "回复简短（一般 1～3 句），中文，适当用 emoji。"
)

# 模型输出为空 / 出错时，最多重试的次数（有限重试）
MAX_ATTEMPTS = 2


def _enrich(message: str, goal: str | None) -> str:
    if goal and any(k in message for k in ("完成", "打卡", "开始", "专注")):
        return f"{message}（我的今日目标是：{goal}）"
    return message


async def _call_once(client: httpx.AsyncClient, message: str, goal: str | None) -> str:
    resp = await client.post(
        settings.llm_base_url.rstrip("/") + "/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + settings.llm_api_key,
        },
        json={
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _enrich(message, goal)},
            ],
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        },
        timeout=30.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}")
    data = resp.json()
    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    text = text.strip()
    if not text:
        raise RuntimeError("empty content")
    return text


async def chat(message: str, goal: str | None = None) -> tuple[str, str]:
    """返回 (reply, source)，source 为 "llm" 或 "local"。"""
    if not settings.llm_api_key:
        return local_reply(message), "local"

    last_err: Exception | None = None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for _ in range(MAX_ATTEMPTS):
                try:
                    return await _call_once(client, message, goal), "llm"
                except Exception as e:  # noqa: BLE001 —— 任何失败都兜底
                    last_err = e
    except Exception as e:  # 客户端构造阶段也可能失败（如无 Key）
        last_err = e

    if last_err is not None:
        # 不把异常堆栈泄露给用户，仅记录类型用于排查
        print(f"[chat] fallback to local engine: {type(last_err).__name__}")
    return local_reply(message), "local"
