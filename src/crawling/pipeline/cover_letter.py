from __future__ import annotations

from pathlib import Path

from ..collectors.dart import DartCollector
from ..collectors.news import (
    ApiNewsProvider,
    MCPNewsProvider,
    NewsCollector,
    TavilyNewsProvider,
)
from ..collectors.talent import TalentCollector
from ..core.config import get_settings
from ..core.models import PipelineResult
from ..core.storage import JsonStorage
from ..core.utils import HttpClient
from .gemini_extractor import GeminiExtractor


class CoverLetterDataPipeline:
    def __init__(self, db_root: Path) -> None:
        self.settings = get_settings()
        self.http_client = HttpClient(
            timeout_seconds=self.settings.request_timeout_seconds,
            retry_count=self.settings.request_retry_count,
            sleep_seconds=self.settings.request_sleep_seconds,
        )
        self.storage = JsonStorage(db_root)

    def run(self, company_name: str, job_title: str = "") -> Path:
        errors: list[dict[str, str]] = []

        dart_items = []
        try:
            dart_collector = DartCollector(self.settings.dart_api_key, self.http_client)
            dart_items = dart_collector.collect_recent_three_years(company_name)
        except Exception as exc:  # pylint: disable=broad-except
            errors.append({"stage": "dart", "error": str(exc)})

        news_items = []
        try:
            tavily_provider = TavilyNewsProvider(api_key=self.settings.tavily_api_key)
            api_provider = ApiNewsProvider(
                endpoint=self.settings.news_api_endpoint,
                client_id=self.settings.news_api_client_id,
                client_secret=self.settings.news_api_client_secret,
                http_client=self.http_client,
            )
            mcp_provider = MCPNewsProvider(
                endpoint=self.settings.mcp_news_endpoint,
                auth_token=self.settings.mcp_news_auth_token,
                http_client=self.http_client,
            )
            news_collector = NewsCollector(
                tavily_provider,
                api_provider,
                mcp_provider,
                self.settings.max_news_items,
            )
            news_items = news_collector.collect(company_name)
        except Exception as exc:  # pylint: disable=broad-except
            errors.append({"stage": "news", "error": str(exc)})

        talent_profile = None
        try:
            talent_collector = TalentCollector(
                http_client=self.http_client,
                homepage_url=self.settings.company_homepage_url,
                talent_page_url=self.settings.talent_page_url,
                tavily_api_key=self.settings.tavily_api_key,
                gemini_api_key=self.settings.gemini_api_key,
            )
            talent_profile = talent_collector.collect(company_name)
        except Exception as exc:  # pylint: disable=broad-except
            errors.append({"stage": "talent", "error": str(exc)})

        result = PipelineResult(
            company=company_name,
            dart_items=dart_items,
            news_items=news_items,
            talent_profile=talent_profile,
            errors=errors,
        )

        gemini_insights: dict | None = None
        if job_title and self.settings.gemini_api_key:
            try:
                extractor = GeminiExtractor(api_key=self.settings.gemini_api_key)
                gemini_insights = extractor.extract(
                    company=company_name,
                    job_title=job_title,
                    dart_items=dart_items,
                    news_items=news_items,
                    talent_profile=talent_profile,
                )
            except Exception as exc:  # pylint: disable=broad-except
                errors.append({"stage": "gemini", "error": str(exc)})

        self.storage.save_dart(company_name, dart_items)
        self.storage.save_news(company_name, news_items)
        self.storage.save_talent(company_name, talent_profile)
        if gemini_insights is not None:
            self.storage.save_gemini(company_name, job_title, gemini_insights)
        return self.storage.save_summary(result)
