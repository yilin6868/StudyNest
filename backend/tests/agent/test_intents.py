from datetime import datetime, timezone

from app.agent.context import digest_arguments
from app.agent.intents import IntentResolver


def test_goal_intent_is_bound_to_exact_normalized_arguments():
    evidence = IntentResolver().resolve(
        "把今天目标设为背 50 个单词",
        user_id="user-1",
        request_id="request_123",
        now=datetime.now(timezone.utc),
    )["set_today_goal"]
    assert evidence.arguments_digest == digest_arguments({"text": "背 50 个单词"})


def test_mentioning_goal_is_not_a_write_intent():
    evidence = IntentResolver().resolve(
        "我今天的目标好难",
        user_id="user-1",
        request_id="request_123",
    )
    assert "set_today_goal" not in evidence


def test_pause_and_preference_intents_are_conservative():
    resolver = IntentResolver()
    pause = resolver.resolve("请暂停专注", user_id="u", request_id="request_123")
    voice = resolver.resolve("帮我打开语音", user_id="u", request_id="request_456")
    assert "request_pause_focus" in pause
    assert voice["update_preference"].arguments_digest == digest_arguments(
        {"voiceEnabled": True}
    )
