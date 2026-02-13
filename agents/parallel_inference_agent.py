"""
Parallel Inference Agent - Specialized agent for multi-model inference tasks
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger
from datetime import datetime, timezone

from ..communication_hub import CommunicationChannel, MessagePriority
from ..model_manager import ModelCapability


@dataclass
class InferenceRequest:
    """Request for parallel inference"""

    id: str
    prompt: str
    task_id: Optional[str] = None
    model_requirements: List[str] = None
    parallel_count: int = 3
    consensus_required: bool = True
    preferred_models: List[str] = None
    options: Dict[str, Any] = None
    requester: str = "unknown"
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.model_requirements is None:
            self.model_requirements = ["text_generation"]
        if self.options is None:
            self.options = {}


class ParallelInferenceAgent:
    """
    Specialized agent for handling parallel inference tasks across multiple local models.

    Features:
    - Intelligent model selection based on task requirements
    - Parallel execution across multiple models
    - Consensus generation from multiple responses
    - Task-specific model optimization
    - Integration with Guild task system
    """

    def __init__(self, guild_core):
        self.guild_core = guild_core
        self.agent_id = "parallel_inference_agent"
        self._running = False

        # Request handling
        self._active_requests: Dict[str, InferenceRequest] = {}
        self._request_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None

        # Performance tracking
        self._completed_requests = 0
        self._total_inference_time = 0.0
        self._model_performance: Dict[str, Dict[str, float]] = {}

        logger.info("Parallel Inference Agent initialized")

    async def start(self) -> None:
        """Start the parallel inference agent"""
        if self._running:
            return

        self._running = True

        # Register with agent coordinator
        await self.guild_core.agent_coordinator.register_agent(
            agent_id=self.agent_id,
            name="Parallel Inference Agent",
            capabilities=[
                "parallel_inference",
                "consensus_generation",
                "model_optimization",
                "text_generation",
                "code_generation",
            ],
            max_concurrent_tasks=10,
            metadata={
                "type": "inference_agent",
                "specialization": "parallel_multi_model_inference",
            },
        )

        # Subscribe to relevant events
        self.guild_core.communication_hub.subscribe(
            CommunicationChannel.TASK_UPDATES, self._handle_task_event
        )

        self.guild_core.communication_hub.subscribe(
            CommunicationChannel.AGENT_COORDINATION, self._handle_coordination_event
        )

        # Start request processor
        self._processor_task = asyncio.create_task(self._process_requests())

        logger.info("Parallel Inference Agent started")

    async def stop(self) -> None:
        """Stop the parallel inference agent"""
        if not self._running:
            return

        self._running = False

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        # Unregister from agent coordinator
        await self.guild_core.agent_coordinator.unregister_agent(self.agent_id)

        logger.info("Parallel Inference Agent stopped")

    async def submit_inference_request(
        self,
        prompt: str,
        task_id: Optional[str] = None,
        model_requirements: List[str] = None,
        parallel_count: int = 3,
        consensus_required: bool = True,
        preferred_models: List[str] = None,
        requester: str = "unknown",
        **options,
    ) -> str:
        """Submit a parallel inference request"""
        try:
            import uuid

            request_id = f"inf-{uuid.uuid4().hex[:8]}"

            request = InferenceRequest(
                id=request_id,
                prompt=prompt,
                task_id=task_id,
                model_requirements=model_requirements or ["text_generation"],
                parallel_count=parallel_count,
                consensus_required=consensus_required,
                preferred_models=preferred_models or [],
                options=options,
                requester=requester,
            )

            self._active_requests[request_id] = request
            await self._request_queue.put(request_id)

            # Emit event
            await self.guild_core.communication_hub.emit_event(
                "inference.request_submitted",
                {
                    "request_id": request_id,
                    "task_id": task_id,
                    "parallel_count": parallel_count,
                    "consensus_required": consensus_required,
                    "requester": requester,
                },
                CommunicationChannel.AGENT_COORDINATION,
                MessagePriority.NORMAL,
            )

            logger.info(f"Inference request {request_id} submitted by {requester}")
            return request_id

        except Exception as e:
            logger.error(f"Failed to submit inference request: {e}")
            return ""

    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an inference request"""
        if request_id not in self._active_requests:
            return None

        request = self._active_requests[request_id]

        # Check if model manager has results
        if self.guild_core.model_manager:
            # The request might have been processed by model manager
            # Check for corresponding parallel task
            parallel_tasks = self.guild_core.model_manager.get_parallel_tasks()

            for task_id, task_data in parallel_tasks.items():
                if (
                    task_data.get("metadata", {}).get("inference_request_id")
                    == request_id
                ):
                    return {
                        "request_id": request_id,
                        "status": (
                            "completed"
                            if task_data.get("completed_at")
                            else "processing"
                        ),
                        "parallel_task_id": task_id,
                        "results": task_data.get("results", []),
                        "consensus": task_data.get("consensus_result"),
                    }

        return {
            "request_id": request_id,
            "status": "queued",
            "created_at": request.created_at,
            "requester": request.requester,
        }

    async def _process_requests(self) -> None:
        """Process inference requests from the queue"""
        while self._running:
            try:
                # Get request with timeout
                request_id = await asyncio.wait_for(
                    self._request_queue.get(), timeout=1.0
                )
                await self._process_single_request(request_id)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in request processor: {e}")

    async def _process_single_request(self, request_id: str) -> None:
        """Process a single inference request"""
        try:
            if request_id not in self._active_requests:
                return

            request = self._active_requests[request_id]

            # Check if model manager is available
            if not self.guild_core.model_manager:
                logger.error("Model manager not available for inference request")
                return

            # Optimize model selection based on request
            optimized_models = await self._optimize_model_selection(request)

            # Submit to model manager with optimization
            start_time = datetime.now(timezone.utc)

            parallel_task_id = await self.guild_core.model_manager.submit_parallel_task(
                prompt=request.prompt,
                model_requirements=request.model_requirements,
                parallel_count=request.parallel_count,
                consensus_required=request.consensus_required,
                preferred_models=optimized_models,
                metadata={
                    "inference_request_id": request_id,
                    "task_id": request.task_id,
                    "requester": request.requester,
                    "agent_id": self.agent_id,
                },
                **request.options,
            )

            if parallel_task_id:
                # Monitor the parallel task
                await self._monitor_parallel_task(
                    request_id, parallel_task_id, start_time
                )
            else:
                logger.error(f"Failed to submit parallel task for request {request_id}")

        except Exception as e:
            logger.error(f"Failed to process inference request {request_id}: {e}")

    async def _optimize_model_selection(self, request: InferenceRequest) -> List[str]:
        """Optimize model selection based on request characteristics and performance history"""
        try:
            available_models = self.guild_core.model_manager.get_available_models()

            # Filter models by capabilities
            suitable_models = []
            required_caps = [ModelCapability(cap) for cap in request.model_requirements]

            for model_id, model_data in available_models.items():
                model_caps = [
                    ModelCapability(cap) for cap in model_data.get("capabilities", [])
                ]
                if all(cap in model_caps for cap in required_caps):
                    suitable_models.append(model_id)

            # Apply performance-based optimization
            optimized_models = self._rank_models_by_performance(
                suitable_models, request
            )

            # Combine with preferred models
            final_selection = []

            # Add preferred models first (if they're suitable)
            for preferred in request.preferred_models:
                if preferred in suitable_models and preferred not in final_selection:
                    final_selection.append(preferred)

            # Add optimized models
            for model in optimized_models:
                if model not in final_selection:
                    final_selection.append(model)
                if (
                    len(final_selection) >= request.parallel_count * 2
                ):  # Give some options
                    break

            logger.debug(
                f"Optimized model selection for request {request.id}: {final_selection}"
            )
            return final_selection

        except Exception as e:
            logger.error(f"Failed to optimize model selection: {e}")
            return request.preferred_models or []

    def _rank_models_by_performance(
        self, models: List[str], request: InferenceRequest
    ) -> List[str]:
        """Rank models by historical performance for similar requests"""
        try:
            # Simple ranking based on performance metrics
            model_scores = []

            for model_id in models:
                score = 0.0

                if model_id in self._model_performance:
                    perf = self._model_performance[model_id]

                    # Factor in response time (lower is better)
                    avg_time = perf.get("avg_response_time", 10.0)
                    time_score = max(0, 10 - avg_time)  # 10 second baseline

                    # Factor in success rate
                    success_rate = perf.get("success_rate", 0.5)
                    success_score = success_rate * 10

                    # Factor in quality score (if available)
                    quality_score = perf.get("quality_score", 5.0)

                    score = time_score * 0.3 + success_score * 0.5 + quality_score * 0.2
                else:
                    # Default score for unknown models
                    score = 5.0

                model_scores.append((model_id, score))

            # Sort by score (descending)
            model_scores.sort(key=lambda x: x[1], reverse=True)

            return [model_id for model_id, _ in model_scores]

        except Exception as e:
            logger.error(f"Failed to rank models by performance: {e}")
            return models

    async def _monitor_parallel_task(
        self, request_id: str, parallel_task_id: str, start_time: datetime
    ) -> None:
        """Monitor a parallel task and update performance metrics"""
        try:
            # Wait for task completion (with timeout)
            timeout_seconds = 300  # 5 minutes
            check_interval = 5  # Check every 5 seconds
            elapsed = 0

            while elapsed < timeout_seconds:
                result = await self.guild_core.model_manager.get_task_result(
                    parallel_task_id
                )

                if result and (result.get("consensus") or result.get("results")):
                    # Task completed
                    end_time = datetime.now(timezone.utc)
                    total_time = (end_time - start_time).total_seconds()

                    # Update performance metrics
                    await self._update_performance_metrics(
                        parallel_task_id, result, total_time
                    )

                    # Update counters
                    self._completed_requests += 1
                    self._total_inference_time += total_time

                    # Emit completion event
                    await self.guild_core.communication_hub.emit_event(
                        "inference.request_completed",
                        {
                            "request_id": request_id,
                            "parallel_task_id": parallel_task_id,
                            "execution_time": total_time,
                            "results_count": len(result.get("results", [])),
                            "consensus_generated": result.get("consensus") is not None,
                        },
                        CommunicationChannel.AGENT_COORDINATION,
                        MessagePriority.HIGH,
                    )

                    logger.info(
                        f"Inference request {request_id} completed in {total_time:.2f}s"
                    )
                    break

                await asyncio.sleep(check_interval)
                elapsed += check_interval

            if elapsed >= timeout_seconds:
                logger.warning(
                    f"Inference request {request_id} timed out after {timeout_seconds}s"
                )

        except Exception as e:
            logger.error(f"Failed to monitor parallel task {parallel_task_id}: {e}")

    async def _update_performance_metrics(
        self, parallel_task_id: str, result: Dict[str, Any], total_time: float
    ) -> None:
        """Update performance metrics for models used in the task"""
        try:
            results = result.get("results", [])

            for model_result in results:
                model_id = model_result.get("model_id")
                if not model_id:
                    continue

                if model_id not in self._model_performance:
                    self._model_performance[model_id] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "total_time": 0.0,
                        "avg_response_time": 0.0,
                        "success_rate": 0.0,
                        "quality_score": 5.0,
                    }

                perf = self._model_performance[model_id]
                perf["total_requests"] += 1

                # Check if this result was successful
                if "result" in model_result and model_result["result"]:
                    perf["successful_requests"] += 1

                # Update timing
                execution_time = model_result.get("execution_time", total_time)
                perf["total_time"] += execution_time
                perf["avg_response_time"] = perf["total_time"] / perf["total_requests"]

                # Update success rate
                perf["success_rate"] = (
                    perf["successful_requests"] / perf["total_requests"]
                )

                # Update quality score (simplified - could be more sophisticated)
                if "result" in model_result:
                    # Simple quality heuristic based on response length and structure
                    response_text = ""
                    if "choices" in model_result["result"]:
                        choices = model_result["result"]["choices"]
                        if choices and "message" in choices[0]:
                            response_text = choices[0]["message"].get("content", "")

                    if response_text:
                        # Simple quality score based on response characteristics
                        quality = min(
                            10.0, len(response_text) / 100
                        )  # Longer responses get higher scores
                        perf["quality_score"] = (
                            perf["quality_score"] * 0.9 + quality * 0.1
                        )

        except Exception as e:
            logger.error(f"Failed to update performance metrics: {e}")

    async def _handle_task_event(self, message) -> None:
        """Handle task-related events"""
        try:
            event_type = message.event_type
            data = message.payload

            if event_type == "task.claimed":
                # Check if this is an inference-related task
                task_id = data.get("task_id")
                if task_id and "inference" in data.get("title", "").lower():
                    # This might be a task that could benefit from parallel inference
                    await self._suggest_parallel_inference(task_id, data)

        except Exception as e:
            logger.error(f"Failed to handle task event: {e}")

    async def _handle_coordination_event(self, message) -> None:
        """Handle agent coordination events"""
        try:
            event_type = message.event_type
            data = message.payload

            if event_type == "cooperation.request":
                request_type = data.get("request_type")

                if request_type == "parallel_inference":
                    # Handle direct parallel inference requests
                    await self._handle_parallel_inference_cooperation(data)
                elif request_type == "model_recommendation":
                    # Provide model recommendations
                    await self._handle_model_recommendation_request(data)

        except Exception as e:
            logger.error(f"Failed to handle coordination event: {e}")

    async def _suggest_parallel_inference(
        self, task_id: str, task_data: Dict[str, Any]
    ) -> None:
        """Suggest parallel inference for a task that might benefit from it"""
        try:
            # Analyze task to see if it would benefit from parallel inference
            title = task_data.get("title", "").lower()
            description = task_data.get("description", "").lower()

            # Keywords that suggest parallel inference would be beneficial
            inference_keywords = [
                "generate",
                "create",
                "write",
                "analyze",
                "review",
                "compare",
                "evaluate",
                "brainstorm",
                "ideate",
            ]

            if any(
                keyword in title or keyword in description
                for keyword in inference_keywords
            ):
                # Suggest parallel inference to the task assignee
                await self.guild_core.communication_hub.emit_event(
                    "inference.suggestion",
                    {
                        "task_id": task_id,
                        "suggestion": "parallel_inference",
                        "reason": "Task appears to benefit from multi-model consensus",
                        "agent_id": self.agent_id,
                    },
                    CommunicationChannel.AGENT_COORDINATION,
                    MessagePriority.LOW,
                )

                logger.debug(f"Suggested parallel inference for task {task_id}")

        except Exception as e:
            logger.error(f"Failed to suggest parallel inference: {e}")

    async def _handle_parallel_inference_cooperation(
        self, data: Dict[str, Any]
    ) -> None:
        """Handle cooperation request for parallel inference"""
        try:
            requesting_agent = data.get("requesting_agent")
            payload = data.get("payload", {})

            prompt = payload.get("prompt")
            if not prompt:
                logger.warning("Parallel inference request missing prompt")
                return

            # Submit inference request
            request_id = await self.submit_inference_request(
                prompt=prompt,
                task_id=payload.get("task_id"),
                model_requirements=payload.get(
                    "model_requirements", ["text_generation"]
                ),
                parallel_count=payload.get("parallel_count", 3),
                consensus_required=payload.get("consensus_required", True),
                preferred_models=payload.get("preferred_models", []),
                requester=requesting_agent,
                **payload.get("options", {}),
            )

            # Respond with request ID
            await self.guild_core.agent_coordinator.respond_to_cooperation(
                request_id=data.get("request_id", ""),
                responding_agent=self.agent_id,
                response={
                    "inference_request_id": request_id,
                    "status": "submitted",
                    "message": "Parallel inference request submitted successfully",
                },
            )

        except Exception as e:
            logger.error(f"Failed to handle parallel inference cooperation: {e}")

    async def _handle_model_recommendation_request(self, data: Dict[str, Any]) -> None:
        """Handle request for model recommendations"""
        try:
            payload = data.get("payload", {})
            requirements = payload.get("requirements", [])
            task_type = payload.get("task_type", "general")

            # Get available models
            available_models = self.guild_core.model_manager.get_available_models()

            # Filter and rank models
            suitable_models = []
            for model_id, model_data in available_models.items():
                model_caps = model_data.get("capabilities", [])
                if not requirements or any(req in model_caps for req in requirements):
                    suitable_models.append(
                        {
                            "model_id": model_id,
                            "name": model_data.get("name", model_id),
                            "capabilities": model_caps,
                            "parameters": model_data.get("parameters", "unknown"),
                            "performance": self._model_performance.get(model_id, {}),
                        }
                    )

            # Respond with recommendations
            await self.guild_core.agent_coordinator.respond_to_cooperation(
                request_id=data.get("request_id", ""),
                responding_agent=self.agent_id,
                response={
                    "recommendations": suitable_models[:5],  # Top 5 recommendations
                    "total_available": len(available_models),
                    "suitable_count": len(suitable_models),
                },
            )

        except Exception as e:
            logger.error(f"Failed to handle model recommendation request: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for the agent"""
        avg_inference_time = (
            self._total_inference_time / self._completed_requests
            if self._completed_requests > 0
            else 0.0
        )

        return {
            "agent_id": self.agent_id,
            "completed_requests": self._completed_requests,
            "total_inference_time": self._total_inference_time,
            "avg_inference_time": avg_inference_time,
            "active_requests": len(self._active_requests),
            "model_performance": dict(self._model_performance),
            "status": "running" if self._running else "stopped",
        }
