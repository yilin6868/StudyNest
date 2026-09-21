"""学习总结服务：事实由程序计算，模型只组织语言。"""
from datetime import date
from ..core.config import settings

def local_summary(facts: dict) -> str:
    if facts["completed_sessions"] == 0:
        return "这段时间暂无足够的专注记录，先从今天的一小步开始吧。"
    return f"这段时间你完成了 {facts['completed_sessions']} 次专注，共 {facts['total_minutes']} 分钟，学习了 {facts['study_days']} 天。"

async def generate_summary(db, user, start: date, end: date, model) -> tuple[dict, str, str]:
    from .facts import build_facts
    facts = build_facts(db, user.id, start, end)
    if not model.available:
        return facts, local_summary(facts), "local_fallback"
    try:
        text = await model.summarize(facts, timeout_seconds=settings.agent_model_timeout_seconds)
        return facts, text, "model"
    except Exception:
        return facts, local_summary(facts), "local_fallback"
