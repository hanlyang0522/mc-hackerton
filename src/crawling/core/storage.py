from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .models import DartBusinessContent, NewsItem, PipelineResult, TalentProfile
from .utils import hash_key, slugify, write_json


class JsonStorage:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.raw_dir = root_dir / "raw"
        self.processed_dir = root_dir / "processed"

    def save_reviewer(
        self,
        company: str,
        job_title: str,
        review_result: dict,
        question: str = "",
    ) -> None:
        company_key = slugify(company)
        job_key = slugify(job_title) if job_title else "unknown"
        filename = f"{company_key}_{job_key}"
        if question:
            filename = f"{filename}_{hash_key(question)[:12]}"
        review_path = self.processed_dir / "review" / f"{filename}.json"
        payload = {
            "company": company,
            "job_title": job_title,
            "question": question,
            **review_result,
        }
        write_json(review_path, payload)

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
        payload = (
            asdict(profile) if profile else {"company": company, "status": "not_found"}
        )
        write_json(raw_path, payload)

    def save_gemini(self, company: str, job_title: str, insights: dict) -> None:
        company_key = slugify(company)
        job_key = slugify(job_title) if job_title else "unknown"
        raw_path = self.processed_dir / "gemini" / f"{company_key}_{job_key}.json"
        write_json(raw_path, {"company": company, "job_title": job_title, **insights})

    def save_summary(self, result: PipelineResult) -> Path:
        company_key = slugify(result.company)
        output_path = self.processed_dir / f"{company_key}.json"
        payload = asdict(result)
        write_json(output_path, payload)
        return output_path
