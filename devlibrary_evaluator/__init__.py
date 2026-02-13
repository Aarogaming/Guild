"""
DevLibrary Evaluator Module

A comprehensive evaluation system for analyzing the DevLibrary workspace,
identifying improvement opportunities, and generating actionable recommendations.

Note: This module lives under Guild. Any remaining "plugin" references are legacy.
"""

from .evaluator import DevLibraryEvaluatorPlugin
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
from .models import (
    Project,
    AnalysisResults,
    Recommendation,
    EvaluationReport,
)

__version__ = "1.0.0"
__author__ = "AAS Development Team"

__all__ = [
    "DevLibraryEvaluatorPlugin",
    "ArchitectureAnalyzer",
    "FeatureGapAnalyzer",
    "IntegrationAnalyzer",
    "TechnicalDebtAnalyzer",
    "StrategicAlignmentAnalyzer",
    "SynergyAnalyzer",
    "WorkflowAnalyzer",
    "RecommendationEngine",
    "Project",
    "AnalysisResults",
    "Recommendation",
    "EvaluationReport",
]
