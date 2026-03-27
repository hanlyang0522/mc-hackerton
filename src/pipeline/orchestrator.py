from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..crawling.core.config import get_settings
from ..crawling.core.storage import JsonStorage
from ..crawling.core.utils import HttpClient, slugify
from ..crawling.pipeline import CoverLetterDataPipeline
from ..material_selection import MaterialSelector
from ..structure_selection import StructureSelector
from .llm_client import generate_draft, generate_outline
from .prompt_builder import build_draft_prompt, build_outline_prompt
from .review_integration import review_essay


_DB_DIR = Path(__file__).resolve().parent.parent.parent / "db"
_BANNED_WORDS_PATH = Path(__file__).resolve().parent.parent / "data" / "banned_words.json"


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
    review_result: dict[str, Any] | None = None


@dataclass
class PipelineOutput:
    company: str
    position: str
    results: list[QuestionResult]


class CoverLetterPipeline:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.material_selector = MaterialSelector()
        self.structure_selector = StructureSelector()
        self.storage = JsonStorage(_DB_DIR)
        self.http_client = HttpClient(
            timeout_seconds=self.settings.request_timeout_seconds,
            retry_count=self.settings.request_retry_count,
            sleep_seconds=self.settings.request_sleep_seconds,
        )
        self.banned_words = self._load_banned_words()

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

        # 1. 크롤링 실행
        print(f"  → {company} 직무분석 크롤링 중...")
        crawl_pipeline = CoverLetterDataPipeline(db_root=_DB_DIR)
        crawl_pipeline.run(company, job_title=position)

        # 2. 직무분석 데이터 로드
        research_context, competency_keywords = self._load_research(company)

        # 3. 구조 선택 (질문 유형 분류)
        structures = self.structure_selector.select_all(questions)
        question_types = [s.question_type for s in structures]

        # 4. 소재 선택
        materials = self.material_selector.select_all(
            questions, competency_keywords, question_types
        )

        # 5. 질문별 큰틀 → 초안
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

            # 1차 reviewer 실행 (글자수 + 표현 검수)
            review_result = self._review_draft(
                company=company,
                position=position,
                question=question,
                draft=draft,
                max_length=max_len,
            )
            if review_result is not None:
                review_pass = review_result.get("pass", False)
                char_check = review_result.get("char_check", {})
                counted = char_check.get("counted_chars", char_count)
                print(f"  → 1차 reviewer 완료 (pass={review_pass}, {counted}자/{max_len}자)")

                if not review_pass:
                    # 표현+글자수 보정 재생성 (1회)
                    print("  → 재생성 중 (글자수/표현 보정)...")
                    rewrite_prompt = build_draft_prompt(
                        question=question,
                        outline=outline,
                        max_length=max_len,
                    )
                    draft = generate_draft(rewrite_prompt)
                    char_count = len(draft)
                    print(f"  → 재생성 완료 ({char_count}자 / 목표 {max_len}자)")

                    # 2차 reviewer 실행 (글자수 10% 이내면 통과)
                    review_result = self._review_draft(
                        company=company,
                        position=position,
                        question=question,
                        draft=draft,
                        max_length=max_len,
                    )
                    if review_result is not None:
                        char_check2 = review_result.get("char_check", {})
                        counted2 = char_check2.get("counted_chars", char_count)
                        within_10pct = abs(counted2 - max_len) / max_len <= 0.10
                        print(f"  → 2차 reviewer 완료 ({counted2}자, 10%이내={within_10pct})")

                self.storage.save_reviewer(
                    company=company,
                    job_title=position,
                    question=question,
                    review_result=review_result,
                )
                review_score = review_result.get("score", "-")
                print(f"  → 최종 score={review_score}, {len(draft)}자")

            results.append(QuestionResult(
                question=question,
                question_type=structure.question_type,
                material_display=material.display,
                material_id=material.material_id,
                outline=outline,
                draft=draft,
                char_count=len(draft),
                score=material.score,
                score_breakdown=material.score_breakdown,
                review_result=review_result,
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
        company_key = slugify(company)

        # processed 폴더에서 직무분석 결과 로드
        processed_path = _DB_DIR / "processed" / f"{company_key}.json"
        if processed_path.exists():
            with open(processed_path, encoding="utf-8") as f:
                data = json.load(f)
            context = self._format_research_context(data)
            keywords = self._extract_keywords(data)
            return context, keywords

        # Gemini 분석 결과 로드
        gemini_dir = _DB_DIR / "processed" / "gemini"
        if gemini_dir.exists():
            for p in gemini_dir.glob(f"{company_key}*.json"):
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                context = self._format_gemini_context(data)
                keywords = data.get("keywords_for_cover_letter", [])
                return context, keywords

        print(f"  ⚠ {company} 직무분석 데이터 로드 실패 — 빈 컨텍스트로 진행")
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
            keywords = talent.get("core_values", [])
            if keywords:
                parts.append(f"\n[인재상 키워드] {', '.join(keywords)}")

        return "\n".join(parts)

    def _extract_keywords(self, data: dict[str, Any]) -> list[str]:
        """processed 데이터에서 역량 키워드를 추출."""
        keywords: list[str] = []

        talent = data.get("talent_profile")
        if talent:
            keywords.extend(talent.get("core_values", []))

        return keywords

    def _format_gemini_context(self, data: dict[str, Any]) -> str:
        """Gemini 분석 결과를 컨텍스트 문자열로 변환."""
        parts: list[str] = []

        summary = data.get("business_summary", "")
        if summary:
            parts.append(f"[business_summary]\n{summary}")

        for key in ["job_relevant_points", "recent_issues", "talent_alignment"]:
            items = data.get(key, [])
            if items:
                parts.append(f"\n[{key}]")
                for item in items:
                    parts.append(f"- {item}")

        return "\n".join(parts)

    def _load_banned_words(self) -> list[str]:
        with open(_BANNED_WORDS_PATH, encoding="utf-8") as f:
            return json.load(f)

    def _review_draft(
        self,
        company: str,
        position: str,
        question: str,
        draft: str,
        max_length: int,
    ) -> dict[str, Any] | None:
        if not self.settings.reviewer_api_url:
            if not self.settings.copilot_reviewer_cli_command:
                if not (
                    self.settings.foundry_project_endpoint
                    and self.settings.foundry_model_deployment_name
                    and self.settings.foundry_api_key
                ):
                    return None

        try:
            return review_essay(
                company=company,
                job_title=position,
                question=question,
                essay=draft,
                char_policy={
                    "mode": "max_only",
                    "max": max_length,
                    "count_spaces": True,
                    "enforce_90_95_rule": True,
                },
                banned_words=self.banned_words,
                reviewer_api_url=self.settings.reviewer_api_url,
                copilot_reviewer_cli_command=self.settings.copilot_reviewer_cli_command,
                foundry_project_endpoint=self.settings.foundry_project_endpoint,
                foundry_model_deployment_name=self.settings.foundry_model_deployment_name,
                foundry_api_key=self.settings.foundry_api_key,
                foundry_api_version=self.settings.foundry_api_version,
                http_client=self.http_client,
            )
        except Exception as exc:  # pylint: disable=broad-except
            print(f"  → reviewer 건너뜀: {exc}")
            return None
