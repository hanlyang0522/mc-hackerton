from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .models import DartBusinessContent, NewsItem, PipelineResult, TalentProfile
from .utils import slugify, write_json


class JsonStorage:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.raw_dir = root_dir / "raw"
        self.processed_dir = root_dir / "processed"

    def save_dart(self, company: str, items: list[DartBusinessContent]) -> None:
        company_key = slugify(company)
        raw_path = self.raw_dir / "dart" / f"{company_key}.json"
        payload = [asdict(item) for item in items]
        write_json(raw_path, payload)

    def save_news(self, company: str, items: list[NewsItem]) -> None:
        company_key = slugify(company)
        raw_path = self.raw_dir / "news" / f"{company_key}.json"
        payload = [asdict(item) for item in items]
        write_json(raw_path, payload)

    def save_talent(self, company: str, profile: TalentProfile | None) -> None:
        company_key = slugify(company)
        raw_path = self.raw_dir / "talent" / f"{company_key}.json"
        payload = asdict(profile) if profile else {"company": company, "status": "not_found"}
        write_json(raw_path, payload)

    def save_summary(self, result: PipelineResult) -> Path:
        company_key = slugify(result.company)
        output_path = self.processed_dir / f"{company_key}.json"
        payload = asdict(result)
        write_json(output_path, payload)
        return output_path
