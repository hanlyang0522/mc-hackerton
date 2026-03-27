from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import AllocationResult
from .scorer import score_material


_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class MaterialSelector:
    def __init__(self, materials: list[dict[str, Any]] | None = None) -> None:
        if materials is not None:
            self.materials = materials
        else:
            with open(_DATA_DIR / "materials.json", encoding="utf-8") as f:
                self.materials = json.load(f)

    def select_all(
        self,
        questions: list[str],
        competency_keywords: list[str],
        question_types: list[str | None] | None = None,
    ) -> list[AllocationResult]:
        """모든 질문에 대해 소재를 배정한다. 중복 방지 적용."""
        if question_types is None:
            question_types = [None] * len(questions)

        used: set[str] = set()
        results: list[AllocationResult] = []

        for question, q_type in zip(questions, question_types):
            result = self._select_one(question, q_type, competency_keywords, used)
            used.add(result.material_id)
            results.append(result)

        return results

    def _select_one(
        self,
        question: str,
        question_type: str | None,
        competency_keywords: list[str],
        used: set[str],
    ) -> AllocationResult:
        """단일 질문에 대해 최적 소재를 선택한다."""
        scored: list[tuple[int, dict[str, int], dict[str, Any]]] = []

        for mat in self.materials:
            total, breakdown = score_material(
                mat, question, question_type, competency_keywords
            )
            scored.append((total, breakdown, mat))

        # 점수 내림차순 정렬. 동점이면 priority 오름차순 (값이 작을수록 우선)
        scored.sort(key=lambda x: (-x[0], x[2].get("priority", 3)))

        # used에 없는 것 중 최고점 선택
        for total, breakdown, mat in scored:
            if mat["id"] not in used:
                return AllocationResult(
                    question=question,
                    material_id=mat["id"],
                    display=mat["display"],
                    activity_key=mat["activity_key"],
                    activity_detail=mat.get("activity_detail", {}),
                    score=total,
                    score_breakdown=breakdown,
                )

        # 모든 소재가 used인 경우 (질문 수 > 소재 수) → 최고점 소재 재사용
        top = scored[0]
        return AllocationResult(
            question=question,
            material_id=top[2]["id"],
            display=top[2]["display"],
            activity_key=top[2]["activity_key"],
            activity_detail=top[2].get("activity_detail", {}),
            score=top[0],
            score_breakdown=top[1],
        )
