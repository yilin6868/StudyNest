"""在模型和工具之前执行的确定性安全分类。"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from .rules_v1 import (
    CRISIS_TERMS,
    ELEVATED_TERMS,
    NEGATION_MARKERS,
    QUOTE_OR_NEWS_MARKERS,
    RULES_VERSION,
)

SafetyLevel = Literal["normal", "elevated", "crisis"]


@dataclass(frozen=True)
class SafetyResult:
    level: SafetyLevel
    rule_id: str
    rules_version: str = RULES_VERSION


class SafetyClassifier:
    @staticmethod
    def normalize(text: str) -> str:
        value = unicodedata.normalize("NFKC", text).lower()
        value = re.sub(r"[\s\u200b]+", "", value)
        return re.sub(r"([!！?？。，,.])\1+", r"\1", value)

    def classify(self, text: str) -> SafetyResult:
        value = self.normalize(text)
        quoted = any(marker in value for marker in QUOTE_OR_NEWS_MARKERS)
        for index, term in enumerate(CRISIS_TERMS, start=1):
            clean_term = term.replace(" ", "")
            self_directed = re.search(r"我.{0,8}" + re.escape(clean_term), value)
            negated = any(marker + clean_term in value for marker in NEGATION_MARKERS)
            if clean_term in value and not negated and (not quoted or self_directed):
                return SafetyResult("crisis", f"crisis_{index:02d}")
        for index, term in enumerate(ELEVATED_TERMS, start=1):
            if term.replace(" ", "") in value and not quoted:
                return SafetyResult("elevated", f"elevated_{index:02d}")
        return SafetyResult("normal", "normal_00")
