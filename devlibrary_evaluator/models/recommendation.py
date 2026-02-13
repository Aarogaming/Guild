"""
Recommendation models for DevLibrary evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EffortLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Recommendation:
    """Base recommendation data."""

    id: str
    title: str
    description: str
    category: str
    effort: str
    priority: str
    roadmap_phase: str
    implementation_via_aas: bool = False


@dataclass
class PrioritizedRecommendation(Recommendation):
    """Recommendation with ranking metadata."""

    score: float = 0.0
    aas_task_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
