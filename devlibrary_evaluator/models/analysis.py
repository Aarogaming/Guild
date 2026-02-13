"""
Analysis result models for DevLibrary evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional

from .project import Project
from ..analyzers.base import AnalysisResult


@dataclass
class AnalysisResults:
    """Aggregate analysis results across analyzers."""

    projects: List[Project]
    analysis_timestamp: datetime
    config: Any
    architecture_results: Optional[AnalysisResult] = None
    feature_gaps_results: Optional[AnalysisResult] = None
    integration_results: Optional[AnalysisResult] = None
    technical_debt_results: Optional[AnalysisResult] = None
    strategic_alignment_results: Optional[AnalysisResult] = None
    synergy_results: Optional[AnalysisResult] = None
    workflow_results: Optional[AnalysisResult] = None


@dataclass
class EvaluationReport:
    """Final evaluation report output."""

    analysis_results: AnalysisResults
    recommendations: List[Any] = field(default_factory=list)
    executive_summary: str = ""
    generated_at: datetime = field(default_factory=datetime.now)
