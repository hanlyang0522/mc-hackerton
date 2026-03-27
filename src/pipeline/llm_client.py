from __future__ import annotations

import os
from pathlib import Path

import google.generativeai as genai


_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SYSTEM_PROMPT_PATH = _DATA_DIR / "prompts" / "system_prompt.md"

# 시스템 프롬프트 캐시
_system_prompt: str | None = None


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return _system_prompt


def _configure() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    genai.configure(api_key=api_key)


def generate_outline(user_prompt: str) -> str:
    """큰틀 작성 LLM — 내용/구조/핵심 팩트 중심으로 구체적 뼈대를 잡는다."""
    _configure()

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=_get_system_prompt(),
    )

    response = model.generate_content(user_prompt)
    return response.text.strip()


def generate_draft(user_prompt: str) -> str:
    """초안 작성 LLM — 큰틀을 바탕으로 표현/문체/Humanizing에 집중한다."""
    _configure()

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=_get_system_prompt(),
    )

    response = model.generate_content(user_prompt)
    return response.text.strip()
