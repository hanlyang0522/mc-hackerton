from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    dart_api_key: str
    tavily_api_key: str
    gemini_api_key: str
    reviewer_api_url: str
    news_api_endpoint: str
    news_api_client_id: str
    news_api_client_secret: str
    mcp_news_endpoint: str
    mcp_news_auth_token: str
    request_timeout_seconds: int
    request_retry_count: int
    request_sleep_seconds: float
    max_news_items: int
    company_homepage_url: str
    talent_page_url: str


def get_settings() -> Settings:
    return Settings(
        dart_api_key=os.getenv("DART_API_KEY", "").strip(),
        tavily_api_key=os.getenv("TAVILY_API_KEY", "").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        reviewer_api_url=os.getenv("REVIEWER_API_URL", "").strip(),
        news_api_endpoint=os.getenv(
            "NEWS_API_ENDPOINT", "https://openapi.naver.com/v1/search/news.json"
        ).strip(),
        news_api_client_id=os.getenv("NEWS_API_CLIENT_ID", "").strip(),
        news_api_client_secret=os.getenv("NEWS_API_CLIENT_SECRET", "").strip(),
        mcp_news_endpoint=os.getenv("MCP_NEWS_ENDPOINT", "").strip(),
        mcp_news_auth_token=os.getenv("MCP_NEWS_AUTH_TOKEN", "").strip(),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
        request_retry_count=int(os.getenv("REQUEST_RETRY_COUNT", "3")),
        request_sleep_seconds=float(os.getenv("REQUEST_SLEEP_SECONDS", "0.2")),
        max_news_items=int(os.getenv("MAX_NEWS_ITEMS", "20")),
        company_homepage_url=os.getenv("COMPANY_HOMEPAGE_URL", "").strip(),
        talent_page_url=os.getenv("TALENT_PAGE_URL", "").strip(),
    )
