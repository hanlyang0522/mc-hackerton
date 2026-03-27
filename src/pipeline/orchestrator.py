from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..material_selection import MaterialSelector
from ..structure_selection import StructureSelector
from .llm_client import generate_draft, generate_outline
from .prompt_builder import build_draft_prompt, build_outline_prompt


_DB_DIR = Path(__file__).resolve().parent.parent.parent / "db"


@dataclass
class QuestionResult:
    question: str
    question_type: str | None
    material_display: str
    material_id: str
    outline: str
    draft: str
    char_count: int
    score: int
    score_breakdown: dict[str, int] = field(default_factory=dict)


@dataclass
class PipelineOutput:
    company: str
    position: str
    results: list[QuestionResult]


class CoverLetterPipeline:
    def __init__(self) -> None:
        self.material_selector = MaterialSelector()
        self.structure_selector = StructureSelector()

    def run(
        self,
        company: str,
        position: str,
        questions: list[str],
        max_lengths: list[int] | None = None,
    ) -> PipelineOutput:
        """전체 파이프라인을 실행한다.

        1. 직무분석 데이터 로드
        2. 구조 선택
        3. 소재 선택
        4. 질문별 큰틀 → 초안 생성
        """
        if max_lengths is None:
            max_lengths = [500] * len(questions)

        # 1. 직무분석 데이터 로드
        research_context, competency_keywords = self._load_research(company)

        # 2. 구조 선택 (질문 유형 분류)
        structures = self.structure_selector.select_all(questions)
        question_types = [s.question_type for s in structures]

        # 3. 소재 선택
        materials = self.material_selector.select_all(
            questions, competency_keywords, question_types
        )

        # 4. 질문별 큰틀 → 초안
        results: list[QuestionResult] = []
        for question, structure, material, max_len in zip(
            questions, structures, materials, max_lengths
        ):
            print(f"\n{'='*50}")
            print(f"질문: {question}")
            print(f"유형: {structure.question_type or '공통만'}")
            print(f"소재: {material.display} (score={material.score})")

            # 큰틀 생성
            print("  → 큰틀 생성 중...")
            outline_prompt = build_outline_prompt(
                company=company,
                position=position,
                question=question,
                structure=structure,
                material=material,
                research_context=research_context,
            )
            outline = generate_outline(outline_prompt)
            print(f"  → 큰틀 완료 ({len(outline)}자)")

            # 초안 생성
            print("  → 초안 생성 중...")
            draft_prompt = build_draft_prompt(
                question=question,
                outline=outline,
                max_length=max_len,
            )
            draft = generate_draft(draft_prompt)
            char_count = len(draft)
            print(f"  → 초안 완료 ({char_count}자 / 목표 {max_len}자)")

            results.append(QuestionResult(
                question=question,
                question_type=structure.question_type,
                material_display=material.display,
                material_id=material.material_id,
                outline=outline,
                draft=draft,
                char_count=char_count,
                score=material.score,
                score_breakdown=material.score_breakdown,
            ))

        output = PipelineOutput(
            company=company,
            position=position,
            results=results,
        )

        print(f"\n{'='*50}")
        print(f"완료: {len(results)}개 질문 처리됨")
        return output

    def _load_research(self, company: str) -> tuple[str, list[str]]:
        """직무분석 데이터를 로드한다.

        Returns:
            (research_context 문자열, competency_keywords 리스트)
        """
        # processed 폴더에서 직무분석 결과 로드
        processed_path = _DB_DIR / "processed" / f"{company}.json"
        if processed_path.exists():
            with open(processed_path, encoding="utf-8") as f:
                data = json.load(f)
            context = self._format_research_context(data)
            keywords = self._extract_keywords(data)
            return context, keywords

        # Gemini 분석 결과 로드
        gemini_dir = _DB_DIR / "gemini"
        if gemini_dir.exists():
            for p in gemini_dir.glob(f"{company}*.json"):
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                context = self._format_gemini_context(data)
                keywords = data.get("keywords", [])
                return context, keywords

        print(f"  ⚠ {company} 직무분석 데이터 없음 — 빈 컨텍스트로 진행")
        return "", []

    def _format_research_context(self, data: dict[str, Any]) -> str:
        """processed 데이터를 컨텍스트 문자열로 변환."""
        parts: list[str] = []

        # DART 사업보고서
        for item in data.get("dart_items", []):
            content = item.get("business_content", "")
            if content:
                parts.append(f"[사업보고서 {item.get('year', '')}]\n{content[:500]}")

        # 뉴스
        news = data.get("news_items", [])
        if news:
            parts.append("\n[최근 뉴스]")
            for n in news[:5]:
                parts.append(f"- {n.get('title', '')}: {n.get('summary', '')[:100]}")

        # 인재상
        talent = data.get("talent_profile")
        if talent:
            keywords = talent.get("keywords", [])
            if keywords:
                parts.append(f"\n[인재상 키워드] {', '.join(keywords)}")

        return "\n".join(parts)

    def _extract_keywords(self, data: dict[str, Any]) -> list[str]:
        """processed 데이터에서 역량 키워드를 추출."""
        keywords: list[str] = []

        talent = data.get("talent_profile")
        if talent:
            keywords.extend(talent.get("keywords", []))

        return keywords

    def _format_gemini_context(self, data: dict[str, Any]) -> str:
        """Gemini 분석 결과를 컨텍스트 문자열로 변환."""
        parts: list[str] = []

        for key in ["job_points", "recent_issues", "talent_fit"]:
            items = data.get(key, [])
            if items:
                parts.append(f"\n[{key}]")
                for item in items:
                    parts.append(f"- {item}")

        return "\n".join(parts)
