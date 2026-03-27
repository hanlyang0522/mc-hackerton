from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AllocationResult:
    question: str
    material_id: str
    display: str
    activity_key: str
    activity_detail: dict[str, Any]
    score: int
    score_breakdown: dict[str, int] = field(default_factory=dict)
