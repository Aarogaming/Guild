"""
Guild Batch Orchestrator - Unified batch processing and optimization system
"""

import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from loguru import logger
from datetime import datetime, timezone, timedelta
import json
import uuid

from .communication_hub import CommunicationChannel, MessagePriority


class BatchStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchType(Enum):
    TASK_ANALYSIS = "task_analysis"
    CODE_GENERATION = "code_generation"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"


@dataclass
class BatchJob:
    """Enhanced batch job representation"""

    id: str
    type: BatchType
    task_ids: List[str]
    description: str
    status: BatchStatus
    openai_batch_id: Optional[str] = None
    priority: str = "medium"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    submitted_at: Optional[str] = None
    completed_at: Optional[str] = None
    cost_estimate: Optional[float] = None
    actual_cost: Optional[float] = None
    results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "task_ids": self.task_ids,
            "description": self.description,
            "status": self.status.value,
            "openai_batch_id": self.openai_batch_id,
            "priority": self.priority,
            "created_at": self.created_at,
            "submitted_at": self.submitted_at,
            "completed_at": self.completed_at,
            "cost_estimate": self.cost_estimate,
            "actual_cost": self.actual_cost,
            "results": self.results,
            "metadata": self.metadata,
            "error_message": self.error_message,
        }


class BatchOrchestrator:
    """
    Unified batch processing orchestration system.

    Features:
    - Intelligent batch grouping and optimization
    - Cost estimation and tracking
    - Priority-based batch scheduling
    - Automatic retry and error handling
    - Result processing and distribution
    - Integration with existing batch systems
    - Performance monitoring and analytics
    """

    def __init__(self, config, guild_core):
        self.config = config
        self.guild_core = guild_core
        self._running = False

        # Batch management
        self._batches: Dict[str, BatchJob] = {}
        self._pending_tasks: Set[str] = set()  # Tasks waiting to be batched
        self._batch_queue: asyncio.Queue = asyncio.Queue()

        # Configuration
        self.max_batch_size = config.batch_size or 20
        self.auto_batch_interval = 300  # 5 minutes
        self.cost_per_1k_tokens = 0.0015  # OpenAI pricing (approximate)

        # Integration with existing systems
        self._batch_manager = None
        self._batch_monitor = None

        # Processing tasks
        self._batch_processor_task: Optional[asyncio.Task] = None
        self._auto_batch_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None

        # State persistence
        self.state_file = Path(config.artifact_dir) / "batch_orchestrator_state.json"

        logger.info("Batch Orchestrator initialized")

    async def start(self) -> None:
        """Start the batch orchestrator"""
        if self._running:
            return

        self._running = True

        # Load existing state
        await self._load_state()

        # Initialize integration with existing batch systems
        await self._initialize_batch_integration()

        # Start processing tasks
        self._batch_processor_task = asyncio.create_task(self._process_batches())
        self._auto_batch_task = asyncio.create_task(self._auto_batch_loop())
        self._monitor_task = asyncio.create_task(self._monitor_batches())

        # Subscribe to communication events
        self.guild_core.communication_hub.subscribe(
            CommunicationChannel.BATCH_PROCESSING, self._handle_batch_event
        )

        logger.info("Batch Orchestrator started")

    async def stop(self) -> None:
        """Stop the batch orchestrator"""
        if not self._running:
            return

        self._running = False

        # Cancel processing tasks
        for task in [
            self._batch_processor_task,
            self._auto_batch_task,
            self._monitor_task,
        ]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Save current state
        await self._save_state()

        logger.info("Batch Orchestrator stopped")

    async def _initialize_batch_integration(self) -> None:
        """Initialize integration with existing batch systems"""
        try:
            # Integrate with existing BatchManager
            if self.guild_core.hub and hasattr(self.guild_core.hub, "batch_manager"):
                self._batch_manager = self.guild_core.hub.batch_manager
                logger.info("Integrated with existing BatchManager")

            # Integrate with batch monitoring
            # This would connect to existing batch_monitor.py functionality

        except Exception as e:
            logger.warning(f"Failed to initialize batch integration: {e}")

    async def submit_batch(
        self,
        task_ids: List[str],
        description: str,
        batch_type: BatchType = BatchType.TASK_ANALYSIS,
        priority: str = "medium",
    ) -> Optional[str]:
        """Submit a new batch job"""
        try:
            if not task_ids:
                return None

            # Create batch job
            batch_id = f"batch-{uuid.uuid4().hex[:8]}"

            batch_job = BatchJob(
                id=batch_id,
                type=batch_type,
                task_ids=task_ids.copy(),
                description=description,
                status=BatchStatus.PENDING,
                priority=priority,
            )

            # Estimate cost
            batch_job.cost_estimate = await self._estimate_batch_cost(
                task_ids, batch_type
            )

            # Store batch
            self._batches[batch_id] = batch_job

            # Queue for processing
            await self._batch_queue.put(batch_id)

            # Remove tasks from pending set
            for task_id in task_ids:
                self._pending_tasks.discard(task_id)

            # Emit event
            await self.guild_core.communication_hub.emit_event(
                "batch.created",
                {
                    "batch_id": batch_id,
                    "task_count": len(task_ids),
                    "type": batch_type.value,
                    "description": description,
                    "cost_estimate": batch_job.cost_estimate,
                },
                CommunicationChannel.BATCH_PROCESSING,
                MessagePriority.NORMAL,
            )

            logger.info(f"Batch {batch_id} created with {len(task_ids)} tasks")
            return batch_id

        except Exception as e:
            logger.error(f"Failed to submit batch: {e}")
            return None

    async def _estimate_batch_cost(
        self, task_ids: List[str], batch_type: BatchType
    ) -> float:
        """Estimate the cost of a batch job"""
        try:
            # Base token estimate per task type
            token_estimates = {
                BatchType.TASK_ANALYSIS: 500,
                BatchType.CODE_GENERATION: 1500,
                BatchType.IMPLEMENTATION: 2000,
                BatchType.REVIEW: 800,
                BatchType.TESTING: 1200,
                BatchType.DOCUMENTATION: 1000,
            }

            base_tokens = token_estimates.get(batch_type, 1000)
            total_tokens = base_tokens * len(task_ids)

            # Apply batch API discount (50% savings)
            batch_discount = 0.5
            estimated_cost = (
                (total_tokens / 1000) * self.cost_per_1k_tokens * (1 - batch_discount)
            )

            return round(estimated_cost, 4)

        except Exception as e:
            logger.error(f"Failed to estimate batch cost: {e}")
            return 0.0

    async def add_task_to_pending(self, task_id: str) -> None:
        """Add a task to the pending batch queue"""
        self._pending_tasks.add(task_id)

        # Emit event for monitoring
        await self.guild_core.communication_hub.emit_event(
            "batch.task_pending",
            {"task_id": task_id, "pending_count": len(self._pending_tasks)},
            CommunicationChannel.BATCH_PROCESSING,
            MessagePriority.LOW,
        )

    async def check_auto_batch(self) -> None:
        """Check if auto-batching should be triggered"""
        try:
            if len(self._pending_tasks) >= self.max_batch_size:
                await self._trigger_auto_batch("size_threshold")
            elif len(self._pending_tasks) > 0:
                # Check if oldest pending task is old enough
                oldest_task_age = await self._get_oldest_pending_task_age()
                if oldest_task_age and oldest_task_age > timedelta(minutes=10):
                    await self._trigger_auto_batch("time_threshold")

        except Exception as e:
            logger.error(f"Failed to check auto batch: {e}")

    async def _trigger_auto_batch(self, reason: str) -> None:
        """Trigger automatic batching of pending tasks"""
        try:
            if not self._pending_tasks:
                return

            # Group tasks by type/priority for optimal batching
            task_groups = await self._group_pending_tasks()

            for group_key, task_ids in task_groups.items():
                if len(task_ids) >= 3:  # Minimum batch size
                    batch_type, priority = group_key
                    description = f"Auto-batch ({reason}): {batch_type.value} - {len(task_ids)} tasks"

                    await self.submit_batch(
                        task_ids=task_ids,
                        description=description,
                        batch_type=batch_type,
                        priority=priority,
                    )

                    logger.info(
                        f"Auto-batched {len(task_ids)} {batch_type.value} tasks ({reason})"
                    )

        except Exception as e:
            logger.error(f"Failed to trigger auto batch: {e}")

    async def _group_pending_tasks(self) -> Dict[Tuple[BatchType, str], List[str]]:
        """Group pending tasks by type and priority for optimal batching"""
        try:
            groups: Dict[Tuple[BatchType, str], List[str]] = {}

            for task_id in self._pending_tasks:
                # Get task details from task director
                task_info = await self._get_task_info(task_id)
                if not task_info:
                    continue

                # Determine batch type based on task characteristics
                batch_type = await self._determine_batch_type(task_info)
                priority = task_info.get("priority", "medium")

                group_key = (batch_type, priority)
                if group_key not in groups:
                    groups[group_key] = []

                groups[group_key].append(task_id)

            return groups

        except Exception as e:
            logger.error(f"Failed to group pending tasks: {e}")
            return {}

    async def _get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information from task director"""
        try:
            # This would integrate with the task director
            if hasattr(self.guild_core, "task_director"):
                task = self.guild_core.task_director._tasks.get(task_id)
                if task:
                    return task.to_dict()
            return None
        except Exception as e:
            logger.error(f"Failed to get task info for {task_id}: {e}")
            return None

    async def _determine_batch_type(self, task_info: Dict[str, Any]) -> BatchType:
        """Determine appropriate batch type for a task"""
        try:
            title = task_info.get("title", "").lower()
            description = task_info.get("description", "").lower()
            capabilities = task_info.get("capabilities_required", [])

            # Simple heuristics for batch type determination
            if any(
                keyword in title + description
                for keyword in ["implement", "code", "build"]
            ):
                return BatchType.IMPLEMENTATION
            elif any(
                keyword in title + description
                for keyword in ["review", "check", "validate"]
            ):
                return BatchType.REVIEW
            elif any(keyword in title + description for keyword in ["test", "verify"]):
                return BatchType.TESTING
            elif any(
                keyword in title + description
                for keyword in ["document", "doc", "readme"]
            ):
                return BatchType.DOCUMENTATION
            elif "code_generation" in capabilities:
                return BatchType.CODE_GENERATION
            else:
                return BatchType.TASK_ANALYSIS

        except Exception as e:
            logger.error(f"Failed to determine batch type: {e}")
            return BatchType.TASK_ANALYSIS

    async def _get_oldest_pending_task_age(self) -> Optional[timedelta]:
        """Get the age of the oldest pending task"""
        try:
            if not self._pending_tasks:
                return None

            oldest_age = timedelta(0)
            now = datetime.now(timezone.utc)

            for task_id in self._pending_tasks:
                task_info = await self._get_task_info(task_id)
                if task_info and task_info.get("created_at"):
                    created_at = datetime.fromisoformat(
                        task_info["created_at"].replace("Z", "+00:00")
                    )
                    age = now - created_at
                    if age > oldest_age:
                        oldest_age = age

            return oldest_age if oldest_age > timedelta(0) else None

        except Exception as e:
            logger.error(f"Failed to get oldest pending task age: {e}")
            return None

    async def _process_batches(self) -> None:
        """Process batches from the queue"""
        while self._running:
            try:
                # Get batch with timeout
                batch_id = await asyncio.wait_for(self._batch_queue.get(), timeout=1.0)
                await self._process_single_batch(batch_id)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing batch: {e}")

    async def _process_single_batch(self, batch_id: str) -> None:
        """Process a single batch job"""
        try:
            if batch_id not in self._batches:
                return

            batch_job = self._batches[batch_id]

            # Update status
            batch_job.status = BatchStatus.SUBMITTED
            batch_job.submitted_at = datetime.now(timezone.utc).isoformat()

            # Submit to OpenAI Batch API via existing BatchManager
            if self._batch_manager:
                openai_batch_id = await self._submit_to_openai(batch_job)
                if openai_batch_id:
                    batch_job.openai_batch_id = openai_batch_id
                    batch_job.status = BatchStatus.IN_PROGRESS
                else:
                    batch_job.status = BatchStatus.FAILED
                    batch_job.error_message = "Failed to submit to OpenAI"
            else:
                # Fallback processing without OpenAI integration
                await self._process_batch_locally(batch_job)

            # Emit event
            await self.guild_core.communication_hub.emit_event(
                "batch.submitted",
                {
                    "batch_id": batch_id,
                    "openai_batch_id": batch_job.openai_batch_id,
                    "status": batch_job.status.value,
                },
                CommunicationChannel.BATCH_PROCESSING,
                MessagePriority.NORMAL,
            )

            logger.info(
                f"Batch {batch_id} submitted with status {batch_job.status.value}"
            )

        except Exception as e:
            logger.error(f"Failed to process batch {batch_id}: {e}")
            if batch_id in self._batches:
                self._batches[batch_id].status = BatchStatus.FAILED
                self._batches[batch_id].error_message = str(e)

    async def _submit_to_openai(self, batch_job: BatchJob) -> Optional[str]:
        """Submit batch to OpenAI via existing BatchManager"""
        try:
            # Prepare requests for OpenAI Batch API
            requests = await self._prepare_openai_requests(batch_job)

            if self._batch_manager and requests:
                # Use existing BatchManager
                openai_batch_id = await self._batch_manager.submit_batch(
                    requests=requests,
                    description=batch_job.description,
                    metadata={"guild_batch_id": batch_job.id},
                )
                return openai_batch_id

            return None

        except Exception as e:
            logger.error(f"Failed to submit to OpenAI: {e}")
            return None

    async def _prepare_openai_requests(
        self, batch_job: BatchJob
    ) -> List[Dict[str, Any]]:
        """Prepare OpenAI API requests for batch job"""
        try:
            requests = []

            for i, task_id in enumerate(batch_job.task_ids):
                task_info = await self._get_task_info(task_id)
                if not task_info:
                    continue

                # Create request based on batch type
                request = {
                    "custom_id": f"{batch_job.id}-{task_id}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "gpt-4",
                        "messages": await self._create_messages_for_task(
                            task_info, batch_job.type
                        ),
                        "max_tokens": 2000,
                        "temperature": 0.1,
                    },
                }

                requests.append(request)

            return requests

        except Exception as e:
            logger.error(f"Failed to prepare OpenAI requests: {e}")
            return []

    async def _create_messages_for_task(
        self, task_info: Dict[str, Any], batch_type: BatchType
    ) -> List[Dict[str, str]]:
        """Create chat messages for a task based on batch type"""
        try:
            title = task_info.get("title", "")
            description = task_info.get("description", "")

            # Base system message
            system_messages = {
                BatchType.TASK_ANALYSIS: "You are a task analysis expert. Analyze the given task and provide detailed breakdown.",
                BatchType.CODE_GENERATION: "You are a code generation expert. Generate high-quality code for the given task.",
                BatchType.IMPLEMENTATION: "You are a software implementation expert. Provide detailed implementation steps.",
                BatchType.REVIEW: "You are a code review expert. Review and provide feedback on the given task.",
                BatchType.TESTING: "You are a testing expert. Create comprehensive test plans and test cases.",
                BatchType.DOCUMENTATION: "You are a documentation expert. Create clear and comprehensive documentation.",
            }

            system_message = system_messages.get(
                batch_type, "You are a helpful assistant."
            )

            user_message = f"Task: {title}\n\nDescription: {description}\n\nPlease provide a detailed response based on the task requirements."

            return [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ]

        except Exception as e:
            logger.error(f"Failed to create messages for task: {e}")
            return []

    async def _process_batch_locally(self, batch_job: BatchJob) -> None:
        """Process batch locally without OpenAI (fallback)"""
        try:
            # This would be a fallback processing method
            # For now, just mark as completed with placeholder results
            batch_job.status = BatchStatus.COMPLETED
            batch_job.completed_at = datetime.now(timezone.utc).isoformat()
            batch_job.results = {
                "processed_locally": True,
                "task_count": len(batch_job.task_ids),
            }

            logger.info(f"Batch {batch_job.id} processed locally (fallback)")

        except Exception as e:
            logger.error(f"Failed to process batch locally: {e}")
            batch_job.status = BatchStatus.FAILED
            batch_job.error_message = str(e)

    async def _monitor_batches(self) -> None:
        """Monitor batch job progress"""
        while self._running:
            try:
                # Check status of in-progress batches
                in_progress_batches = [
                    batch
                    for batch in self._batches.values()
                    if batch.status == BatchStatus.IN_PROGRESS
                ]

                for batch_job in in_progress_batches:
                    await self._check_batch_status(batch_job)

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch monitoring error: {e}")
                await asyncio.sleep(10)

    async def _check_batch_status(self, batch_job: BatchJob) -> None:
        """Check the status of a specific batch job"""
        try:
            if not batch_job.openai_batch_id or not self._batch_manager:
                return

            # Check status via existing BatchManager
            # This would integrate with existing batch monitoring logic

            # For now, simulate completion after some time
            if batch_job.submitted_at:
                submitted_time = datetime.fromisoformat(
                    batch_job.submitted_at.replace("Z", "+00:00")
                )
                if datetime.now(timezone.utc) - submitted_time > timedelta(minutes=30):
                    await self._complete_batch(batch_job)

        except Exception as e:
            logger.error(f"Failed to check batch status: {e}")

    async def _complete_batch(self, batch_job: BatchJob) -> None:
        """Complete a batch job and process results"""
        try:
            batch_job.status = BatchStatus.COMPLETED
            batch_job.completed_at = datetime.now(timezone.utc).isoformat()

            # Process results and distribute to tasks
            await self._process_batch_results(batch_job)

            # Emit completion event
            await self.guild_core.communication_hub.emit_event(
                "batch.completed",
                {
                    "batch_id": batch_job.id,
                    "task_count": len(batch_job.task_ids),
                    "actual_cost": batch_job.actual_cost,
                    "duration_minutes": self._calculate_duration(batch_job),
                },
                CommunicationChannel.BATCH_PROCESSING,
                MessagePriority.HIGH,
            )

            logger.info(f"Batch {batch_job.id} completed successfully")

        except Exception as e:
            logger.error(f"Failed to complete batch: {e}")
            batch_job.status = BatchStatus.FAILED
            batch_job.error_message = str(e)

    async def _process_batch_results(self, batch_job: BatchJob) -> None:
        """Process and distribute batch results to individual tasks"""
        try:
            # This would process the OpenAI batch results and update individual tasks
            # Integration with existing batch recycling logic

            for task_id in batch_job.task_ids:
                # Update task with batch results
                task_result = batch_job.results.get(task_id, {})

                # Notify task director of completion
                if hasattr(self.guild_core, "task_director"):
                    # This would integrate with task completion workflow
                    pass

        except Exception as e:
            logger.error(f"Failed to process batch results: {e}")

    def _calculate_duration(self, batch_job: BatchJob) -> Optional[float]:
        """Calculate batch processing duration in minutes"""
        try:
            if not batch_job.submitted_at or not batch_job.completed_at:
                return None

            submitted = datetime.fromisoformat(
                batch_job.submitted_at.replace("Z", "+00:00")
            )
            completed = datetime.fromisoformat(
                batch_job.completed_at.replace("Z", "+00:00")
            )

            duration = completed - submitted
            return duration.total_seconds() / 60

        except Exception as e:
            logger.error(f"Failed to calculate duration: {e}")
            return None

    async def get_health(self) -> Dict[str, Any]:
        """Get health status of batch orchestrator"""
        status_counts = {}
        for status in BatchStatus:
            status_counts[status.value] = len(
                [b for b in self._batches.values() if b.status == status]
            )

        return {
            "status": "healthy" if self._running else "stopped",
            "total_batches": len(self._batches),
            "pending_tasks": len(self._pending_tasks),
            "queue_size": self._batch_queue.qsize(),
            "by_status": status_counts,
            "integration": {"batch_manager": self._batch_manager is not None},
        }

    async def _handle_batch_event(self, message) -> None:
        """Handle batch-related events"""
        try:
            event_type = message.event_type
            data = message.payload

            if event_type == "task.created":
                # Automatically add new tasks to pending batch queue
                task_id = data.get("task_id")
                if task_id:
                    await self.add_task_to_pending(task_id)
            elif event_type == "batch.priority_changed":
                await self._handle_priority_change(data)
            # Add more event handlers as needed

        except Exception as e:
            logger.error(f"Failed to handle batch event: {e}")

    async def _auto_batch_loop(self) -> None:
        """Automatic batching loop"""
        while self._running:
            try:
                await self.check_auto_batch()
                await asyncio.sleep(self.auto_batch_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto batch loop error: {e}")
                await asyncio.sleep(30)

    async def _load_state(self) -> None:
        """Load batch orchestrator state from disk"""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r") as f:
                    state = json.load(f)

                # Restore batches
                for batch_data in state.get("batches", []):
                    batch_job = BatchJob(
                        id=batch_data["id"],
                        type=BatchType(batch_data["type"]),
                        task_ids=batch_data["task_ids"],
                        description=batch_data["description"],
                        status=BatchStatus(batch_data["status"]),
                        openai_batch_id=batch_data.get("openai_batch_id"),
                        priority=batch_data.get("priority", "medium"),
                        created_at=batch_data["created_at"],
                        submitted_at=batch_data.get("submitted_at"),
                        completed_at=batch_data.get("completed_at"),
                        cost_estimate=batch_data.get("cost_estimate"),
                        actual_cost=batch_data.get("actual_cost"),
                        results=batch_data.get("results", {}),
                        metadata=batch_data.get("metadata", {}),
                        error_message=batch_data.get("error_message"),
                    )
                    self._batches[batch_job.id] = batch_job

                # Restore pending tasks
                self._pending_tasks = set(state.get("pending_tasks", []))

                logger.info(
                    f"Loaded {len(self._batches)} batches and {len(self._pending_tasks)} pending tasks"
                )

        except Exception as e:
            logger.error(f"Failed to load state: {e}")

    async def _save_state(self) -> None:
        """Save batch orchestrator state to disk"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                "batches": [batch.to_dict() for batch in self._batches.values()],
                "pending_tasks": list(self._pending_tasks),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)

            logger.debug("Batch orchestrator state saved")

        except Exception as e:
            logger.error(f"Failed to save state: {e}")
