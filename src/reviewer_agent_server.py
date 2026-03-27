from __future__ import annotations

import json
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import jsonschema


_DATA_DIR = Path(__file__).resolve().parent / "data" / "schemas"
_INPUT_SCHEMA_PATH = _DATA_DIR / "cover_letter_review_input.schema.json"
_OUTPUT_SCHEMA_PATH = _DATA_DIR / "cover_letter_review_output.schema.json"


def _load_schema(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


INPUT_SCHEMA = _load_schema(_INPUT_SCHEMA_PATH)
OUTPUT_SCHEMA = _load_schema(_OUTPUT_SCHEMA_PATH)


@dataclass
class CharCheckResult:
    passed: bool
    counted_chars: int
    utilization_ratio: float
    utilization_pass: bool
    expected: dict[str, int]
    message: str


def _count_chars(text: str, count_spaces: bool) -> int:
    return len(text if count_spaces else text.replace(" ", ""))


def _expected_from_policy(char_policy: dict[str, Any]) -> dict[str, int]:
    expected: dict[str, int] = {}
    for key in ("target", "min", "max"):
        value = char_policy.get(key)
        if isinstance(value, int):
            expected[key] = value
    return expected


def _get_base_limit(char_policy: dict[str, Any]) -> int | None:
    mode = char_policy.get("mode", "")
    if mode == "exact":
        return char_policy.get("target")
    if mode == "max_only":
        return char_policy.get("max")
    if mode == "range":
        return char_policy.get("max")
    return None


def _check_char_policy(essay: str, char_policy: dict[str, Any]) -> CharCheckResult:
    mode = char_policy["mode"]
    count_spaces = char_policy.get("count_spaces", True)
    counted_chars = _count_chars(essay, count_spaces)

    expected = _expected_from_policy(char_policy)

    if mode == "exact":
        mode_pass = counted_chars == char_policy["target"]
        mode_message = f"exact 기준: {char_policy['target']}자"
    elif mode == "range":
        mode_pass = char_policy["min"] <= counted_chars <= char_policy["max"]
        mode_message = f"range 기준: {char_policy['min']}~{char_policy['max']}자"
    elif mode == "max_only":
        mode_pass = counted_chars <= char_policy["max"]
        mode_message = f"max_only 기준: 최대 {char_policy['max']}자"
    else:  # min_only
        mode_pass = counted_chars >= char_policy["min"]
        mode_message = f"min_only 기준: 최소 {char_policy['min']}자"

    utilization_ratio = 0.0
    utilization_pass = True
    enforce_rule = char_policy.get("enforce_90_95_rule", True)
    base_limit = _get_base_limit(char_policy)
    if enforce_rule and isinstance(base_limit, int) and base_limit > 0:
        utilization_ratio = counted_chars / base_limit
        utilization_pass = 0.90 <= utilization_ratio <= 0.95

    passed = mode_pass and utilization_pass
    message = (
        f"{mode_message}, 실제 {counted_chars}자, "
        f"사용률 {utilization_ratio:.3f}"
    )

    return CharCheckResult(
        passed=passed,
        counted_chars=counted_chars,
        utilization_ratio=utilization_ratio,
        utilization_pass=utilization_pass,
        expected=expected,
        message=message,
    )


def _find_banned_hits(essay: str, banned_words: list[str]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for word in banned_words:
        if word and word in essay:
            hits.append(
                {
                    "word": word,
                    "evidence_text": word,
                    "suggestion": f"'{word}' 대신 구체적 사실 표현으로 교체하세요.",
                }
            )
    return hits


def _build_response(input_data: dict[str, Any]) -> dict[str, Any]:
    essay = input_data["essay"]
    question = input_data["question"]
    char_policy = input_data["char_policy"]
    banned_words = input_data.get("banned_words", [])

    char_result = _check_char_policy(essay, char_policy)
    banned_hits = _find_banned_hits(essay, banned_words)

    issue_list: list[dict[str, str]] = []
    if not char_result.passed:
        issue_list.append(
            {
                "type": "char_count",
                "severity": "high",
                "message": "글자수 또는 사용률 기준을 충족하지 못했습니다.",
                "evidence_text": str(char_result.counted_chars),
                "suggestion": "핵심 문장을 압축/확장하여 90~95% 구간을 맞추세요.",
            }
        )
    if banned_hits:
        issue_list.append(
            {
                "type": "banned_word",
                "severity": "medium",
                "message": "금지 표현이 발견되었습니다.",
                "suggestion": "추상 표현 대신 경험 기반 문장으로 수정하세요.",
            }
        )

    question_fit = 85 if question and len(essay) > 80 else 70
    clarity = 80 if len(essay) > 120 else 72
    evidence = 78 if any(token in essay for token in ["경험", "문제", "결과", "협업"]) else 68
    job_alignment = 82 if input_data.get("job_title", "") in essay else 75
    tone_naturalness = 84 if not banned_hits else 72

    raw_score = int((question_fit + clarity + evidence + job_alignment + tone_naturalness) / 5)
    score = max(0, min(100, raw_score - (8 * len(banned_hits))))

    final_pass = char_result.passed and len([i for i in issue_list if i["severity"] == "high"]) < 2

    response = {
        "pass": final_pass,
        "score": score,
        "char_check": {
            "pass": char_result.passed,
            "counted_chars": char_result.counted_chars,
            "mode": char_policy["mode"],
            "expected": char_result.expected,
            "utilization_ratio": round(char_result.utilization_ratio, 4),
            "utilization_pass": char_result.utilization_pass,
            "message": char_result.message,
        },
        "dimension_scores": {
            "question_fit": question_fit,
            "clarity": clarity,
            "evidence": evidence,
            "job_alignment": job_alignment,
            "tone_naturalness": tone_naturalness,
        },
        "issues": issue_list,
        "banned_word_hits": banned_hits,
        "rewrite_guidance": {
            "keep_points": [
                "질문에 대한 답변 의도를 유지하세요.",
                "핵심 경험 1개를 중심으로 유지하세요.",
            ],
            "fix_points": [
                "문장 길이를 조절해 글자수 사용률을 90~95%로 맞추세요.",
                "금지 표현은 구체적 행동/결과 문장으로 바꾸세요.",
            ],
            "recommended_outline": [
                "문제/과제 배경 한 문장",
                "본인이 취한 행동과 판단 근거",
                "정량/정성 결과",
            ],
        },
        "final_comment": "기준 충족 여부를 확인했고, 수정 포인트를 반영하면 완성도가 높아집니다.",
    }

    jsonschema.validate(instance=response, schema=OUTPUT_SCHEMA)
    return response


class ReviewerHandler(BaseHTTPRequestHandler):
    server_version = "ReviewerAgentHTTP/0.1"

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/agent/reviewer":
            self._send_json(404, {"error": "not_found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            data = json.loads(raw_body.decode("utf-8"))
            jsonschema.validate(instance=data, schema=INPUT_SCHEMA)

            reviewed = _build_response(data)
            self._send_json(200, reviewed)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
        except jsonschema.ValidationError as exc:
            self._send_json(400, {"error": "invalid_payload", "message": exc.message})
        except Exception as exc:  # pylint: disable=broad-except
            self._send_json(500, {"error": "internal_error", "message": str(exc)})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "not_found"})


def main() -> None:
    host = os.getenv("REVIEWER_HOST", "127.0.0.1")
    port = int(os.getenv("REVIEWER_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), ReviewerHandler)
    print(f"reviewer agent server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()