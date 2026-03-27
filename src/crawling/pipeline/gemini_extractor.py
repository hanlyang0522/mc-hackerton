"""Gemini API를 이용해 수집 데이터에서 직무 관련 핵심 정보를 추출한다."""

from __future__ import annotations

import json
import textwrap

from google import genai

from ..core.models import DartBusinessContent, NewsItem


_SYSTEM_PROMPT = textwrap.dedent(
    """\
    당신은 취업 자소서 작성 전문가입니다.
    주어진 기업 데이터(DART 사업보고서, 뉴스 기사)를 바탕으로
    지원 직무와 관련된 핵심 정보만 간결하게 정리해 주세요.
    반드시 JSON 형식으로만 응답하세요.
"""
)

_USER_TEMPLATE = textwrap.dedent(
    """\
    ## 지원 기업: {company}
    ## 지원 직무: {job_title}

    ---
    ## DART 사업보고서 (최근 3개년)
    {dart_section}

    ---
    ## 최신 뉴스
    {news_section}

    ---
    위 내용을 참고하여 **"{job_title}"** 직무 지원자에게 유용한 정보를 아래 JSON 형식으로 추출해 주세요.
    다른 텍스트 없이 JSON만 출력하세요.

    {{
      "business_summary": "사업 전반 요약 (3-5문장)",
      "job_relevant_points": [
        "직무와 직접 관련된 핵심 포인트 (최대 8개, 구체적인 수치·사업명 포함)"
      ],
      "recent_issues": [
        "최근 1-2년 내 주요 변화·이슈 (최대 5개)"
      ],
      "keywords_for_cover_letter": [
        "자소서에 활용할 키워드 (최대 10개)"
      ]
    }}
"""
)


class GeminiExtractor:
    """Gemini API로 수집 데이터에서 직무 관련 핵심 정보를 추출한다."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def extract(
        self,
        company: str,
        job_title: str,
        dart_items: list[DartBusinessContent],
        news_items: list[NewsItem],
    ) -> dict:
        """직무 관련 핵심 정보를 추출해 dict로 반환한다."""
        dart_section = self._format_dart(dart_items)
        news_section = self._format_news(news_items)

        prompt = _USER_TEMPLATE.format(
            company=company,
            job_title=job_title,
            dart_section=dart_section,
            news_section=news_section,
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config={"system_instruction": _SYSTEM_PROMPT},
        )

        raw = response.text.strip()
        # 마크다운 코드블록 제거
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            raw = raw.rsplit("```", 1)[0]

        return json.loads(raw)

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _format_dart(items: list[DartBusinessContent]) -> str:
        if not items:
            return "(DART 데이터 없음)"
        parts = []
        for item in items:
            header = f"### {item.year}년 {item.report_name}"
            # 너무 길면 앞부분만 사용 (토큰 절약)
            content = item.business_content[:6000]
            parts.append(f"{header}\n{content}")
        return "\n\n".join(parts)

    @staticmethod
    def _format_news(items: list[NewsItem]) -> str:
        if not items:
            return "(뉴스 데이터 없음)"
        lines = []
        for item in items[:20]:  # 최대 20건
            date_str = item.published_at[:10] if item.published_at else ""
            summary = item.summary or item.title
            lines.append(f"- [{date_str}] {item.title}\n  {summary}")
        return "\n".join(lines)
