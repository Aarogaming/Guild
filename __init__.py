"""
Guild - Unified Task Management & Orchestration Sub-Module

The Guild serves as AAS's central nervous system for:
- Task lifecycle management
- Agent coordination and handoff
- Batch processing orchestration
- Directory and workspace management
- Inter-module communication routing

This sub-module consolidates previously scattered functionality into a cohesive,
dedicated system for autonomous task execution and agent cooperation.
"""

from .core import GuildCore
from .task_director import TaskDirector
from .agent_coordinator import AgentCoordinator
from .batch_orchestrator import BatchOrchestrator
from .communication_hub import CommunicationHub
from .workspace_director import WorkspaceDirector

__all__ = [
    "GuildCore",
    "TaskDirector",
    "AgentCoordinator",
    "BatchOrchestrator",
    "CommunicationHub",
    "WorkspaceDirector",
]

__version__ = "2.0.0"
