"""可评审的第一版情绪安全规则。"""

RULES_VERSION = "1"

CRISIS_TERMS = (
    "自杀",
    "自残",
    "自伤",
    "不想活",
    "不想活了",
    "结束生命",
    "活不下去",
    "死了算了",
    "kill myself",
    "hurt myself",
    "end my life",
)

ELEVATED_TERMS = (
    "快崩溃了",
    "要崩溃了",
    "撑不住了",
    "非常绝望",
    "特别绝望",
    "没有希望",
    "压力大得受不了",
    "panic attack",
    "hopeless",
)

QUOTE_OR_NEWS_MARKERS = ("新闻", "电影", "小说", "论文", "他说", "她说", "引用")
NEGATION_MARKERS = ("没有", "不会", "并不想", "从没想过")

