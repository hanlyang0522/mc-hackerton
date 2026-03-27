import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from ..crawling.core.utils import HttpClient

DEFAULT_REVIEWER_API_URL = "http://localhost:8000/agent/reviewer"

INPUT_SCHEMA_PATH = Path(__file__).parent.parent / "data/schemas/cover_letter_review_input.schema.json"
OUTPUT_SCHEMA_PATH = Path(__file__).parent.parent / "data/schemas/cover_letter_review_output.schema.json"
REVIEW_AGENT_PROMPT_PATH = Path(__file__).parent.parent / "data/prompts/review_agent_prompt.md"


def call_reviewer_agent(
    input_data: Dict[str, Any],
    reviewer_api_url: str,
    http_client: HttpClient,
) -> Dict[str, Any]:
    """reviewer agent HTTP API를 호출한다."""
    resp = http_client.post(reviewer_api_url, json=input_data)
    return resp.json()


def call_copilot_cli_reviewer(input_data: Dict[str, Any], cli_command: str) -> Dict[str, Any]:
    """Copilot CLI 커맨드로 reviewer를 호출한다.

    커맨드는 stdin(JSON 문자열)을 입력으로 받아 stdout(JSON 문자열)을 출력해야 한다.
    """
    completed = subprocess.run(
        cli_command,
        input=json.dumps(input_data, ensure_ascii=False),
        text=True,
        shell=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"copilot cli fallback failed: rc={completed.returncode}, stderr={completed.stderr.strip()}"
        )

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("copilot cli fallback returned non-JSON output") from exc


def _normalize_foundry_endpoint(endpoint: str) -> str:
    return endpoint.rstrip("/")


def call_foundry_reviewer(
    input_data: Dict[str, Any],
    foundry_project_endpoint: str,
    foundry_model_deployment_name: str,
    foundry_api_key: str,
    foundry_api_version: str,
    http_client: HttpClient,
) -> Dict[str, Any]:
    """Microsoft Foundry(Azure OpenAI-compatible) 모델 호출로 reviewer JSON을 생성한다."""
    if not (foundry_project_endpoint and foundry_model_deployment_name and foundry_api_key):
        raise ValueError("foundry fallback config is incomplete")

    prompt = REVIEW_AGENT_PROMPT_PATH.read_text(encoding="utf-8")
    endpoint = _normalize_foundry_endpoint(foundry_project_endpoint)
    url = (
        f"{endpoint}/openai/deployments/{foundry_model_deployment_name}/chat/completions"
        f"?api-version={foundry_api_version}"
    )

    payload = {
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(input_data, ensure_ascii=False)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    resp = http_client.post(url, json=payload, headers={"api-key": foundry_api_key})
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


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
    copilot_reviewer_cli_command: str = "",
    foundry_project_endpoint: str = "",
    foundry_model_deployment_name: str = "",
    foundry_api_key: str = "",
    foundry_api_version: str = "2024-06-01",
    http_client: Optional[HttpClient] = None,
) -> dict:
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

    errors: list[str] = []

    if reviewer_api_url:
        try:
            result = call_reviewer_agent(input_data, reviewer_api_url, client)
            validate_json_schema(result, OUTPUT_SCHEMA_PATH)
            return result
        except Exception as exc:  # pylint: disable=broad-except
            errors.append(f"primary reviewer: {exc}")

    if copilot_reviewer_cli_command:
        try:
            result = call_copilot_cli_reviewer(input_data, copilot_reviewer_cli_command)
            validate_json_schema(result, OUTPUT_SCHEMA_PATH)
            return result
        except Exception as exc:  # pylint: disable=broad-except
            errors.append(f"copilot cli fallback: {exc}")

    if foundry_project_endpoint and foundry_model_deployment_name and foundry_api_key:
        try:
            result = call_foundry_reviewer(
                input_data=input_data,
                foundry_project_endpoint=foundry_project_endpoint,
                foundry_model_deployment_name=foundry_model_deployment_name,
                foundry_api_key=foundry_api_key,
                foundry_api_version=foundry_api_version,
                http_client=client,
            )
            validate_json_schema(result, OUTPUT_SCHEMA_PATH)
            return result
        except Exception as exc:  # pylint: disable=broad-except
            errors.append(f"foundry fallback: {exc}")

    if not errors:
        raise ValueError("No reviewer path configured. Set REVIEWER_API_URL, COPILOT_REVIEWER_CLI_COMMAND, or Foundry configs.")
    raise RuntimeError("reviewer failed on all paths: " + " | ".join(errors))

