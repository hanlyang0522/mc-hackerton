from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ..core.models import NewsItem
from ..core.utils import HttpClient, hash_key, strip_html

try:
    from tavily import TavilyClient as _TavilyClient
except ImportError:  # pragma: no cover
    _TavilyClient = None  # type: ignore[assignment,misc]


class TavilyNewsProvider:
    """Tavily Search API를 사용한 뉴스 수집 provider."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = None

    def enabled(self) -> bool:
        return bool(self.api_key and _TavilyClient is not None)

    def _get_client(self):
        if self._client is None:
            self._client = _TavilyClient(api_key=self.api_key)
        return self._client

    def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        if not self.enabled():
            return []
        client = self._get_client()
        response = client.search(
            query=query,
            search_depth="advanced",
            topic="news",
            max_results=min(limit, 20),
        )
        results = response.get("results", [])
        normalized: list[dict[str, Any]] = []
        for r in results:
            normalized.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "link": r.get("url", ""),
                    "description": r.get("content", ""),
                    "source": r.get("source", "tavily"),
                    "pubDate": r.get("published_date", ""),
                }
            )
        return normalized


class ApiNewsProvider:
    def __init__(
        self,
        endpoint: str,
        client_id: str,
        client_secret: str,
        http_client: HttpClient,
    ) -> None:
        self.endpoint = endpoint
        self.client_id = client_id
        self.client_secret = client_secret
        self.http_client = http_client

    def enabled(self) -> bool:
        return bool(self.client_id and self.client_secret and self.endpoint)

    def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        if not self.enabled():
            return []
        response = self.http_client.get(
            self.endpoint,
            params={"query": query, "display": str(limit), "sort": "date"},
            headers={
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
            },
        )
        payload = response.json()
        return payload.get("items", [])


class MCPNewsProvider:
    def __init__(self, endpoint: str, auth_token: str, http_client: HttpClient) -> None:
        self.endpoint = endpoint
        self.auth_token = auth_token
        self.http_client = http_client

    def enabled(self) -> bool:
        return bool(self.endpoint)

    def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        if not self.enabled():
            return []
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        response = self.http_client.post(
            self.endpoint,
            json={"query": query, "limit": limit},
            headers=headers,
        )
        payload = response.json()
        items = payload.get("items", [])
        if not isinstance(items, list):
            return []
        return items


class NewsCollector:
    def __init__(
        self,
        tavily_provider: TavilyNewsProvider,
        api_provider: ApiNewsProvider,
        mcp_provider: MCPNewsProvider,
        max_items: int,
    ) -> None:
        self.tavily_provider = tavily_provider
        self.api_provider = api_provider
        self.mcp_provider = mcp_provider
        self.max_items = max_items

    def collect(self, company_name: str) -> list[NewsItem]:
        today = datetime.today()
        from_date = (today - timedelta(days=180)).strftime("%Y-%m-%d")
        query = f"{company_name} 최근 이슈 사업 동향"

        # 1순위: Tavily
        raw_items = self.tavily_provider.search(query, self.max_items)
        provider = "tavily"
        # 2순위: Naver API
        if not raw_items:
            raw_items = self.api_provider.search(
                f"{company_name} 최근 이슈 사업 동향 {from_date}", self.max_items
            )
            provider = "api"
        # 3순위: MCP fallback
        if not raw_items:
            raw_items = self.mcp_provider.search(query, self.max_items)
            provider = "mcp"

        dedup: dict[str, NewsItem] = {}
        for item in raw_items:
            title = strip_html(str(item.get("title", "")))
            link = str(item.get("link") or item.get("url") or "")
            if not title or not link:
                continue

            source = str(item.get("originallink") or item.get("source") or "unknown")
            summary = strip_html(
                str(item.get("description") or item.get("summary") or "")
            )
            published = str(item.get("pubDate") or item.get("publishedAt") or "")

            key = hash_key(title, link)
            dedup[key] = NewsItem(
                company=company_name,
                title=title,
                source=source,
                published_at=published,
                url=link,
                summary=summary,
                provider=provider,
            )

        items = list(dedup.values())
        items.sort(key=lambda x: x.published_at, reverse=True)
        return items[: self.max_items]
