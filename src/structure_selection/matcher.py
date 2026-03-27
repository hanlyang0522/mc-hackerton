from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# 질문 끝에 붙는 동사 어미 — 키워드 매칭 전에 제거해야 오탐 방지
_QUESTION_SUFFIXES = [
    r"기술하[시세]오\.?",
    r"기술하십시오\.?",
    r"기술해\s*주[시세]?[오요]?\.?",
    r"서술하[시세]오\.?",
    r"서술하십시오\.?",
    r"서술해\s*주[시세]?[오요]?\.?",
    r"작성하[시세]오\.?",
    r"작성하십시오\.?",
    r"작성해\s*주[시세]?[오요]?\.?",
    r"설명하[시세]오\.?",
    r"설명하십시오\.?",
    r"설명해\s*주[시세]?[오요]?\.?",
    r"기재하[시세]오\.?",
    r"기재하십시오\.?",
    r"말씀해\s*주[시세]?[오요]?\.?",
]
_SUFFIX_PATTERN = re.compile("|".join(_QUESTION_SUFFIXES))

# 질문 앞에 붙는 번호/라벨 제거
_PREFIX_PATTERN = re.compile(r"^[\s]*(?:문항\s*\d+[\.\):]?\s*|Q\d+[\.\):]?\s*|\d+[\.\)]\s*|\[.*?\]\s*)")


def load_question_types() -> dict[str, Any]:
    with open(_DATA_DIR / "question_types.json", encoding="utf-8") as f:
        return json.load(f)


def preprocess_question(question: str) -> str:
    """질문에서 동사 어미와 번호 접두사를 제거한다."""
    cleaned = _PREFIX_PATTERN.sub("", question)
    cleaned = _SUFFIX_PATTERN.sub("", cleaned)
    return cleaned.strip()


def match_question_type(
    question: str,
    type_data: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, int]:
    """질문 문자열에서 유형을 매칭한다.

    Returns:
        (매칭된 유형 dict 또는 None, 매칭 히트 수)
    """
    if type_data is None:
        type_data = load_question_types()

    cleaned = preprocess_question(question)
    q_lower = cleaned.lower()

    best_match: dict[str, Any] | None = None
    best_hits = 0

    for t in type_data.get("types", []):
        hits = sum(1 for kw in t.get("keywords", []) if kw in q_lower)
        if hits > best_hits:
            best_hits = hits
            best_match = t

    return best_match, best_hits
