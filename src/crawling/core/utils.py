from __future__ import annotations

import hashlib
import json
import re
import time
from html import unescape
from pathlib import Path
from typing import Any

import requests


class HttpClient:
    def __init__(self, timeout_seconds: int, retry_count: int, sleep_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.sleep_seconds = sleep_seconds
        self.session = requests.Session()

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        for _ in range(self.retry_count):
            try:
                response = self.session.get(url, timeout=self.timeout_seconds, **kwargs)
                response.raise_for_status()
                time.sleep(self.sleep_seconds)
                return response
            except Exception as exc:  # pylint: disable=broad-except
                last_error = exc
                time.sleep(self.sleep_seconds)
        if last_error:
            raise last_error
        raise RuntimeError("HTTP GET failed unexpectedly")

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        for _ in range(self.retry_count):
            try:
                response = self.session.post(url, timeout=self.timeout_seconds, **kwargs)
                response.raise_for_status()
                time.sleep(self.sleep_seconds)
                return response
            except Exception as exc:  # pylint: disable=broad-except
                last_error = exc
                time.sleep(self.sleep_seconds)
        if last_error:
            raise last_error
        raise RuntimeError("HTTP POST failed unexpectedly")



def slugify(text: str) -> str:
    compact = re.sub(r"\s+", "-", text.strip().lower())
    safe = re.sub(r"[^a-z0-9\-가-힣]", "", compact)
    return safe or "company"



def strip_html(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text



def hash_key(*parts: str) -> str:
    payload = "||".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()



def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
