"""Integration analyzer stub."""

from __future__ import annotations

from typing import Any, List

from .base import BaseAnalyzer
from ..models.project import Project


class IntegrationAnalyzer(BaseAnalyzer):
    @property
    def analyzer_name(self) -> str:
        return "integration"

    async def analyze(self, projects: List[Project], config: Any):
        self._log_analysis_start(projects)
        result = self._create_result(
            projects_analyzed=len(projects),
            analysis_duration=0.0,
            findings=[],
            summary="Integration analysis placeholder",
            recommendations=[],
        )
        self._log_analysis_complete(result)
        return result
