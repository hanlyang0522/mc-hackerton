from __future__ import annotations

import io
import re
import zipfile
from datetime import date
from typing import Any

import dart_fss as dart
from bs4 import BeautifulSoup

from ..core.models import DartBusinessContent
from ..core.utils import HttpClient


class DartCollector:
    def __init__(self, api_key: str, http_client: HttpClient) -> None:
        if not api_key:
            raise ValueError("DART_API_KEY is required")
        self.api_key = api_key
        self.http_client = http_client
        dart.set_api_key(api_key=api_key)

    def collect_recent_three_years(
        self, company_name: str
    ) -> list[DartBusinessContent]:
        corp_code = self._resolve_corp_code(company_name)
        filings = self._fetch_business_reports(corp_code)

        current_year = date.today().year
        target_years = [current_year - 1, current_year - 2, current_year - 3]

        picked: dict[int, list[dict[str, Any]]] = {}
        for filing in filings:
            report_name = filing.get("report_nm", "")
            receipt_no = filing.get("rcept_no", "")
            if "사업보고서" not in report_name or not receipt_no:
                continue

            fiscal_year = self._extract_fiscal_year_from_report_name(report_name)
            if fiscal_year is None:
                continue

            if fiscal_year in target_years:
                picked.setdefault(fiscal_year, []).append(filing)

        # 3개년 중 누락된 연도는 정정 공시 등 대체 후보를 보강 탐색한다.
        for year in target_years:
            if year in picked:
                continue
            alternatives = self._find_alternative_filings_for_year(filings, year)
            if alternatives:
                picked[year] = alternatives

        results: list[DartBusinessContent] = []
        for year in target_years:
            candidates = picked.get(year, [])
            if not candidates:
                continue

            selected_report_name = ""
            selected_receipt_no = ""
            selected_business_content = ""
            selected_score = -1

            for filing in candidates:
                receipt_no = filing["rcept_no"]
                report_name = filing["report_nm"]
                document_text_candidates = self._download_document_text_candidates(
                    receipt_no
                )
                business_content = ""
                business_score = -1
                for candidate_text in document_text_candidates:
                    section = self._extract_business_section(candidate_text)
                    section_score = self._business_content_quality_score(section)
                    if section_score > business_score:
                        business_score = section_score
                        business_content = section

                score = self._business_content_quality_score(business_content)
                if score > selected_score:
                    selected_score = score
                    selected_report_name = report_name
                    selected_receipt_no = receipt_no
                    selected_business_content = business_content

            if not selected_receipt_no:
                continue

            results.append(
                DartBusinessContent(
                    company=company_name,
                    year=year,
                    report_name=selected_report_name,
                    receipt_no=selected_receipt_no,
                    business_content=selected_business_content,
                )
            )
        return sorted(results, key=lambda x: x.year, reverse=True)

    def _extract_fiscal_year_from_report_name(self, report_name: str) -> int | None:
        match = re.search(r"\((\d{4})\.\d{2}\)", report_name)
        if not match:
            return None
        return int(match.group(1))

    def _find_alternative_filings_for_year(
        self, filings: list[dict[str, Any]], year: int
    ) -> list[dict[str, Any]]:
        exact: list[dict[str, Any]] = []
        corrected: list[dict[str, Any]] = []

        for filing in filings:
            report_name = filing.get("report_nm", "")
            if "사업보고서" not in report_name:
                continue

            fiscal_year = self._extract_fiscal_year_from_report_name(report_name)
            if fiscal_year != year:
                continue

            if "정정" in report_name:
                corrected.append(filing)
            else:
                exact.append(filing)

        # 일반 사업보고서를 우선하고, 없을 때 정정 사업보고서를 사용한다.
        return exact or corrected

    def _business_content_quality_score(self, text: str) -> int:
        heading_hits = len(
            re.findall(
                r"\d+\.\s*(사업의\s*개요|주요\s*제품|원재료|매출\s*및\s*수주|위험관리|연구개발)",
                text,
            )
        )
        prose_hits = len(re.findall(r"[가-힣]{2,}", text))
        penalty = 15000 if "연결감사보고서" in text[:800] else 0
        return len(text) + (heading_hits * 4000) + prose_hits - penalty

    def _resolve_corp_code(self, company_name: str) -> str:
        corp_list = dart.get_corp_list()

        candidates: list[Any] = []
        if hasattr(corp_list, "find_by_corp_name"):
            candidates = corp_list.find_by_corp_name(company_name, exactly=False)

        if not candidates:
            raise ValueError(f"기업명을 찾을 수 없습니다: {company_name}")

        best = candidates[0]
        for candidate in candidates:
            if getattr(candidate, "corp_name", "") == company_name:
                best = candidate
                break
        corp_code = getattr(best, "corp_code", "")
        if not corp_code:
            raise ValueError(f"corp_code를 확인할 수 없습니다: {company_name}")
        return corp_code

    def _fetch_business_reports(self, corp_code: str) -> list[dict[str, Any]]:
        today = date.today().strftime("%Y%m%d")
        start = f"{date.today().year - 4}0101"
        response = self.http_client.get(
            "https://opendart.fss.or.kr/api/list.json",
            params={
                "crtfc_key": self.api_key,
                "corp_code": corp_code,
                "bgn_de": start,
                "end_de": today,
                "pblntf_ty": "A",
                "page_count": "100",
            },
        )
        payload = response.json()
        if payload.get("status") != "000":
            raise RuntimeError(
                f"DART 목록 조회 실패: {payload.get('message', payload)}"
            )
        return payload.get("list", [])

    def _download_document_text_candidates(self, receipt_no: str) -> list[str]:
        response = self.http_client.get(
            "https://opendart.fss.or.kr/api/document.xml",
            params={"crtfc_key": self.api_key, "rcept_no": receipt_no},
        )

        texts: list[str] = []
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            names = zf.namelist()
            if not names:
                return [""]

            for name in names:
                if not name.lower().endswith(
                    (".xml", ".xhtml", ".html", ".htm", ".txt")
                ):
                    continue

                raw = zf.read(name)
                parser = "xml" if name.lower().endswith(".xml") else "lxml"
                soup = BeautifulSoup(raw, parser)
                text = soup.get_text("\n").strip()
                if text:
                    texts.append(text)

        if not texts:
            # 파싱 가능한 첨부를 찾지 못한 경우에도 첫 파일을 텍스트화해서 반환 시도
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                raw = zf.read(zf.namelist()[0])
            soup = BeautifulSoup(raw, "lxml")
            fallback_text = soup.get_text("\n").strip()
            return [fallback_text]

        return texts

    def _extract_business_section(self, full_text: str) -> str:
        normalized = re.sub(r"\r\n?", "\n", full_text)
        normalized = re.sub(r"\n{2,}", "\n", normalized)

        start_patterns = [
            r"\n\s*(?:II|Ⅱ|2)\.?\s*사업의\s*내용\s*\n",
            r"\n\s*사업의\s*내용\s*\n",
            r"\n\s*영업의\s*개황\s*\n",
        ]
        end_pattern = r"\n\s*(?:III|Ⅲ|3|IV|Ⅳ|4)\.?\s*(?:재무|재무에\s*관한\s*사항)|\n\s*연결재무제표"

        # 문서 내 여러 "사업의 내용" 후보(목차/본문) 중 본문 가능성이 높은 구간을 선택한다.
        candidate_sections: list[str] = []
        for pattern in start_patterns:
            for match in re.finditer(pattern, normalized):
                start_idx = match.start()
                tail = normalized[start_idx:]
                end_match = re.search(end_pattern, tail)
                if end_match:
                    section = tail[: end_match.start()]
                else:
                    section = tail[:160000]
                section = section.strip()
                if section:
                    candidate_sections.append(section)

        if not candidate_sections:
            # 섹션 헤더를 못 찾으면 원문 앞부분 일부를 반환해 후처리 가능하게 둔다.
            return normalized[:12000].strip()

        def score(section: str) -> int:
            lines = [line.strip() for line in section.splitlines() if line.strip()]
            numeric_only = sum(
                1
                for line in lines
                if re.fullmatch(r"[0-9\-\.] +", line) or re.fullmatch(r"[0-9]+", line)
            )
            heading_hits = sum(
                1
                for line in lines
                if re.search(
                    r"\d+\.\s*(사업의\s*개요|주요\s*제품|원재료|매출\s*및\s*수주|위험관리|연구개발)",
                    line,
                )
            )
            prose_hits = len(re.findall(r"[가-힣]{2,}", section))
            # 목차형 데이터(숫자/대시 위주)를 페널티하고, 실제 문장량과 하위 항목 존재를 가산한다.
            return (
                len(section) + (heading_hits * 3000) + prose_hits - (numeric_only * 800)
            )

        best = max(candidate_sections, key=score)
        return best[:200000].strip()
