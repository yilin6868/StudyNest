"""阻止明显危险的模型最终输出。"""

import re

_BLOCKED = re.compile(
    r"我诊断你|你就是(?:抑郁|焦虑)|绝对保密|保证绝对保密|"
    r"去死|怎么自杀|自伤方法|你太矫情"
)


class SafetyOutputGuard:
    def allows(self, text: str) -> bool:
        return not _BLOCKED.search(text)

