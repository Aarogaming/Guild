"""
DevLibrary Evaluator Module - Main evaluation orchestrator

This module provides the main evaluation functionality for the DevLibrary workspace,
integrating with the AAS ecosystem to analyze projects, identify improvements,
and generate actionable recommendations aligned with the Master Roadmap.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from loguru import logger
from core.config import load_config
from core.managers import ManagerHub

from .models.project import (
    Project,
    AASIntegration,
    RoadmapAlignment,
    ResourceRequirements,
    StrategicValue,
)
from .models.analysis import AnalysisResults, EvaluationReport
from .models.recommendation import PrioritizedRecommendation
from .analyzers import (
    ArchitectureAnalyzer,
    FeatureGapAnalyzer,
    IntegrationAnalyzer,
    TechnicalDebtAnalyzer,
    StrategicAlignmentAnalyzer,
    SynergyAnalyzer,
    WorkflowAnalyzer,
)
from .recommendation_engine import RecommendationEngine
from .report_generator import ReportGenerator


@dataclass
class EvaluationConfig:
    """Configuration for DevLibrary evaluation"""

    workspace_path: Path
    analyzers: Optional[List[str]] = field(default=None)  # None means all analyzers
    output_format: str = "markdown"
    output_path: Optional[Path] = None
    quick_mode: bool = False
    include_tasks: bool = True
    master_roadmap_path: Optional[Path] = None


class DevLibraryEvaluatorPlugin:
    """
    Main module class for DevLibrary evaluation system.

    Integrates with AAS infrastructure to provide comprehensive analysis
    of the DevLibrary workspace and generate actionable recommendations
    aligned with the Master Roadmap.
    """

    def __init__(self, manager_hub: ManagerHub):
        """Initialize the evaluator module with AAS integration"""
        self.manager_hub = manager_hub
        self.config = getattr(manager_hub, "config", load_config())
        self.logger = getattr(manager_hub, "logger", logger)
        self.task_manager = getattr(manager_hub, "tasks", None)
        self.artifact_manager = getattr(manager_hub, "artifacts", None) or getattr(
            manager_hub, "artifact_manager", None
        )
        if self.artifact_manager is None and self.task_manager is not None:
            self.artifact_manager = getattr(self.task_manager, "artifact_manager", None)
        self.health_manager = getattr(manager_hub, "health", None) or getattr(
            manager_hub, "health_aggregator", None
        )

        # Initialize analyzers
        self.analyzers = self._initialize_analyzers()

        # Initialize engines
        self.recommendation_engine = RecommendationEngine(manager_hub)
        self.report_generator = ReportGenerator(manager_hub)

        self.logger.info("DevLibrary Evaluator Plugin initialized")

    def get_plugin_info(self) -> Dict[str, Any]:
        """Return plugin information for AAS registry"""
        return {
            "name": "devlibrary_evaluator",
            "version": "1.0.0",
            "description": "Comprehensive evaluation system for DevLibrary workspace",
            "author": "AAS Core Team",
            "capabilities": self.get_capabilities(),
            "aas_integration": {
                "uses_manager_hub": True,
                "uses_task_management": True,
                "uses_artifact_management": True,
                "cli_commands": ["evaluate"],
            },
        }

    def get_capabilities(self) -> List[str]:
        """Return list of plugin capabilities"""
        return [
            "workspace_analysis",
            "architecture_evaluation",
            "feature_gap_analysis",
            "integration_assessment",
            "technical_debt_analysis",
            "strategic_alignment",
            "synergy_identification",
            "workflow_analysis",
            "recommendation_generation",
            "report_generation",
            "aas_task_creation",
            "master_roadmap_alignment",
        ]

    def _initialize_analyzers(self) -> Dict[str, Any]:
        """Initialize all analyzers with AAS integration"""
        analyzers = {
            "architecture": ArchitectureAnalyzer(self.manager_hub),
            "feature_gaps": FeatureGapAnalyzer(self.manager_hub),
            "integration": IntegrationAnalyzer(self.manager_hub),
            "technical_debt": TechnicalDebtAnalyzer(self.manager_hub),
            "strategic_alignment": StrategicAlignmentAnalyzer(self.manager_hub),
            "synergy": SynergyAnalyzer(self.manager_hub),
            "workflow": WorkflowAnalyzer(self.manager_hub),
        }

        self.logger.info(f"Initialized {len(analyzers)} analyzers")
        return analyzers

    async def _maybe_await(self, func, *args, **kwargs):
        """Call sync/async functions uniformly."""
        result = func(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def evaluate_workspace(self, config: EvaluationConfig) -> EvaluationReport:
        """
        Main evaluation method that orchestrates the complete analysis

        Args:
            config: Evaluation configuration

        Returns:
            Complete evaluation report with recommendations
        """
        self.logger.info(f"Starting DevLibrary evaluation: {config.workspace_path}")

        # Create task for progress tracking (if supported)
        task_id = None
        task_tracking_enabled = False
        if self.task_manager and all(
            hasattr(self.task_manager, name)
            for name in ("create_task", "update_progress", "complete_task", "fail_task")
        ):
            task_tracking_enabled = True
            try:
                task_id = await self._maybe_await(
                    self.task_manager.create_task,
                    "devlibrary_evaluation",
                    "DevLibrary Workspace Evaluation",
                    {"workspace": str(config.workspace_path)},
                )
            except Exception as e:
                self.logger.warning(
                    f"Task tracking unavailable; skipping progress updates: {e}"
                )
                task_tracking_enabled = False

        try:
            # Phase 1: Project Discovery
            self.logger.info("Phase 1: Discovering projects")
            if task_tracking_enabled and task_id:
                try:
                    await self._maybe_await(
                        self.task_manager.update_progress,
                        task_id,
                        0.1,
                        "Discovering projects",
                    )
                except Exception as e:
                    self.logger.warning(f"Task progress update failed: {e}")
                    task_tracking_enabled = False
            projects = await self._discover_projects(config.workspace_path)

            # Phase 2: Analysis
            self.logger.info("Phase 2: Running analysis")
            if task_tracking_enabled and task_id:
                try:
                    await self._maybe_await(
                        self.task_manager.update_progress,
                        task_id,
                        0.2,
                        "Running analysis",
                    )
                except Exception as e:
                    self.logger.warning(f"Task progress update failed: {e}")
                    task_tracking_enabled = False
            analysis_results = await self._run_analysis(projects, config)

            # Phase 3: Recommendation Generation
            self.logger.info("Phase 3: Generating recommendations")
            if task_tracking_enabled and task_id:
                try:
                    await self._maybe_await(
                        self.task_manager.update_progress,
                        task_id,
                        0.8,
                        "Generating recommendations",
                    )
                except Exception as e:
                    self.logger.warning(f"Task progress update failed: {e}")
                    task_tracking_enabled = False
            recommendations = await self.recommendation_engine.generate_recommendations(
                analysis_results, config
            )

            # Phase 4: Report Generation
            self.logger.info("Phase 4: Generating report")
            if task_tracking_enabled and task_id:
                try:
                    await self._maybe_await(
                        self.task_manager.update_progress,
                        task_id,
                        0.9,
                        "Generating report",
                    )
                except Exception as e:
                    self.logger.warning(f"Task progress update failed: {e}")
                    task_tracking_enabled = False
            report = await self.report_generator.create_report(
                analysis_results, recommendations, config
            )

            # Phase 5: Task Creation (if enabled)
            if config.include_tasks:
                self.logger.info("Phase 5: Creating AAS tasks")
                await self._create_aas_tasks(recommendations, task_id)

            if task_tracking_enabled and task_id:
                try:
                    await self._maybe_await(
                        self.task_manager.complete_task,
                        task_id,
                        "Evaluation completed successfully",
                    )
                except Exception as e:
                    self.logger.warning(f"Task completion update failed: {e}")
            self.logger.info("DevLibrary evaluation completed successfully")

            return report

        except Exception as e:
            if task_tracking_enabled and task_id:
                try:
                    await self._maybe_await(
                        self.task_manager.fail_task,
                        task_id,
                        f"Evaluation failed: {str(e)}",
                    )
                except Exception as fail_error:
                    self.logger.warning(f"Task failure update failed: {fail_error}")
            self.logger.error(f"Evaluation failed: {str(e)}")
            raise

    async def _discover_projects(self, workspace_path: Path) -> List[Project]:
        """
        Discover and catalog all projects in the workspace

        Args:
            workspace_path: Path to DevLibrary workspace

        Returns:
            List of discovered projects with metadata
        """
        projects = []

        # Discover AAS main project
        aas_path = workspace_path / "AaroneousAutomationSuite"
        if aas_path.exists():
            aas_project = await self._analyze_aas_project(aas_path)
            projects.append(aas_project)

        # Discover other projects
        for project_dir in workspace_path.iterdir():
            if project_dir.is_dir() and project_dir.name not in [
                "AaroneousAutomationSuite",
                ".git",
                ".venv",
                "__pycache__",
                "node_modules",
                "artifacts",
                "_archive",
                "_tmp",
            ]:
                project = await self._analyze_project(project_dir)
                if project:
                    projects.append(project)

        self.logger.info(f"Discovered {len(projects)} projects")
        return projects

    async def _analyze_aas_project(self, aas_path: Path) -> Project:
        """Analyze the main AAS project with special handling"""
        # Discover AAS plugins
        plugins_path = aas_path / "plugins"
        plugins = []
        if plugins_path.exists():
            for plugin_dir in plugins_path.iterdir():
                if plugin_dir.is_dir() and (plugin_dir / "__init__.py").exists():
                    plugins.append(plugin_dir.name)

        # Analyze AAS integration
        aas_integration = AASIntegration(
            is_aas_plugin=False,  # This is the main AAS project
            uses_manager_hub=True,
            manager_dependencies=["config", "logging", "tasks", "artifacts", "health"],
            cli_integration=True,
            config_integration=True,
            logging_integration=True,
            task_integration=True,
            artifact_integration=True,
        )

        # Analyze roadmap alignment
        roadmap_path = aas_path / "docs" / "MASTER_ROADMAP.md"
        roadmap_alignment = await self._analyze_roadmap_alignment(roadmap_path)

        return Project(
            name="AaroneousAutomationSuite",
            path=aas_path,
            language="python",
            framework="custom",
            version="2.0",
            dependencies=[],  # Will be populated by dependency analyzer
            aas_integration=aas_integration,
            plugin_compliance=None,  # Will be populated by architecture analyzer
            manager_usage=["config", "logging", "tasks", "artifacts", "health"],
            roadmap_alignment=roadmap_alignment,
            last_updated=datetime.now(),
            metadata={
                "plugins": plugins,
                "is_main_project": True,
                "has_dashboard": True,
                "has_cli": True,
            },
        )

    async def _analyze_project(self, project_path: Path) -> Optional[Project]:
        """Analyze a general project and determine its characteristics"""
        # Basic project detection logic
        if (project_path / "requirements.txt").exists() or (
            project_path / "pyproject.toml"
        ).exists():
            language = "python"
        elif (project_path / "package.json").exists():
            language = "javascript"
        elif any(project_path.glob("*.csproj")):
            language = "csharp"
        else:
            return None  # Unknown project type

        # Analyze AAS integration
        aas_integration = await self._analyze_aas_integration(project_path)

        return Project(
            name=project_path.name,
            path=project_path,
            language=language,
            framework="unknown",  # Will be determined by analyzers
            version="unknown",
            dependencies=[],
            aas_integration=aas_integration,
            plugin_compliance=None,
            manager_usage=[],
            roadmap_alignment=None,
            last_updated=datetime.now(),
        )

    async def _analyze_aas_integration(self, project_path: Path) -> AASIntegration:
        """Analyze how a project integrates with AAS"""
        # Check for plugin manifest
        manifest_path = project_path / "plugin_manifest.json"
        is_plugin = manifest_path.exists()

        # Check for AAS imports (simplified analysis)
        uses_manager_hub = False
        manager_deps = []

        # This would be expanded with actual code analysis
        # For now, provide basic detection

        return AASIntegration(
            is_aas_plugin=is_plugin,
            uses_manager_hub=uses_manager_hub,
            manager_dependencies=manager_deps,
            cli_integration=False,
            config_integration=False,
            logging_integration=False,
            task_integration=False,
            artifact_integration=False,
        )

    async def _analyze_roadmap_alignment(
        self, roadmap_path: Path
    ) -> Optional[RoadmapAlignment]:
        """Analyze alignment with Master Roadmap"""
        if not roadmap_path.exists():
            return None

        # This would parse the roadmap and analyze alignment
        # For now, return basic structure
        return RoadmapAlignment(
            aligned_phases=["Phase 1", "Phase 2"],
            supporting_initiatives=["AAS-208", "AAS-211", "AAS-215"],
            blocking_dependencies=[],
            strategic_value=StrategicValue.HIGH,
            timeline_compatibility=True,
            resource_requirements=ResourceRequirements(
                developers=3,
                timeline="3 months",
            ),
        )

    async def _run_analysis(
        self, projects: List[Project], config: EvaluationConfig
    ) -> AnalysisResults:
        """Run all configured analyzers on the discovered projects"""
        results = AnalysisResults(
            projects=projects, analysis_timestamp=datetime.now(), config=config
        )

        # Determine which analyzers to run
        analyzers_to_run = config.analyzers or list(self.analyzers.keys())

        # Run analyzers in parallel
        analysis_tasks = []
        for analyzer_name in analyzers_to_run:
            if analyzer_name in self.analyzers:
                analyzer = self.analyzers[analyzer_name]
                task = asyncio.create_task(
                    analyzer.analyze(projects, config), name=f"analyzer_{analyzer_name}"
                )
                analysis_tasks.append((analyzer_name, task))

        # Collect results
        for analyzer_name, task in analysis_tasks:
            try:
                result = await task
                setattr(results, f"{analyzer_name}_results", result)
                self.logger.info(f"Completed {analyzer_name} analysis")
            except Exception as e:
                self.logger.error(f"Failed {analyzer_name} analysis: {str(e)}")
                setattr(results, f"{analyzer_name}_results", None)

        return results

    async def _create_aas_tasks(
        self,
        recommendations: List[PrioritizedRecommendation],
        parent_task_id: Optional[str],
    ):
        """Create AAS tasks from recommendations"""
        if not self.task_manager or not hasattr(self.task_manager, "create_task"):
            self.logger.warning(
                "Task manager unavailable or missing create_task; skipping task creation"
            )
            return
        for rec in recommendations[:10]:  # Limit to top 10 recommendations
            if rec.implementation_via_aas:
                task_id = await self._maybe_await(
                    self.task_manager.create_task,
                    f"recommendation_{rec.id}",
                    rec.title,
                    {
                        "description": rec.description,
                        "category": rec.category,
                        "effort": rec.effort,
                        "priority": rec.priority,
                        "roadmap_phase": rec.roadmap_phase,
                        "parent_evaluation": parent_task_id or "",
                    },
                )
                rec.aas_task_id = task_id
                self.logger.info(
                    f"Created AAS task {task_id} for recommendation {rec.id}"
                )

    async def quick_evaluate(self, workspace_path: Path) -> Dict[str, Any]:
        """Run a quick evaluation with limited analysis"""
        config = EvaluationConfig(
            workspace_path=workspace_path,
            analyzers=["architecture", "strategic_alignment"],
            quick_mode=True,
            include_tasks=False,
        )

        report = await self.evaluate_workspace(config)

        return {
            "summary": report.executive_summary,
            "top_recommendations": report.recommendations[:5],
            "strategic_alignment": report.analysis_results.strategic_alignment_results,
            "quick_wins": [r for r in report.recommendations if r.effort == "low"][:3],
        }
