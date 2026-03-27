from __future__ import annotations

from typing import Any

from ..structure_selection.matcher import preprocess_question

# 너무 짧은 키워드는 부분 매칭에서 오탐 유발 (예: "C" in "ACM")
_MIN_KEYWORD_LENGTH = 2


def score_material(
    material: dict[str, Any],
    question: str,
    question_type: str | None,
    competency_keywords: list[str],
) -> tuple[int, dict[str, int]]:
    """단일 소재에 대한 점수를 계산한다.

    Returns:
        (total_score, breakdown_dict)
    """
    breakdown: dict[str, int] = {}

    # 질문 전처리 (동사 어미 제거)
    q_lower = preprocess_question(question).lower()

    # 1. 질문 키워드 매칭 (×3)
    keyword_hits = sum(
        1 for kw in material.get("keywords", [])
        if kw.lower() in q_lower
    )
    breakdown["keyword_match"] = keyword_hits * 3

    # 2. 역량 키워드 ↔ capabilities 매칭 (×3)
    cap_hits = _match_lists(competency_keywords, material.get("capabilities", []))
    breakdown["competency_match"] = cap_hits * 3

    # 3. 질문 유형 ↔ material.question_types 매칭 (×2)
    type_hit = 0
    if question_type and question_type in material.get("question_types", []):
        type_hit = 1
    breakdown["type_match"] = type_hit * 2

    # 4. 역량 키워드 ↔ keywords 매칭 (×2)
    cap_kw_hits = _match_lists(competency_keywords, material.get("keywords", []))
    breakdown["capability_keyword_match"] = cap_kw_hits * 2

    # 5. priority (값이 작을수록 높은 우선순위 → 역변환)
    priority_raw = material.get("priority", 3)
    priority_score = max(0, 4 - priority_raw)  # 1→3, 2→2, 3→1
    breakdown["priority"] = priority_score

    total = sum(breakdown.values())
    return total, breakdown


def _match_lists(source: list[str], target: list[str]) -> int:
    """source의 각 항목이 target의 어떤 항목에 부분 포함되는지 카운트."""
    hits = 0
    for s in source:
        s_lower = s.lower()
        if len(s_lower) < _MIN_KEYWORD_LENGTH:
            # 짧은 키워드는 완전 일치만
            if any(s_lower == t.lower() for t in target):
                hits += 1
            continue
        for t in target:
            if s_lower in t.lower() or t.lower() in s_lower:
                hits += 1
                break
    return hits
