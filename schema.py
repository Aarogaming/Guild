"""
Shared Guild schema definitions.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class AgentStatus(Enum):
    OFFLINE = "offline"
    IDLE = "idle"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    ERROR = "error"


class AgentRole(Enum):
    GENERAL = "general"
    MERLIN = "merlin"
    FORTRESS = "fortress"
    ANDROID_APP = "androidapp"
    DESKTOP = "desktop"


class AgentCapability(Enum):
    TASK_EXECUTION = "task_execution"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"
    ANALYSIS = "analysis"
    RESEARCH = "research"
    PLANNING = "planning"

    GAME_AUTOMATION = "game_automation"
    HOME_AUTOMATION = "home_automation"
    AI_ASSISTANCE = "ai_assistance"
    DATA_ANALYSIS = "data_analysis"
    SYSTEM_ADMINISTRATION = "system_administration"

    IPC_BRIDGE = "ipc_bridge"
    BATCH_PROCESSING = "batch_processing"
    WORKFLOW_ORCHESTRATION = "workflow_orchestration"

    USER_ENGAGEMENT = "user_engagement"
    MOBILE_EXTENSION = "mobile_extension"


class ExecutionMode(Enum):
    AUTOMATIC = "automatic"
    SEMI_AUTOMATIC = "semi_automatic"
    MANUAL = "manual"
    AGENT_ASSISTED = "agent_assisted"


def normalize_task_priority(value: str | TaskPriority) -> TaskPriority:
    if isinstance(value, TaskPriority):
        return value
    normalized = value.strip().lower().replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())
    alias_map = {
        "low": TaskPriority.LOW,
        "medium": TaskPriority.MEDIUM,
        "normal": TaskPriority.MEDIUM,
        "high": TaskPriority.HIGH,
        "urgent": TaskPriority.URGENT,
        "critical": TaskPriority.CRITICAL,
    }
    return alias_map.get(normalized, TaskPriority.MEDIUM)


def normalize_task_status(value: str | TaskStatus) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    normalized = value.strip().lower().replace("-", "_")
    alias_map = {
        "queued": TaskStatus.QUEUED,
        "in_progress": TaskStatus.IN_PROGRESS,
        "in progress": TaskStatus.IN_PROGRESS,
        "blocked": TaskStatus.BLOCKED,
        "done": TaskStatus.DONE,
        "completed": TaskStatus.DONE,
        "failed": TaskStatus.FAILED,
        "cancelled": TaskStatus.CANCELLED,
        "canceled": TaskStatus.CANCELLED,
    }
    return alias_map.get(normalized, TaskStatus.QUEUED)


def normalize_agent_capability(
    value: str | AgentCapability,
) -> Optional[AgentCapability]:
    if isinstance(value, AgentCapability):
        return value
    normalized = value.strip().lower().replace(" ", "_")
    try:
        return AgentCapability(normalized)
    except ValueError:
        return None


def normalize_agent_role(value: str | AgentRole | None) -> AgentRole:
    if value is None:
        return AgentRole.GENERAL
    if isinstance(value, AgentRole):
        return value
    normalized = value.strip().lower().replace("-", "_")
    alias_map = {
        "general": AgentRole.GENERAL,
        "merlin": AgentRole.MERLIN,
        "fortress": AgentRole.FORTRESS,
        "androidapp": AgentRole.ANDROID_APP,
        "android": AgentRole.ANDROID_APP,
        "mobile": AgentRole.ANDROID_APP,
        "desktop": AgentRole.DESKTOP,
        "ui": AgentRole.DESKTOP,
    }
    return alias_map.get(normalized, AgentRole.GENERAL)


def normalize_execution_mode(value: str | ExecutionMode | None) -> ExecutionMode:
    if value is None:
        return ExecutionMode.AUTOMATIC
    if isinstance(value, ExecutionMode):
        return value
    normalized = value.strip().lower().replace("-", "_")
    alias_map = {
        "automatic": ExecutionMode.AUTOMATIC,
        "auto": ExecutionMode.AUTOMATIC,
        "semi_automatic": ExecutionMode.SEMI_AUTOMATIC,
        "semi": ExecutionMode.SEMI_AUTOMATIC,
        "manual": ExecutionMode.MANUAL,
        "agent_assisted": ExecutionMode.AGENT_ASSISTED,
        "assisted": ExecutionMode.AGENT_ASSISTED,
    }
    return alias_map.get(normalized, ExecutionMode.AUTOMATIC)
