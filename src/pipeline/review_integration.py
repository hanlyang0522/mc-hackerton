import json
from pathlib import Path
from typing import Any, Dict

from ..crawling.core.utils import HttpClient

DEFAULT_REVIEWER_API_URL = "http://localhost:8000/agent/reviewer"

INPUT_SCHEMA_PATH = Path(__file__).parent.parent / "data/schemas/cover_letter_review_input.schema.json"
OUTPUT_SCHEMA_PATH = Path(__file__).parent.parent / "data/schemas/cover_letter_review_output.schema.json"


def call_reviewer_agent(
    input_data: Dict[str, Any],
    reviewer_api_url: str,
    http_client: HttpClient,
) -> Dict[str, Any]:
    """reviewer agent HTTP API를 호출한다."""
    resp = http_client.post(reviewer_api_url, json=input_data)
    return resp.json()


def validate_json_schema(data: Dict[str, Any], schema_path: Path) -> None:
    import jsonschema

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema.validate(instance=data, schema=schema)


def build_reviewer_input(
    company: str,
    job_title: str,
    question: str,
    essay: str,
    char_policy: dict,
    banned_words: list[str],
) -> dict:
    return {
        "company": company,
        "job_title": job_title,
        "question": question,
        "essay": essay,
        "char_policy": char_policy,
        "banned_words": banned_words,
    }


def review_essay(
    company: str,
    job_title: str,
    question: str,
    essay: str,
    char_policy: dict,
    banned_words: list[str],
    reviewer_api_url: str = DEFAULT_REVIEWER_API_URL,
    http_client: HttpClient | None = None,
) -> dict:
    if not reviewer_api_url:
        raise ValueError("REVIEWER_API_URL is not configured")

    client = http_client or HttpClient(timeout_seconds=30, retry_count=1, sleep_seconds=0.0)
    input_data = build_reviewer_input(
        company,
        job_title,
        question,
        essay,
        char_policy,
        banned_words,
    )
    validate_json_schema(input_data, INPUT_SCHEMA_PATH)
    result = call_reviewer_agent(input_data, reviewer_api_url, client)
    validate_json_schema(result, OUTPUT_SCHEMA_PATH)
    return result

