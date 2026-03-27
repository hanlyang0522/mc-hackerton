from __future__ import annotations

import json
from typing import Any

from ..material_selection.models import AllocationResult
from ..structure_selection.models import StructureResult


def build_outline_prompt(
    company: str,
    position: str,
    question: str,
    structure: StructureResult,
    material: AllocationResult,
    research_context: str,
) -> str:
    """큰틀 작성용 user prompt를 조립한다.

    큰틀 LLM에게 전달할 정보:
    - 회사/직무 컨텍스트 (직무분석 결과)
    - 질문 + 유형 + 글 구조 (flow/core/caution)
    - 소재 상세 데이터 (activity_detail)
    """
    parts: list[str] = []

    # 회사 컨텍스트
    parts.append(f"[회사/직무 정보]\n회사: {company}\n직무: {position}")
    parts.append(f"\n[직무 분석 결과]\n{research_context}")

    # 질문 + 구조
    parts.append(f"\n[질문]\n{question}")

    if structure.question_type:
        parts.append(f"\n[질문 유형] {structure.question_type}")
        parts.append("\n[글 구조 — 이 흐름을 따라 큰틀을 작성하세요]")
        for step in structure.flow:
            parts.append(f"  {step}")
        if structure.core:
            parts.append(f"\n[핵심] {structure.core}")
        if structure.caution:
            parts.append(f"\n[주의] {structure.caution}")
    else:
        parts.append("\n[질문 유형] 매칭 실패 — 공통 규칙만 적용")

    parts.append("\n[공통 규칙]")
    for rule in structure.common_rules:
        parts.append(f"  - {rule}")

    # 소재
    parts.append(f"\n[배정된 소재] {material.display}")
    detail = material.activity_detail
    if detail:
        parts.append(f"\n[소재 상세 데이터]\n{json.dumps(detail, ensure_ascii=False, indent=2)}")

    # 큰틀 작성 지시
    parts.append("\n---")
    parts.append("위 정보를 바탕으로 이 질문에 대한 큰틀을 작성하세요.")
    parts.append("큰틀은 최종 자소서의 뼈대입니다. 다음을 포함해야 합니다:")
    parts.append("  - 글의 전체 흐름 (문단별 핵심 내용)")
    parts.append("  - 사용할 구체적 팩트/경험 (소재 데이터에서 추출)")
    parts.append("  - 회사/직무와의 연결 포인트")
    parts.append("  - 각 문단의 핵심 메시지")
    parts.append("표현은 다듬지 않아도 됩니다. 내용과 구조에만 집중하세요.")

    return "\n".join(parts)


def build_draft_prompt(
    question: str,
    outline: str,
    max_length: int,
) -> str:
    """초안 작성용 user prompt를 조립한다.

    초안 LLM에게 전달할 정보:
    - 큰틀 (내용/구조 확정)
    - 글자수 제한
    - 표현 집중 지시
    """
    parts: list[str] = []

    parts.append(f"[질문]\n{question}")
    parts.append(f"\n[큰틀]\n{outline}")
    parts.append(f"\n[글자수] {max_length}자 (공백 포함)")

    parts.append("\n---")
    parts.append("위 큰틀을 바탕으로 완성된 자소서를 작성하세요.")
    parts.append("큰틀의 내용과 구조는 그대로 유지하되, 표현에 집중하세요:")
    parts.append("  - 시스템 프롬프트의 Humanizing 규칙 반드시 적용")
    parts.append("  - 긴 문장과 짧은 문장을 의도적으로 섞을 것")
    parts.append("  - 접속사 없이 문맥 흐름으로 연결")
    parts.append("  - 솔직한 감정 표현 적절히 삽입")
    parts.append("  - 금지 표현 사용 금지")
    parts.append(f"  - 글자수 {max_length}자에 맞출 것 (남는 글자수 100자 이내)")

    return "\n".join(parts)
