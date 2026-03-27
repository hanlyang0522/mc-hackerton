from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..core.models import TalentProfile
from ..core.utils import HttpClient, slugify


class TalentCollector:
    KEYWORDS = ["인재상", "핵심가치", "인재", "가치", "채용", "문화"]

    def __init__(self, http_client: HttpClient, homepage_url: str = "", talent_page_url: str = "") -> None:
        self.http_client = http_client
        self.homepage_url = homepage_url
        self.talent_page_url = talent_page_url

    def collect(self, company_name: str) -> TalentProfile | None:
        candidates = self._candidate_urls(company_name)
        for url in candidates:
            try:
                response = self.http_client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            except Exception:  # pylint: disable=broad-except
                continue

            soup = BeautifulSoup(response.text, "lxml")
            body_text = soup.get_text("\n")
            if not self._looks_like_talent_page(body_text):
                # 홈페이지에서 인재상 링크를 찾는 1차 확장
                nested = self._find_talent_link(soup, url)
                if nested:
                    try:
                        nested_response = self.http_client.get(nested, headers={"User-Agent": "Mozilla/5.0"})
                        nested_soup = BeautifulSoup(nested_response.text, "lxml")
                        body_text = nested_soup.get_text("\n")
                        url = nested
                    except Exception:  # pylint: disable=broad-except
                        pass

            if not self._looks_like_talent_page(body_text):
                continue

            sections = self._extract_sections(body_text)
            keywords = [word for word in self.KEYWORDS if word in body_text]
            excerpt = re.sub(r"\s+", " ", body_text).strip()[:3000]

            return TalentProfile(
                company=company_name,
                page_url=url,
                sections=sections,
                keywords=keywords,
                raw_excerpt=excerpt,
            )
        return None

    def _candidate_urls(self, company_name: str) -> list[str]:
        if self.talent_page_url:
            return [self.talent_page_url]

        candidates: list[str] = []
        if self.homepage_url:
            candidates.append(self.homepage_url)
        slug = slugify(company_name).replace("-", "")
        candidates.extend(
            [
                f"https://www.{slug}.co.kr",
                f"https://www.{slug}.com",
                f"https://career.{slug}.co.kr",
            ]
        )
        return candidates

    def _looks_like_talent_page(self, text: str) -> bool:
        hit_count = sum(1 for word in self.KEYWORDS if word in text)
        return hit_count >= 2

    def _find_talent_link(self, soup: BeautifulSoup, base_url: str) -> str:
        for anchor in soup.find_all("a", href=True):
            title = (anchor.get_text(" ", strip=True) or "") + " " + str(anchor.get("href", ""))
            if any(word in title for word in self.KEYWORDS):
                return urljoin(base_url, str(anchor["href"]))
        return ""

    def _extract_sections(self, text: str) -> list[str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        selected: list[str] = []
        for line in lines:
            if len(line) > 80:
                continue
            if any(keyword in line for keyword in self.KEYWORDS):
                selected.append(line)
            if len(selected) >= 20:
                break
        return selected
