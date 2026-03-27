from __future__ import annotations

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()


_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SYSTEM_PROMPT_PATH = _DATA_DIR / "prompts" / "system_prompt.md"

_system_prompt: str | None = None


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return _system_prompt


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
    return anthropic.Anthropic(api_key=api_key)


def generate_outline(user_prompt: str) -> str:
    """큰틀 작성 LLM — 내용/구조/핵심 팩트 중심으로 구체적 뼈대를 잡는다."""
    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=_get_system_prompt(),
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text.strip()


def generate_draft(user_prompt: str) -> str:
    """초안 작성 LLM — 큰틀을 바탕으로 표현/문체/Humanizing에 집중한다."""
    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=_get_system_prompt(),
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text.strip()
