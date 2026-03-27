from __future__ import annotations

from typing import Any

from .matcher import load_question_types, match_question_type
from .models import StructureResult


# 히트 수가 이 값 이하면 매칭 신뢰도가 낮다고 판단
_LOW_CONFIDENCE_THRESHOLD = 0


class StructureSelector:
    def __init__(self, type_data: dict[str, Any] | None = None) -> None:
        self.type_data = type_data or load_question_types()

    def select(self, question: str) -> StructureResult:
        """질문에 맞는 글 구조를 반환한다."""
        common_rules = self.type_data.get("common_structure", {}).get("rules", [])
        matched, hits = match_question_type(question, self.type_data)

        if matched and hits > _LOW_CONFIDENCE_THRESHOLD:
            return StructureResult(
                question=question,
                question_type=matched["type"],
                common_rules=common_rules,
                flow=matched.get("flow", []),
                core=matched.get("core"),
                caution=matched.get("caution"),
            )

        return StructureResult(
            question=question,
            question_type=None,
            common_rules=common_rules,
        )

    def select_all(self, questions: list[str]) -> list[StructureResult]:
        """여러 질문에 대해 구조를 반환한다."""
        return [self.select(q) for q in questions]
