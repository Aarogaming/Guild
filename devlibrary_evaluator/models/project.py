"""
Project data models with AAS integration support

This module defines data structures for representing projects in the DevLibrary
workspace with specific support for AAS integration patterns and Master Roadmap alignment.
"""

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum


class StrategicValue(Enum):
    """Strategic value levels for roadmap alignment"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class Dependency:
    """Represents a project dependency"""

    name: str
    version: str
    type: str  # "runtime", "dev", "build"
    source: str  # "pip", "npm", "nuget", etc.
    security_issues: List[str] = field(default_factory=list)
    outdated: bool = False


@dataclass
class AASIntegration:
    """Represents how a project integrates with the AAS ecosystem"""

    is_aas_plugin: bool
    uses_manager_hub: bool
    manager_dependencies: List[str]
    cli_integration: bool
    config_integration: bool
    logging_integration: bool
    task_integration: bool
    artifact_integration: bool

    def integration_score(self) -> float:
        """Calculate integration completeness score (0.0 to 1.0)"""
        integrations = [
            self.uses_manager_hub,
            self.cli_integration,
            self.config_integration,
            self.logging_integration,
            self.task_integration,
            self.artifact_integration,
        ]
        return sum(integrations) / len(integrations)


@dataclass
class PluginCompliance:
    """Represents compliance with AAS plugin architecture standards"""

    has_manifest: bool
    manifest_valid: bool
    follows_structure: bool
    has_init_file: bool
    has_tests: bool
    has_documentation: bool
    uses_base_plugin: bool
    compliance_issues: List[str] = field(default_factory=list)

    def compliance_score(self) -> float:
        """Calculate compliance score (0.0 to 1.0)"""
        checks = [
            self.has_manifest,
            self.manifest_valid,
            self.follows_structure,
            self.has_init_file,
            self.has_tests,
            self.has_documentation,
            self.uses_base_plugin,
        ]
        return sum(checks) / len(checks)


@dataclass
class ResourceRequirements:
    """Resource requirements for roadmap alignment"""

    developers: int
    timeline: str
    budget: Optional[str] = None
    infrastructure: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class RoadmapAlignment:
    """Represents alignment with AAS Master Roadmap"""

    aligned_phases: List[str]
    supporting_initiatives: List[str]
    blocking_dependencies: List[str]
    strategic_value: StrategicValue
    timeline_compatibility: bool
    resource_requirements: ResourceRequirements
    alignment_notes: str = ""

    def alignment_score(self) -> float:
        """Calculate alignment score (0.0 to 1.0)"""
        score = 0.0

        # Phase alignment (40% of score)
        if self.aligned_phases:
            score += 0.4

        # Strategic value (30% of score)
        value_scores = {
            StrategicValue.CRITICAL: 1.0,
            StrategicValue.HIGH: 0.8,
            StrategicValue.MEDIUM: 0.6,
            StrategicValue.LOW: 0.4,
            StrategicValue.UNKNOWN: 0.0,
        }
        score += 0.3 * value_scores.get(self.strategic_value, 0.0)

        # Timeline compatibility (20% of score)
        if self.timeline_compatibility:
            score += 0.2

        # No blocking dependencies (10% of score)
        if not self.blocking_dependencies:
            score += 0.1

        return min(score, 1.0)


@dataclass
class Project:
    """
    Represents a project in the DevLibrary workspace with AAS integration context
    """

    name: str
    path: Path
    language: str
    framework: str
    version: str
    dependencies: List[Dependency]
    aas_integration: AASIntegration
    plugin_compliance: Optional[PluginCompliance]
    manager_usage: List[str]
    roadmap_alignment: Optional[RoadmapAlignment]
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_aas_project(self) -> bool:
        """Check if this is the main AAS project"""
        return self.name == "AaroneousAutomationSuite"

    def is_aas_plugin(self) -> bool:
        """Check if this is an AAS plugin"""
        return self.aas_integration.is_aas_plugin

    def get_integration_level(self) -> str:
        """Get integration level description"""
        score = self.aas_integration.integration_score()
        if score >= 0.8:
            return "full"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        elif score >= 0.2:
            return "low"
        else:
            return "none"

    def get_strategic_priority(self) -> str:
        """Get strategic priority based on roadmap alignment"""
        if not self.roadmap_alignment:
            return "unknown"

        score = self.roadmap_alignment.alignment_score()
        if score >= 0.8:
            return "critical"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"

    def get_modernization_needs(self) -> List[str]:
        """Identify modernization needs based on project characteristics"""
        needs = []

        # AAS integration needs
        if not self.aas_integration.uses_manager_hub:
            needs.append("manager_hub_integration")

        if not self.aas_integration.logging_integration:
            needs.append("logging_standardization")

        if not self.aas_integration.config_integration:
            needs.append("configuration_management")

        # Plugin compliance needs
        if self.is_aas_plugin() and self.plugin_compliance:
            if self.plugin_compliance.compliance_score() < 0.8:
                needs.append("plugin_compliance_improvement")

        # Dependency modernization
        outdated_deps = [d for d in self.dependencies if d.outdated]
        if outdated_deps:
            needs.append("dependency_updates")

        # Security issues
        security_issues = [d for d in self.dependencies if d.security_issues]
        if security_issues:
            needs.append("security_updates")

        return needs

    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary for serialization"""
        return {
            "name": self.name,
            "path": str(self.path),
            "language": self.language,
            "framework": self.framework,
            "version": self.version,
            "dependencies": [
                {
                    "name": d.name,
                    "version": d.version,
                    "type": d.type,
                    "source": d.source,
                    "security_issues": d.security_issues,
                    "outdated": d.outdated,
                }
                for d in self.dependencies
            ],
            "aas_integration": {
                "is_aas_plugin": self.aas_integration.is_aas_plugin,
                "uses_manager_hub": self.aas_integration.uses_manager_hub,
                "manager_dependencies": self.aas_integration.manager_dependencies,
                "cli_integration": self.aas_integration.cli_integration,
                "config_integration": self.aas_integration.config_integration,
                "logging_integration": self.aas_integration.logging_integration,
                "task_integration": self.aas_integration.task_integration,
                "artifact_integration": self.aas_integration.artifact_integration,
                "integration_score": self.aas_integration.integration_score(),
            },
            "plugin_compliance": (
                {
                    "has_manifest": self.plugin_compliance.has_manifest,
                    "manifest_valid": self.plugin_compliance.manifest_valid,
                    "follows_structure": self.plugin_compliance.follows_structure,
                    "has_init_file": self.plugin_compliance.has_init_file,
                    "has_tests": self.plugin_compliance.has_tests,
                    "has_documentation": self.plugin_compliance.has_documentation,
                    "uses_base_plugin": self.plugin_compliance.uses_base_plugin,
                    "compliance_issues": self.plugin_compliance.compliance_issues,
                    "compliance_score": self.plugin_compliance.compliance_score(),
                }
                if self.plugin_compliance
                else None
            ),
            "manager_usage": self.manager_usage,
            "roadmap_alignment": (
                {
                    "aligned_phases": self.roadmap_alignment.aligned_phases,
                    "supporting_initiatives": self.roadmap_alignment.supporting_initiatives,
                    "blocking_dependencies": self.roadmap_alignment.blocking_dependencies,
                    "strategic_value": self.roadmap_alignment.strategic_value.value,
                    "timeline_compatibility": self.roadmap_alignment.timeline_compatibility,
                    "resource_requirements": {
                        "developers": self.roadmap_alignment.resource_requirements.developers,
                        "timeline": self.roadmap_alignment.resource_requirements.timeline,
                        "budget": self.roadmap_alignment.resource_requirements.budget,
                        "infrastructure": self.roadmap_alignment.resource_requirements.infrastructure,
                        "dependencies": self.roadmap_alignment.resource_requirements.dependencies,
                    },
                    "alignment_notes": self.roadmap_alignment.alignment_notes,
                    "alignment_score": self.roadmap_alignment.alignment_score(),
                }
                if self.roadmap_alignment
                else None
            ),
            "last_updated": self.last_updated.isoformat(),
            "metadata": self.metadata,
            "integration_level": self.get_integration_level(),
            "strategic_priority": self.get_strategic_priority(),
            "modernization_needs": self.get_modernization_needs(),
        }
