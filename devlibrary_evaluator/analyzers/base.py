"""
Base analyzer class for DevLibrary evaluation system

Provides common functionality and AAS integration for all analyzers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from core.managers import ManagerHub
from ..models.project import Project


@dataclass
class AnalysisResult:
    """Base class for analysis results"""

    analyzer_name: str
    timestamp: datetime
    projects_analyzed: int
    analysis_duration: float
    findings: List[Dict[str, Any]]
    summary: str
    recommendations: List[str]
    metadata: Dict[str, Any]


class BaseAnalyzer(ABC):
    """
    Base class for all DevLibrary analyzers

    Provides common functionality including AAS integration,
    logging, configuration, and result formatting.
    """

    def __init__(self, manager_hub: ManagerHub):
        """Initialize analyzer with AAS integration"""
        self.manager_hub = manager_hub
        self.config = getattr(manager_hub, "config", {})
        self.logger = getattr(manager_hub, "logger", logger)
        self.health_manager = getattr(
            manager_hub, "health", getattr(manager_hub, "health_aggregator", None)
        )

        # Analyzer-specific configuration
        self.analyzer_config = self._load_analyzer_config()

        self.logger.debug(f"Initialized {self.__class__.__name__}")

    @property
    @abstractmethod
    def analyzer_name(self) -> str:
        """Return the name of this analyzer"""
        pass

    @abstractmethod
    async def analyze(self, projects: List[Project], config: Any) -> AnalysisResult:
        """
        Perform analysis on the provided projects

        Args:
            projects: List of projects to analyze
            config: Evaluation configuration

        Returns:
            Analysis results
        """
        pass

    def _load_analyzer_config(self) -> Dict[str, Any]:
        """Load analyzer-specific configuration from AAS config"""
        try:
            plugin_config = self.config.get("plugins", {})
            evaluator_config = plugin_config.get("devlibrary_evaluator", {})
            analyzer_config = evaluator_config.get("analyzers", {})
            return analyzer_config.get(self.analyzer_name, {})
        except Exception as e:
            self.logger.warning(f"Could not load analyzer config: {e}")
            return {}

    def _create_result(
        self,
        projects_analyzed: int,
        analysis_duration: float,
        findings: List[Dict[str, Any]],
        summary: str,
        recommendations: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """Create standardized analysis result"""
        return AnalysisResult(
            analyzer_name=self.analyzer_name,
            timestamp=datetime.now(),
            projects_analyzed=projects_analyzed,
            analysis_duration=analysis_duration,
            findings=findings,
            summary=summary,
            recommendations=recommendations,
            metadata=metadata or {},
        )

    def _log_analysis_start(self, projects: List[Project]):
        """Log analysis start with project context"""
        project_names = [p.name for p in projects]
        self.logger.info(
            f"Starting {self.analyzer_name} analysis on {len(projects)} projects: {project_names}"
        )

    def _log_analysis_complete(self, result: AnalysisResult):
        """Log analysis completion with summary"""
        self.logger.info(
            f"Completed {self.analyzer_name} analysis: "
            f"{result.projects_analyzed} projects, "
            f"{len(result.findings)} findings, "
            f"{result.analysis_duration:.2f}s"
        )

    def _filter_projects_by_criteria(
        self, projects: List[Project], criteria: Dict[str, Any]
    ) -> List[Project]:
        """Filter projects based on analysis criteria"""
        filtered = []

        for project in projects:
            include = True

            # Language filter
            if "languages" in criteria:
                if project.language not in criteria["languages"]:
                    include = False

            # AAS integration filter
            if "aas_integration" in criteria:
                if (
                    criteria["aas_integration"]
                    and not project.aas_integration.uses_manager_hub
                ):
                    include = False

            # Plugin filter
            if "plugins_only" in criteria:
                if criteria["plugins_only"] and not project.is_aas_plugin():
                    include = False

            # Strategic priority filter
            if "min_strategic_priority" in criteria:
                priority_order = {
                    "critical": 4,
                    "high": 3,
                    "medium": 2,
                    "low": 1,
                    "unknown": 0,
                }
                min_priority = priority_order.get(criteria["min_strategic_priority"], 0)
                project_priority = priority_order.get(
                    project.get_strategic_priority(), 0
                )
                if project_priority < min_priority:
                    include = False

            if include:
                filtered.append(project)

        if len(filtered) != len(projects):
            self.logger.debug(
                f"Filtered {len(projects)} projects to {len(filtered)} "
                f"based on criteria: {criteria}"
            )

        return filtered

    def _extract_project_metadata(self, project: Project) -> Dict[str, Any]:
        """Extract relevant metadata from project for analysis"""
        return {
            "name": project.name,
            "language": project.language,
            "framework": project.framework,
            "is_aas_plugin": project.is_aas_plugin(),
            "integration_level": project.get_integration_level(),
            "strategic_priority": project.get_strategic_priority(),
            "manager_usage": project.manager_usage,
            "modernization_needs": project.get_modernization_needs(),
        }

    def _create_finding(
        self,
        finding_type: str,
        severity: str,
        title: str,
        description: str,
        project: Optional[Project] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create standardized finding structure"""
        finding = {
            "type": finding_type,
            "severity": severity,  # "critical", "high", "medium", "low", "info"
            "title": title,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "analyzer": self.analyzer_name,
        }

        if project:
            finding["project"] = {
                "name": project.name,
                "path": str(project.path),
                "language": project.language,
            }

        if details:
            finding["details"] = details

        return finding

    def _calculate_severity_distribution(
        self, findings: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Calculate distribution of finding severities"""
        distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

        for finding in findings:
            severity = finding.get("severity", "info")
            if severity in distribution:
                distribution[severity] += 1

        return distribution

    def _generate_summary_from_findings(self, findings: List[Dict[str, Any]]) -> str:
        """Generate summary text from findings"""
        if not findings:
            return f"No issues found by {self.analyzer_name} analysis."

        distribution = self._calculate_severity_distribution(findings)
        total = len(findings)

        summary_parts = [f"Found {total} findings:"]

        for severity, count in distribution.items():
            if count > 0:
                summary_parts.append(f"{count} {severity}")

        return f"{self.analyzer_name} analysis: " + ", ".join(summary_parts) + "."

    async def _health_check(self) -> bool:
        """Perform health check for this analyzer"""
        try:
            # Basic health checks
            if not self.manager_hub:
                return False

            if not self.config:
                return False

            # Analyzer-specific health checks can be overridden
            return await self._analyzer_health_check()

        except Exception as e:
            self.logger.error(f"Health check failed for {self.analyzer_name}: {e}")
            return False

    async def _analyzer_health_check(self) -> bool:
        """Override this method for analyzer-specific health checks"""
        return True
