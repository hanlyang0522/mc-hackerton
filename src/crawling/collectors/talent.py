from __future__ import annotations

import json
import os
import textwrap

import anthropic

from ..core.models import TalentProfile
from ..core.utils import HttpClient

try:
    from tavily import TavilyClient as _TavilyClient
except ImportError:  # pragma: no cover
    _TavilyClient = None  # type: ignore[assignment,misc]


_SYSTEM_PROMPT = "당신은 기업 채용 분석 전문가입니다. 반드시 JSON만 출력하세요."

_USER_TEMPLATE = textwrap.dedent(
    """\
    아래는 '{company}' 기업의 인재상·채용 문화 관련 검색 결과입니다.

    {snippets}

    위 내용을 바탕으로 '{company}'의 인재상을 아래 JSON 형식으로 정리해 주세요.
    다른 텍스트 없이 JSON만 출력하세요.

    {{
      "talent_description": "인재상 종합 설명 (3-5문장)",
      "core_values": ["핵심가치1", "핵심가치2", "...최대 8개"]
    }}
"""
)


class TalentCollector:
    """Tavily 검색 + Claude 요약으로 기업 인재상을 수집한다."""

    def __init__(
        self,
        http_client: HttpClient,
        homepage_url: str = "",
        talent_page_url: str = "",
        tavily_api_key: str = "",
        gemini_api_key: str = "",  # 하위 호환성 유지 (미사용)
        gemini_model: str = "",    # 하위 호환성 유지 (미사용)
    ) -> None:
        self.http_client = http_client
        self._tavily_api_key = tavily_api_key
        self._tavily_client = None
        self._claude_client = None

    def collect(self, company_name: str) -> TalentProfile | None:
        snippets = self._search_via_tavily(company_name)
        if not snippets:
            return None

        result = self._summarize_via_claude(company_name, snippets)
        if result is None:
            return None

        return TalentProfile(
            company=company_name,
            talent_description=result.get("talent_description", ""),
            core_values=result.get("core_values", []),
            source_snippets=snippets,
        )

    # ------------------------------------------------------------------ helpers

    def _search_via_tavily(self, company_name: str) -> list[str]:
        """Tavily로 '{기업} 인재상' 검색 후 스니펫 리스트를 반환한다."""
        if not self._tavily_api_key or _TavilyClient is None:
            return []
        if self._tavily_client is None:
            self._tavily_client = _TavilyClient(api_key=self._tavily_api_key)
        try:
            response = self._tavily_client.search(
                query=f"{company_name} 인재상 핵심가치 채용문화",
                search_depth="advanced",
                max_results=5,
            )
            results = response.get("results", [])
            snippets = []
            for r in results:
                content = (r.get("content") or r.get("description") or "").strip()
                if content:
                    snippets.append(f"[출처: {r.get('url', '')}]\n{content[:800]}")
            return snippets
        except Exception:  # pylint: disable=broad-except
            return []

    def _summarize_via_claude(
        self, company_name: str, snippets: list[str]
    ) -> dict | None:
        """Claude로 인재상을 요약·구조화한다."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        if self._claude_client is None:
            self._claude_client = anthropic.Anthropic(api_key=api_key)

        prompt = _USER_TEMPLATE.format(
            company=company_name,
            snippets="\n\n".join(snippets),
        )
        try:
            message = self._claude_client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                raw = raw.rsplit("```", 1)[0]
            return json.loads(raw)
        except Exception:  # pylint: disable=broad-except
            return None
