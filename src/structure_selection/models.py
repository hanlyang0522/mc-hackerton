from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StructureResult:
    question: str
    question_type: str | None
    common_rules: list[str]
    flow: list[str] = field(default_factory=list)
    core: str | None = None
    caution: str | None = None
