from __future__ import annotations

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from google import genai

load_dotenv()


_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SYSTEM_PROMPT_PATH = _DATA_DIR / "prompts" / "system_prompt.md"

_system_prompt: str | None = None
_client: genai.Client | None = None
_provider: str | None = None


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return _system_prompt


def _get_provider() -> str:
    global _provider
    if _provider is not None:
        return _provider

    if os.environ.get("ANTHROPIC_API_KEY"):
        _provider = "anthropic"
        return _provider

    if os.environ.get("GEMINI_API_KEY"):
        _provider = "gemini"
        return _provider

    raise RuntimeError("ANTHROPIC_API_KEY 또는 GEMINI_API_KEY 환경변수가 필요합니다.")


def _get_client() -> genai.Client:
    global _client
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    if _client is None:
        _client = genai.Client(api_key=api_key)
    return _client


def _extract_anthropic_text(message: object) -> str:
    content = getattr(message, "content", [])
    texts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            texts.append(text)
    return "\n".join(texts).strip()


def _generate_with_anthropic(user_prompt: str, max_tokens: int) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=max_tokens,
        system=_get_system_prompt(),
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _extract_anthropic_text(message)


def _generate_with_gemini(user_prompt: str) -> str:
    response = _get_client().models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config={"system_instruction": _get_system_prompt()},
    )
    return (response.text or "").strip()


def generate_outline(user_prompt: str) -> str:
    """큰틀 작성 LLM — 내용/구조/핵심 팩트 중심으로 구체적 뼈대를 잡는다."""
    provider = _get_provider()
    if provider == "anthropic":
        return _generate_with_anthropic(user_prompt, max_tokens=2048)
    return _generate_with_gemini(user_prompt)


def generate_draft(user_prompt: str) -> str:
    """초안 작성 LLM — 큰틀을 바탕으로 표현/문체/Humanizing에 집중한다."""
    provider = _get_provider()
    if provider == "anthropic":
        return _generate_with_anthropic(user_prompt, max_tokens=4096)
    return _generate_with_gemini(user_prompt)
