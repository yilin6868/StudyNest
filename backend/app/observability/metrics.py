"""基于脱敏事件的最小指标汇总。"""

from collections import Counter


def summarize_events(events: list) -> dict[str, int]:
    types = Counter(item.event_type for item in events)
    outcomes = Counter(item.outcome for item in events)
    tts = [item for item in events if item.event_type == "tts.call.completed"]
    return {
        "events": len(events),
        "agentRequests": types["agent.request.started"],
        "completedRequests": types["agent.request.completed"],
        "modelCalls": types["model.call.completed"],
        "toolCalls": types["tool.call.completed"],
        "safetyFlows": sum(
            1
            for item in events
            if item.event_type == "safety.input.classified" and item.outcome == "blocked"
        ),
        "failedEvents": outcomes["failed"],
        "fallbackEvents": outcomes["fallback"],
        "ttsSucceeded": sum(item.outcome == "succeeded" for item in tts),
        "ttsFailed": sum(item.outcome in {"failed", "fallback"} for item in tts),
        "focusStarted": types["focus.started"],
        "focusCompleted": types["focus.completed"],
        "focusCompletionFailed": types["focus.completion_failed"],
        "halfwayShown": types["focus.halfway_shown"],
        "companionPreferenceChanges": types["companion.preference_changed"],
        "summaryViewed": types["summary.viewed"],
    }
