"""
Guild Task Director - Unified task lifecycle management
"""

import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from loguru import logger
from datetime import datetime, timezone
import json

from .communication_hub import CommunicationChannel, MessagePriority
from .schema import (
    TaskStatus,
    TaskPriority,
    ExecutionMode,
    normalize_task_priority,
    normalize_task_status,
    normalize_execution_mode,
)


@dataclass
class Task:
    """Enhanced task representation with full lifecycle tracking"""

    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    capabilities_required: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    claimed_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "assignee": self.assignee,
            "dependencies": self.dependencies,
            "capabilities_required": self.capabilities_required,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "claimed_at": self.claimed_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
            "execution_history": self.execution_history,
        }


class TaskDirector:
    """
    Unified task lifecycle management system.

    Responsibilities:
    - Task creation, claiming, and completion
    - Dependency resolution and blocking
    - Task prioritization and routing
    - Integration with existing task board (Markdown)
    - Database synchronization
    - Task metrics and analytics
    """

    def __init__(self, config, guild_core):
        self.config = config
        self.guild_core = guild_core
        self._running = False

        # Task storage and indexing
        self._tasks: Dict[str, Task] = {}
        self._task_index_by_status: Dict[TaskStatus, Set[str]] = {
            status: set() for status in TaskStatus
        }
        self._task_index_by_assignee: Dict[str, Set[str]] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}  # task_id -> dependents

        # Task board integration
        self.task_board_path = Path(config.task_board_path)

        # Synchronization
        self._sync_task: Optional[asyncio.Task] = None
        self._sync_interval = 30  # seconds

        logger.info("Task Director initialized")

    async def start(self) -> None:
        """Start the task director"""
        if self._running:
            return

        self._running = True

        # Load existing tasks
        await self._load_tasks()

        # Start synchronization
        self._sync_task = asyncio.create_task(self._sync_loop())

        # Subscribe to communication events
        self.guild_core.communication_hub.subscribe(
            CommunicationChannel.TASK_UPDATES, self._handle_task_event
        )

        logger.info("Task Director started")

    async def stop(self) -> None:
        """Stop the task director"""
        if not self._running:
            return

        self._running = False

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Save current state
        await self._save_tasks()

        logger.info("Task Director stopped")

    async def _load_tasks(self) -> None:
        """Load tasks from task board and database"""
        try:
            # Load from Markdown task board (existing format)
            if self.task_board_path.exists():
                await self._load_from_markdown()

            # Load from database if available
            if self.guild_core.hub and hasattr(self.guild_core.hub, "db"):
                await self._load_from_database()

            logger.info(f"Loaded {len(self._tasks)} tasks")

        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")

    async def _load_from_markdown(self) -> None:
        """Load tasks from existing Markdown task board"""
        try:
            # Use existing GuildManager parsing logic
            from core.guild_manager import GuildManager

            guild_manager = GuildManager(config=self.config)
            lines, tasks, status_map = guild_manager.parse_board()

            for task_data in tasks:
                metadata = {
                    "execution_mode": task_data.get("execution_mode") or "automatic",
                    "approvals": self._parse_approvals(task_data.get("approvals", "")),
                }
                preferred_role = task_data.get("preferred_role")
                if preferred_role and preferred_role != "-":
                    metadata["preferred_role"] = preferred_role
                domain = task_data.get("domain")
                if domain and domain != "-":
                    metadata["domain"] = domain

                task = Task(
                    id=task_data.get("id", ""),
                    title=task_data.get("title", ""),
                    description=task_data.get("description", ""),
                    status=normalize_task_status(task_data.get("status", "queued")),
                    priority=normalize_task_priority(
                        task_data.get("priority", "medium")
                    ),
                    assignee=(
                        task_data.get("assignee")
                        if task_data.get("assignee") != "-"
                        else None
                    ),
                    dependencies=self._parse_dependencies(
                        task_data.get("depends_on", "")
                    ),
                    created_at=task_data.get("created", ""),
                    updated_at=task_data.get("updated", ""),
                    metadata=metadata,
                )

                await self._add_task_internal(task)

        except Exception as e:
            logger.error(f"Failed to load from Markdown: {e}")

    async def _load_from_database(self) -> None:
        """Load tasks from database"""
        try:
            # Implementation depends on database schema
            # This would integrate with existing db_models.py Task model
            pass
        except Exception as e:
            logger.error(f"Failed to load from database: {e}")

    def _parse_dependencies(self, depends_on: str) -> List[str]:
        """Parse dependency string into list of task IDs"""
        if not depends_on or depends_on == "-":
            return []
        return [dep.strip() for dep in depends_on.split(",") if dep.strip()]

    def _parse_approvals(self, approvals: str) -> Dict[str, Any]:
        if not approvals or approvals == "-":
            return {}
        result: Dict[str, Any] = {}
        for entry in approvals.split(","):
            entry = entry.strip()
            if not entry or ":" not in entry:
                continue
            gate, status = entry.split(":", 1)
            result[gate.strip()] = {"status": status.strip()}
        return result

    async def _add_task_internal(self, task: Task) -> None:
        """Add task to internal storage and indexes"""
        self._ensure_task_metadata(task)
        self._tasks[task.id] = task

        # Update indexes
        self._task_index_by_status[task.status].add(task.id)

        if task.assignee:
            if task.assignee not in self._task_index_by_assignee:
                self._task_index_by_assignee[task.assignee] = set()
            self._task_index_by_assignee[task.assignee].add(task.id)

        # Update dependency graph
        for dep_id in task.dependencies:
            if dep_id not in self._dependency_graph:
                self._dependency_graph[dep_id] = set()
            self._dependency_graph[dep_id].add(task.id)

    def _ensure_task_metadata(self, task: Task) -> None:
        if not isinstance(task.metadata, dict):
            task.metadata = {}
        if "execution_mode" not in task.metadata:
            task.metadata["execution_mode"] = ExecutionMode.AUTOMATIC.value
        else:
            task.metadata["execution_mode"] = normalize_execution_mode(
                task.metadata.get("execution_mode")
            ).value
        approvals = task.metadata.get("approvals")
        if not isinstance(approvals, dict):
            task.metadata["approvals"] = {}

    async def create_task(
        self,
        title: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: Optional[List[str]] = None,
        capabilities_required: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new task"""
        import uuid

        priority = normalize_task_priority(priority)
        metadata = metadata or {}
        metadata["execution_mode"] = normalize_execution_mode(
            metadata.get("execution_mode")
        ).value
        if not isinstance(metadata.get("approvals"), dict):
            metadata["approvals"] = {}

        # Generate unique task ID
        task_id = f"AAS-{len(self._tasks) + 1:03d}"

        # Ensure unique ID
        while task_id in self._tasks:
            task_id = f"AAS-{len(self._tasks) + 1:03d}-{uuid.uuid4().hex[:4]}"

        task = Task(
            id=task_id,
            title=title,
            description=description,
            status=TaskStatus.QUEUED,
            priority=priority,
            dependencies=dependencies or [],
            capabilities_required=capabilities_required or [],
            metadata=metadata,
        )

        await self._add_task_internal(task)

        # Emit event
        await self.guild_core.communication_hub.emit_event(
            "task.created",
            {"task_id": task_id, "title": title, "priority": priority.value},
            CommunicationChannel.TASK_UPDATES,
            MessagePriority.NORMAL,
        )

        logger.info(f"Created task {task_id}: {title}")
        return task_id

    async def claim_task(
        self, agent_id: str, task_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Claim a task for an agent"""
        try:
            if task_id:
                # Claim specific task
                if task_id not in self._tasks:
                    return None
                task = self._tasks[task_id]
            else:
                # Find next available task
                task = await self._find_next_claimable_task(agent_id)
                if not task:
                    return None

            # Check if task is claimable
            if not await self._is_task_claimable(task, agent_id):
                return None

            execution_mode = normalize_execution_mode(
                task.metadata.get("execution_mode")
            )
            requires_execute = self._requires_execute_gate(task)

            if requires_execute:
                approved = await self._ensure_gate_approval(
                    task, "execute", execution_mode
                )
                if not approved:
                    old_status = task.status
                    task.assignee = agent_id
                    task.status = TaskStatus.BLOCKED
                    task.updated_at = datetime.now(timezone.utc).isoformat()

                    self._task_index_by_status[old_status].discard(task.id)
                    self._task_index_by_status[TaskStatus.BLOCKED].add(task.id)
                    self._task_index_by_assignee.setdefault(agent_id, set()).add(
                        task.id
                    )

                    task.execution_history.append(
                        {
                            "action": "execution_pending",
                            "agent_id": agent_id,
                            "timestamp": task.updated_at,
                        }
                    )

                    await self.guild_core.communication_hub.emit_event(
                        "task.execution_pending",
                        {
                            "task_id": task.id,
                            "agent_id": agent_id,
                            "title": task.title,
                        },
                        CommunicationChannel.TASK_UPDATES,
                        MessagePriority.HIGH,
                    )

                    logger.info(
                        f"Task {task.id} pending execution approval for {agent_id}"
                    )
                    return task.to_dict()

            # Claim the task
            old_status = task.status
            task.status = TaskStatus.IN_PROGRESS
            task.assignee = agent_id
            task.claimed_at = datetime.now(timezone.utc).isoformat()
            task.updated_at = task.claimed_at

            # Update indexes
            self._task_index_by_status[old_status].discard(task.id)
            self._task_index_by_status[TaskStatus.IN_PROGRESS].add(task.id)

            if agent_id not in self._task_index_by_assignee:
                self._task_index_by_assignee[agent_id] = set()
            self._task_index_by_assignee[agent_id].add(task.id)

            # Add to execution history
            task.execution_history.append(
                {
                    "action": "claimed",
                    "agent_id": agent_id,
                    "timestamp": task.claimed_at,
                }
            )

            # Emit event
            await self.guild_core.communication_hub.emit_event(
                "task.claimed",
                {"task_id": task.id, "agent_id": agent_id, "title": task.title},
                CommunicationChannel.TASK_UPDATES,
                MessagePriority.HIGH,
            )

            logger.info(f"Task {task.id} claimed by {agent_id}")
            return task.to_dict()

        except Exception as e:
            logger.error(f"Failed to claim task: {e}")
            return None

    async def _find_next_claimable_task(self, agent_id: str) -> Optional[Task]:
        """Find the next claimable task for an agent"""
        # Get agent capabilities
        agent_capabilities = await self._get_agent_capabilities(agent_id)

        # Get queued tasks sorted by priority
        queued_tasks = [
            self._tasks[task_id]
            for task_id in self._task_index_by_status[TaskStatus.QUEUED]
        ]

        # Sort by priority (urgent first)
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.URGENT: 1,
            TaskPriority.HIGH: 2,
            TaskPriority.MEDIUM: 3,
            TaskPriority.LOW: 4,
        }
        queued_tasks.sort(key=lambda t: priority_order[t.priority])

        # Find first claimable task
        for task in queued_tasks:
            if await self._is_task_claimable(task, agent_id, agent_capabilities):
                return task

        return None

    async def _is_task_claimable(
        self, task: Task, agent_id: str, agent_capabilities: Optional[List[str]] = None
    ) -> bool:
        """Check if a task can be claimed by an agent"""
        # Check if task is in correct status
        if task.status != TaskStatus.QUEUED:
            return False

        # Check dependencies
        if not await self._are_dependencies_met(task):
            return False

        execution_mode = normalize_execution_mode(task.metadata.get("execution_mode"))
        if execution_mode in {ExecutionMode.MANUAL, ExecutionMode.SEMI_AUTOMATIC}:
            approved = await self._ensure_gate_approval(task, "claim", execution_mode)
            if not approved:
                return False

        # Check capabilities
        if agent_capabilities is None:
            agent_capabilities = await self._get_agent_capabilities(agent_id)

        if task.capabilities_required:
            if not all(cap in agent_capabilities for cap in task.capabilities_required):
                return False

        return True

    async def _ensure_gate_approval(
        self, task: Task, gate: str, mode: ExecutionMode
    ) -> bool:
        approvals = task.metadata.setdefault("approvals", {})
        gate_state = approvals.get(gate, {}) if isinstance(approvals, dict) else {}
        status = gate_state.get("status")

        if status == "approved":
            return True
        if status == "rejected":
            return False

        hub = self.guild_core.hub
        if hub and getattr(hub, "approvals", None):
            existing = hub.approvals.get_for_task(task.id, gate)
            if existing:
                approvals[gate] = {
                    "status": existing.status,
                    "request_id": existing.approval_id,
                    "targets": existing.targets,
                }
                return existing.status == "approved"

            targets = gate_state.get("targets")
            if not targets:
                targets = task.metadata.get("approval_targets") or [
                    "desktop",
                    "androidapp",
                ]
            metadata = {
                "execution_mode": mode.value,
                "title": task.title,
                "priority": task.priority.value,
            }
            approval = await hub.approvals.request(
                task_id=task.id,
                gate=gate,
                requested_by="guild.task_director",
                targets=targets,
                metadata=metadata,
            )
            approvals[gate] = {
                "status": approval.status,
                "request_id": approval.approval_id,
                "targets": approval.targets,
            }
        return False

    def _requires_execute_gate(self, task: Task) -> bool:
        if task.metadata.get("execution_gate") is True:
            return True
        if task.metadata.get("require_execute_gate") is True:
            return True
        gates = task.metadata.get("approval_gates")
        if isinstance(gates, list) and "execute" in gates:
            return True
        return False

    async def start_execution(self, task_id: str, agent_id: str) -> bool:
        """Begin execution for a task after execute approval."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.assignee and task.assignee != agent_id:
            logger.warning(
                f"Agent {agent_id} cannot execute task assigned to {task.assignee}"
            )
            return False

        execution_mode = normalize_execution_mode(task.metadata.get("execution_mode"))
        if self._requires_execute_gate(task):
            approved = await self._ensure_gate_approval(task, "execute", execution_mode)
            if not approved:
                return False

        if task.status == TaskStatus.IN_PROGRESS:
            return True

        old_status = task.status
        task.status = TaskStatus.IN_PROGRESS
        task.assignee = agent_id
        task.claimed_at = datetime.now(timezone.utc).isoformat()
        task.updated_at = task.claimed_at

        self._task_index_by_status[old_status].discard(task.id)
        self._task_index_by_status[TaskStatus.IN_PROGRESS].add(task.id)
        self._task_index_by_assignee.setdefault(agent_id, set()).add(task.id)

        task.execution_history.append(
            {
                "action": "execution_started",
                "agent_id": agent_id,
                "timestamp": task.claimed_at,
            }
        )

        await self.guild_core.communication_hub.emit_event(
            "task.execution_started",
            {"task_id": task.id, "agent_id": agent_id, "title": task.title},
            CommunicationChannel.TASK_UPDATES,
            MessagePriority.HIGH,
        )
        return True

    async def _are_dependencies_met(self, task: Task) -> bool:
        """Check if all task dependencies are completed"""
        for dep_id in task.dependencies:
            if dep_id not in self._tasks:
                continue  # Missing dependency treated as unmet

            dep_task = self._tasks[dep_id]
            if dep_task.status != TaskStatus.DONE:
                return False

        return True

    async def _get_agent_capabilities(self, agent_id: str) -> List[str]:
        """Get capabilities for an agent"""
        try:
            # Query agent coordinator for capabilities
            return await self.guild_core.agent_coordinator.get_agent_capabilities(
                agent_id
            )
        except Exception:
            return []  # Default to no specific capabilities

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self._tasks.get(task_id)

    async def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """List tasks, optionally filtered by status"""
        if status is None:
            return list(self._tasks.values())
        return [self._tasks[task_id] for task_id in self._task_index_by_status[status]]

    async def set_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        metadata: Optional[Dict[str, Any]] = None,
        assignee: Optional[str] = None,
    ) -> bool:
        """Force-update task status (admin/operational overrides)."""
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        old_status = task.status

        if old_status == status:
            if metadata:
                task.metadata.update(metadata)
            return True

        self._task_index_by_status[old_status].discard(task_id)
        self._task_index_by_status[status].add(task_id)

        if assignee is not None:
            if task.assignee and task.assignee in self._task_index_by_assignee:
                self._task_index_by_assignee[task.assignee].discard(task_id)
            task.assignee = assignee
            if assignee:
                self._task_index_by_assignee.setdefault(assignee, set()).add(task_id)

        task.status = status
        task.updated_at = datetime.now(timezone.utc).isoformat()
        if status == TaskStatus.IN_PROGRESS and not task.claimed_at:
            task.claimed_at = task.updated_at
        if status == TaskStatus.DONE:
            task.completed_at = task.updated_at

        if metadata:
            task.metadata.update(metadata)

        await self.guild_core.communication_hub.emit_event(
            "task.status_changed",
            {
                "task_id": task_id,
                "old_status": old_status.value,
                "new_status": status.value,
            },
            CommunicationChannel.TASK_UPDATES,
            MessagePriority.NORMAL,
        )
        return True

    async def complete_task(
        self, task_id: str, agent_id: str, result: Dict[str, Any]
    ) -> bool:
        """Complete a task"""
        try:
            if task_id not in self._tasks:
                return False

            task = self._tasks[task_id]

            # Verify agent can complete this task
            if task.assignee != agent_id:
                logger.warning(
                    f"Agent {agent_id} cannot complete task {task_id} assigned to {task.assignee}"
                )
                return False

            # Update task
            old_status = task.status
            task.status = TaskStatus.DONE
            task.completed_at = datetime.now(timezone.utc).isoformat()
            task.updated_at = task.completed_at
            task.metadata.update(result)

            # Update indexes
            self._task_index_by_status[old_status].discard(task.id)
            self._task_index_by_status[TaskStatus.DONE].add(task.id)

            # Add to execution history
            task.execution_history.append(
                {
                    "action": "completed",
                    "agent_id": agent_id,
                    "timestamp": task.completed_at,
                    "result": result,
                }
            )

            # Check for unblocked tasks
            await self._check_unblocked_tasks(task_id)

            # Emit event
            await self.guild_core.communication_hub.emit_event(
                "task.completed",
                {
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "title": task.title,
                    "result": result,
                },
                CommunicationChannel.TASK_UPDATES,
                MessagePriority.HIGH,
            )

            logger.info(f"Task {task_id} completed by {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")
            return False

    async def _check_unblocked_tasks(self, completed_task_id: str) -> None:
        """Check for tasks that may now be unblocked"""
        if completed_task_id in self._dependency_graph:
            dependent_task_ids = self._dependency_graph[completed_task_id]

            for dep_task_id in dependent_task_ids:
                if dep_task_id in self._tasks:
                    dep_task = self._tasks[dep_task_id]
                    if (
                        dep_task.status == TaskStatus.BLOCKED
                        and await self._are_dependencies_met(dep_task)
                    ):
                        # Unblock task
                        self._task_index_by_status[TaskStatus.BLOCKED].discard(
                            dep_task_id
                        )
                        dep_task.status = TaskStatus.QUEUED
                        self._task_index_by_status[TaskStatus.QUEUED].add(dep_task_id)
                        dep_task.updated_at = datetime.now(timezone.utc).isoformat()

                        # Emit event
                        await self.guild_core.communication_hub.emit_event(
                            "task.unblocked",
                            {"task_id": dep_task_id, "title": dep_task.title},
                            CommunicationChannel.TASK_UPDATES,
                            MessagePriority.NORMAL,
                        )

                        logger.info(f"Task {dep_task_id} unblocked")

    async def get_active_count(self) -> int:
        """Get count of active (in progress) tasks"""
        return len(self._task_index_by_status[TaskStatus.IN_PROGRESS])

    async def get_health(self) -> Dict[str, Any]:
        """Get health status of task director"""
        return {
            "status": "healthy" if self._running else "stopped",
            "total_tasks": len(self._tasks),
            "by_status": {
                status.value: len(task_ids)
                for status, task_ids in self._task_index_by_status.items()
            },
            "active_agents": len(self._task_index_by_assignee),
            "dependency_graph_size": len(self._dependency_graph),
        }

    async def _handle_task_event(self, message) -> None:
        """Handle task-related events from communication hub"""
        try:
            event_type = message.event_type
            data = message.payload

            if event_type == "task.priority_changed":
                await self._handle_priority_change(data)
            elif event_type == "task.dependency_added":
                await self._handle_dependency_change(data)
            elif event_type.startswith("legacy."):
                await self._handle_task_context(data)
            # Add more event handlers as needed

        except Exception as e:
            logger.error(f"Failed to handle task event: {e}")

    async def _handle_priority_change(self, data: Dict[str, Any]) -> None:
        """Handle priority updates from external systems."""
        task_id = data.get("task_id")
        new_priority = data.get("priority")
        if not task_id or not new_priority:
            return
        task = self._tasks.get(task_id)
        if not task:
            return
        task.priority = normalize_task_priority(new_priority)
        task.updated_at = datetime.now(timezone.utc).isoformat()

    async def _handle_dependency_change(self, data: Dict[str, Any]) -> None:
        """Handle dependency updates from external systems."""
        task_id = data.get("task_id")
        dependency = data.get("dependency")
        if not task_id or not dependency:
            return
        task = self._tasks.get(task_id)
        if not task:
            return
        if dependency not in task.dependencies:
            task.dependencies.append(dependency)
            self._dependency_graph.setdefault(dependency, set()).add(task_id)
            task.updated_at = datetime.now(timezone.utc).isoformat()

    async def _handle_task_context(self, data: Dict[str, Any]) -> None:
        """Handle task context updates (domain/role hints)."""
        task_id = data.get("task_id")
        if not task_id:
            return
        task = self._tasks.get(task_id)
        if not task:
            return
        if data.get("preferred_role"):
            task.metadata["preferred_role"] = data.get("preferred_role")
        if data.get("domain"):
            task.metadata["domain"] = data.get("domain")
        task.updated_at = datetime.now(timezone.utc).isoformat()

    async def _sync_loop(self) -> None:
        """Periodic synchronization with external systems"""
        while self._running:
            try:
                await self._sync_with_markdown()
                await self._sync_with_database()
                await asyncio.sleep(self._sync_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync error: {e}")
                await asyncio.sleep(5)

    async def _sync_with_markdown(self) -> None:
        """Sync tasks with Markdown task board"""
        try:
            self.task_board_path.parent.mkdir(parents=True, exist_ok=True)

            header = "| ID | Priority | Title | Depends On | Status | Assignee | Created | Updated | Mode | Approvals | Preferred Role | Domain |\n"
            separator = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"

            def safe(value: Any) -> str:
                text = str(value) if value is not None else "-"
                return text.replace("|", "/")

            def format_approvals(task: Task) -> str:
                approvals = task.metadata.get("approvals", {})
                if not isinstance(approvals, dict) or not approvals:
                    return "-"
                parts = []
                for gate, info in approvals.items():
                    if not isinstance(info, dict):
                        continue
                    status = info.get("status", "pending")
                    parts.append(f"{gate}:{status}")
                return ", ".join(parts) if parts else "-"

            rows = []
            tasks = list(self._tasks.values())
            tasks.sort(key=lambda t: t.id)
            for task in tasks:
                mode = task.metadata.get(
                    "execution_mode", ExecutionMode.AUTOMATIC.value
                )
                approvals = format_approvals(task)
                preferred_role = task.metadata.get("preferred_role", "-")
                domain = task.metadata.get("domain", "-")
                row = (
                    f"| {safe(task.id)} | {safe(task.priority.value)} | {safe(task.title)} | "
                    f"{safe(', '.join(task.dependencies) if task.dependencies else '-')} | {safe(task.status.value)} | "
                    f"{safe(task.assignee or '-')} | {safe(task.created_at)} | {safe(task.updated_at)} | {safe(mode)} | "
                    f"{safe(approvals)} | {safe(preferred_role)} | {safe(domain)} |\n"
                )
                rows.append(row)

            with open(self.task_board_path, "w", encoding="utf-8") as handle:
                handle.write(header)
                handle.write(separator)
                handle.writelines(rows)
        except Exception as e:
            logger.error(f"Failed to sync Markdown board: {e}")

    async def _sync_with_database(self) -> None:
        """Sync tasks with database"""
        hub = self.guild_core.hub
        if not hub or not hasattr(hub, "db"):
            return
        try:
            from core.db_models import Task as DbTask
            from core.db_models import TaskStatus as DbStatus
            from core.db_models import TaskPriority as DbPriority
            from datetime import datetime

            def map_status(status: TaskStatus) -> DbStatus:
                if status == TaskStatus.BLOCKED:
                    return DbStatus.BLOCKED
                if status == TaskStatus.IN_PROGRESS:
                    return DbStatus.IN_PROGRESS
                if status == TaskStatus.DONE:
                    return DbStatus.DONE
                if status == TaskStatus.FAILED:
                    return DbStatus.FAILED
                if status == TaskStatus.QUEUED:
                    return DbStatus.QUEUED
                return DbStatus.QUEUED

            def map_priority(priority: TaskPriority) -> DbPriority:
                if priority == TaskPriority.URGENT or priority == TaskPriority.CRITICAL:
                    return DbPriority.URGENT
                if priority == TaskPriority.HIGH:
                    return DbPriority.HIGH
                if priority == TaskPriority.LOW:
                    return DbPriority.LOW
                return DbPriority.MEDIUM

            with hub.db.get_session() as session:
                for task in self._tasks.values():
                    db_task = session.query(DbTask).filter(DbTask.id == task.id).first()
                    if not db_task:
                        db_task = DbTask(id=task.id, title=task.title)
                        session.add(db_task)

                    db_task.title = task.title
                    db_task.description = task.description
                    db_task.priority = map_priority(task.priority)
                    db_status = map_status(task.status)

                    mode = task.metadata.get("execution_mode")
                    approvals = task.metadata.get("approvals", {})
                    if (
                        task.status == TaskStatus.QUEUED
                        and isinstance(approvals, dict)
                        and mode
                        in {
                            ExecutionMode.MANUAL.value,
                            ExecutionMode.SEMI_AUTOMATIC.value,
                        }
                    ):
                        claim_state = approvals.get("claim", {})
                        if (
                            isinstance(claim_state, dict)
                            and claim_state.get("status") != "approved"
                        ):
                            db_status = DbStatus.PENDING_APPROVAL

                    db_task.status = db_status
                    db_task.assignee = task.assignee
                    db_task.dependencies = task.dependencies or []

                    if task.created_at:
                        db_task.created_at = datetime.fromisoformat(
                            task.created_at.replace("Z", "+00:00")
                        )
                    if task.updated_at:
                        db_task.updated_at = datetime.fromisoformat(
                            task.updated_at.replace("Z", "+00:00")
                        )
                    if task.claimed_at:
                        db_task.started_at = datetime.fromisoformat(
                            task.claimed_at.replace("Z", "+00:00")
                        )
                    if task.completed_at:
                        db_task.completed_at = datetime.fromisoformat(
                            task.completed_at.replace("Z", "+00:00")
                        )

                    tags = list(db_task.tags or []) if hasattr(db_task, "tags") else []
                    tags = [
                        t
                        for t in tags
                        if not t.startswith("mode:") and not t.startswith("approval:")
                    ]

                    if mode:
                        tags.append(f"mode:{mode}")

                    if isinstance(approvals, dict):
                        for gate, info in approvals.items():
                            if isinstance(info, dict):
                                status = info.get("status", "pending")
                                tags.append(f"approval:{gate}={status}")

                    if tags:
                        db_task.tags = list(dict.fromkeys(tags))
        except Exception as e:
            logger.error(f"Failed to sync tasks to database: {e}")

    async def _save_tasks(self) -> None:
        """Save current task state"""
        try:
            # Save to JSON for persistence
            state_file = Path(self.config.artifact_dir) / "task_director_state.json"
            state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                "tasks": {
                    task_id: task.to_dict() for task_id, task in self._tasks.items()
                },
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

            logger.debug("Task state saved")

        except Exception as e:
            logger.error(f"Failed to save task state: {e}")
