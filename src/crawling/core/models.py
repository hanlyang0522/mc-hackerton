from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DartBusinessContent:
    company: str
    year: int
    report_name: str
    receipt_no: str
    business_content: str
    collected_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )


@dataclass
class NewsItem:
    company: str
    title: str
    source: str
    published_at: str
    url: str
    summary: str
    provider: str
    collected_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )


@dataclass
class TalentProfile:
    company: str
    talent_description: str  # 인재상 요약 (Gemini 생성)
    core_values: list[str]  # 핵심가치 키워드 목록
    source_snippets: list[str]  # Tavily 검색 원문 발췌
    collected_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )


@dataclass
class PipelineResult:
    company: str
    dart_items: list[DartBusinessContent]
    news_items: list[NewsItem]
    talent_profile: TalentProfile | None
    errors: list[dict[str, Any]]
    collected_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
