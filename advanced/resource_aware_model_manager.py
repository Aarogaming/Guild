"""
Resource-Aware Model Manager - Intelligent local/remote model selection

This extends the Guild Model Manager with resource-aware capabilities that:
- Prefer local models when system resources are available
- Automatically fall back to remote/cloud models when resources are constrained
- Monitor system resources in real-time
- Dynamically adjust model selection based on resource thresholds
- Provide cost optimization through intelligent routing
"""

import asyncio
import os
import psutil
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
from datetime import datetime, timezone
import json

try:
    import GPUtil

    GPU_MONITORING_AVAILABLE = True
except ImportError:
    GPU_MONITORING_AVAILABLE = False

from ..model_manager import ModelManager, ParallelTask, ModelSpec, ModelInstance


class ResourceThreshold(Enum):
    """Resource threshold levels"""

    LOW = "low"  # < 50% usage
    MODERATE = "moderate"  # 50-70% usage
    HIGH = "high"  # 70-85% usage
    CRITICAL = "critical"  # > 85% usage


class ModelRoutingStrategy(Enum):
    """Model routing strategies based on resources"""

    LOCAL_ONLY = "local_only"  # Only use local models
    LOCAL_PREFERRED = "local_preferred"  # Prefer local, fallback to remote
    BALANCED = "balanced"  # Balance local and remote
    REMOTE_PREFERRED = "remote_preferred"  # Prefer remote, fallback to local
    REMOTE_ONLY = "remote_only"  # Only use remote models
    COST_OPTIMIZED = "cost_optimized"  # Optimize for cost


@dataclass
class ResourceMetrics:
    """Current system resource metrics"""

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    gpu_percent: float = 0.0
    gpu_memory_percent: float = 0.0
    network_io: Dict[str, float] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def get_overall_load(self) -> float:
        """Calculate overall system load"""
        weights = {"cpu": 0.3, "memory": 0.4, "gpu": 0.2, "disk": 0.1}

        return (
            self.cpu_percent * weights["cpu"]
            + self.memory_percent * weights["memory"]
            + self.gpu_percent * weights["gpu"]
            + self.disk_percent * weights["disk"]
        ) / 100.0

    def get_threshold_level(self) -> ResourceThreshold:
        """Get current resource threshold level"""
        overall_load = self.get_overall_load() * 100

        if overall_load < 50:
            return ResourceThreshold.LOW
        elif overall_load < 70:
            return ResourceThreshold.MODERATE
        elif overall_load < 85:
            return ResourceThreshold.HIGH
        else:
            return ResourceThreshold.CRITICAL


@dataclass
class RemoteModelEndpoint:
    """Configuration for remote model endpoints"""

    id: str
    name: str
    endpoint_url: str
    provider: str = "openai"
    api_key: Optional[str] = None
    model_name: str = ""
    cost_per_token: float = 0.0
    max_tokens: int = 4096
    capabilities: List[str] = field(default_factory=list)
    latency_ms: float = 100.0
    reliability_score: float = 0.95

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "endpoint_url": self.endpoint_url,
            "provider": self.provider,
            "model_name": self.model_name,
            "cost_per_token": self.cost_per_token,
            "max_tokens": self.max_tokens,
            "capabilities": self.capabilities,
            "latency_ms": self.latency_ms,
            "reliability_score": self.reliability_score,
        }


class ResourceAwareModelManager(ModelManager):
    """
    Enhanced Model Manager with resource-aware local/remote model selection.

    Features:
    - Real-time resource monitoring
    - Dynamic model routing based on system load
    - Cost optimization through intelligent selection
    - Automatic fallback mechanisms
    - Performance tracking and optimization
    """

    def __init__(self, config, guild_core):
        super().__init__(config, guild_core)

        # Resource monitoring
        self.resource_thresholds = {
            ResourceThreshold.LOW: {
                "cpu_max": 50.0,
                "memory_max": 50.0,
                "gpu_max": 50.0,
                "strategy": ModelRoutingStrategy.LOCAL_PREFERRED,
            },
            ResourceThreshold.MODERATE: {
                "cpu_max": 70.0,
                "memory_max": 70.0,
                "gpu_max": 70.0,
                "strategy": ModelRoutingStrategy.BALANCED,
            },
            ResourceThreshold.HIGH: {
                "cpu_max": 85.0,
                "memory_max": 85.0,
                "gpu_max": 85.0,
                "strategy": ModelRoutingStrategy.REMOTE_PREFERRED,
            },
            ResourceThreshold.CRITICAL: {
                "cpu_max": 100.0,
                "memory_max": 100.0,
                "gpu_max": 100.0,
                "strategy": ModelRoutingStrategy.REMOTE_ONLY,
            },
        }

        # Remote model endpoints
        self.remote_endpoints: Dict[str, RemoteModelEndpoint] = {}
        self.current_metrics: Optional[ResourceMetrics] = None
        self.current_strategy: ModelRoutingStrategy = (
            ModelRoutingStrategy.LOCAL_PREFERRED
        )

        # Performance tracking
        self.routing_decisions: List[Dict[str, Any]] = []
        self.cost_tracking: Dict[str, float] = {"local": 0.0, "remote": 0.0}

        # Configuration
        self.enable_resource_awareness = True
        self.resource_check_interval = 10  # seconds
        self.fallback_timeout = 30  # seconds
        self.cost_optimization_enabled = True

        # Background tasks
        self.resource_monitor_task: Optional[asyncio.Task] = None

        logger.info("Resource-Aware Model Manager initialized")

    async def start(self) -> None:
        """Start the resource-aware model manager"""
        await super().start()

        # Initialize remote endpoints
        await self._initialize_remote_endpoints()

        # Start resource monitoring
        if self.enable_resource_awareness:
            self.resource_monitor_task = asyncio.create_task(
                self._resource_awareness_loop()
            )

        logger.info("Resource-aware model management started")

    async def stop(self) -> None:
        """Stop the resource-aware model manager"""
        if self.resource_monitor_task:
            self.resource_monitor_task.cancel()
            try:
                await self.resource_monitor_task
            except asyncio.CancelledError:
                pass

        await super().stop()

    async def _initialize_remote_endpoints(self):
        """Initialize remote model endpoints"""
        openai_key = (
            getattr(self.config, "openai_api_key", "")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENAI_PROJECT_API_KEY")
        )
        anthropic_key = getattr(self.config, "anthropic_api_key", "") or os.getenv(
            "ANTHROPIC_API_KEY"
        )
        gemini_key = (
            getattr(self.config, "google_api_key", "")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )

        # Example remote endpoints (would be configured via settings)
        remote_configs = [
            {
                "id": "openai_gpt4",
                "name": "OpenAI GPT-4",
                "endpoint_url": "https://api.openai.com/v1/chat/completions",
                "provider": "openai",
                "api_key": openai_key or None,
                "model_name": "gpt-4",
                "cost_per_token": 0.00003,  # $0.03 per 1K tokens
                "capabilities": ["text_generation", "reasoning", "coding", "analysis"],
            },
            {
                "id": "anthropic_claude",
                "name": "Anthropic Claude",
                "endpoint_url": "https://api.anthropic.com/v1/messages",
                "provider": "anthropic",
                "api_key": anthropic_key or None,
                "model_name": "claude-3-sonnet-20240229",
                "cost_per_token": 0.000015,  # $0.015 per 1K tokens
                "capabilities": [
                    "text_generation",
                    "reasoning",
                    "analysis",
                    "creative_writing",
                ],
            },
            {
                "id": "google_gemini",
                "name": "Google Gemini Pro",
                "endpoint_url": "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent",
                "provider": "gemini",
                "api_key": gemini_key or None,
                "model_name": "gemini-pro",
                "cost_per_token": 0.0000005,  # $0.0005 per 1K tokens
                "capabilities": ["text_generation", "reasoning", "multimodal"],
            },
        ]

        for config in remote_configs:
            endpoint = RemoteModelEndpoint(**config)
            self.remote_endpoints[endpoint.id] = endpoint

        logger.info(f"Initialized {len(self.remote_endpoints)} remote model endpoints")

    async def _resource_awareness_loop(self):
        """Monitor system resources and adjust strategy"""
        while self._running:
            try:
                # Collect resource metrics
                self.current_metrics = await self._collect_resource_metrics()

                # Determine optimal routing strategy
                new_strategy = await self._determine_routing_strategy(
                    self.current_metrics
                )

                if new_strategy != self.current_strategy:
                    logger.info(
                        f"Routing strategy changed: {self.current_strategy.value} → {new_strategy.value}"
                    )
                    self.current_strategy = new_strategy

                    # Emit strategy change event
                    await self.guild_core.communication_hub.emit_event(
                        "model_routing.strategy_changed",
                        {
                            "old_strategy": self.current_strategy.value,
                            "new_strategy": new_strategy.value,
                            "resource_level": self.current_metrics.get_threshold_level().value,
                            "overall_load": self.current_metrics.get_overall_load(),
                        },
                    )

                await asyncio.sleep(self.resource_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource awareness loop error: {e}")
                await asyncio.sleep(30)

    async def _collect_resource_metrics(self) -> ResourceMetrics:
        """Collect current system resource metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # GPU metrics if available
            gpu_percent = 0.0
            gpu_memory_percent = 0.0

            if GPU_MONITORING_AVAILABLE:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu_percent = max(gpu.load * 100 for gpu in gpus)
                        gpu_memory_percent = max(gpu.memoryUtil * 100 for gpu in gpus)
                except Exception:
                    pass

            # Network I/O
            network_io = {}
            try:
                net_io = psutil.net_io_counters()
                network_io = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                }
            except Exception:
                pass

            return ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                gpu_percent=gpu_percent,
                gpu_memory_percent=gpu_memory_percent,
                network_io=network_io,
            )

        except Exception as e:
            logger.error(f"Failed to collect resource metrics: {e}")
            # Return safe defaults
            return ResourceMetrics(
                cpu_percent=50.0, memory_percent=50.0, disk_percent=50.0
            )

    async def _determine_routing_strategy(
        self, metrics: ResourceMetrics
    ) -> ModelRoutingStrategy:
        """Determine optimal routing strategy based on resource metrics"""
        forced = os.getenv("AAS_ROUTING_STRATEGY") or os.getenv(
            "AAS_MODEL_ROUTING_STRATEGY"
        )
        if forced:
            forced_value = forced.strip().lower()
            for strategy in ModelRoutingStrategy:
                if strategy.value == forced_value:
                    return strategy
            logger.warning(f"Unknown AAS_ROUTING_STRATEGY: {forced}")

        threshold_level = metrics.get_threshold_level()

        # Get strategy from threshold configuration
        base_strategy = self.resource_thresholds[threshold_level]["strategy"]

        # Apply cost optimization if enabled
        if self.cost_optimization_enabled:
            base_strategy = await self._apply_cost_optimization(base_strategy, metrics)

        return base_strategy

    async def _apply_cost_optimization(
        self, base_strategy: ModelRoutingStrategy, metrics: ResourceMetrics
    ) -> ModelRoutingStrategy:
        """Apply cost optimization to routing strategy"""
        # If resources are low and we have local models available, prefer local
        if (
            metrics.get_threshold_level() == ResourceThreshold.LOW
            and len(self._loaded_models) > 0
        ):
            return ModelRoutingStrategy.LOCAL_PREFERRED

        # If resources are moderate, balance based on cost efficiency
        if metrics.get_threshold_level() == ResourceThreshold.MODERATE:
            local_cost = self.cost_tracking.get("local", 0.0)
            remote_cost = self.cost_tracking.get("remote", 0.0)

            # If remote costs are getting high, prefer local
            if remote_cost > local_cost * 2:
                return ModelRoutingStrategy.LOCAL_PREFERRED

        return base_strategy

    async def submit_parallel_task(
        self,
        prompt: str,
        model_requirements: List[str] = None,
        parallel_count: int = 3,
        consensus_required: bool = True,
        preferred_models: List[str] = None,
        **kwargs,
    ) -> str:
        """Submit parallel task with resource-aware model selection"""

        # Select models based on current routing strategy
        selected_models = await self._select_resource_aware_models(
            model_requirements or [], parallel_count, preferred_models or []
        )

        # Track routing decision
        routing_decision = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy": self.current_strategy.value,
            "resource_level": (
                self.current_metrics.get_threshold_level().value
                if self.current_metrics
                else "unknown"
            ),
            "selected_models": selected_models,
            "local_models": [m for m in selected_models if m in self._loaded_models],
            "remote_models": [m for m in selected_models if m in self.remote_endpoints],
        }
        self.routing_decisions.append(routing_decision)

        # Create modified parallel task with selected models
        return await super().submit_parallel_task(
            prompt=prompt,
            model_requirements=model_requirements,
            parallel_count=len(selected_models),
            consensus_required=consensus_required,
            preferred_models=selected_models,
            **kwargs,
        )

    async def _select_resource_aware_models(
        self, requirements: List[str], count: int, preferred: List[str]
    ) -> List[str]:
        """Select models based on current resource awareness strategy"""

        if not self.current_metrics:
            # Fallback to default selection
            return await self._select_default_models(requirements, count, preferred)

        strategy = self.current_strategy
        selected_models = []

        if strategy == ModelRoutingStrategy.LOCAL_ONLY:
            selected_models = await self._select_local_models_only(
                requirements, count, preferred
            )

        elif strategy == ModelRoutingStrategy.LOCAL_PREFERRED:
            selected_models = await self._select_local_preferred(
                requirements, count, preferred
            )

        elif strategy == ModelRoutingStrategy.BALANCED:
            selected_models = await self._select_balanced(
                requirements, count, preferred
            )

        elif strategy == ModelRoutingStrategy.REMOTE_PREFERRED:
            selected_models = await self._select_remote_preferred(
                requirements, count, preferred
            )

        elif strategy == ModelRoutingStrategy.REMOTE_ONLY:
            selected_models = await self._select_remote_models_only(
                requirements, count, preferred
            )

        elif strategy == ModelRoutingStrategy.COST_OPTIMIZED:
            selected_models = await self._select_cost_optimized(
                requirements, count, preferred
            )

        # Ensure we have at least some models
        if not selected_models:
            logger.warning(
                "No models selected by resource-aware strategy, falling back to default"
            )
            selected_models = await self._select_default_models(
                requirements, count, preferred
            )

        return selected_models[:count]

    async def _select_local_models_only(
        self, requirements: List[str], count: int, preferred: List[str]
    ) -> List[str]:
        """Select only local models"""
        local_models = []

        # Check loaded models first
        for model_id, instance in self._loaded_models.items():
            if self._model_meets_requirements(instance.spec, requirements):
                local_models.append(model_id)

        # Load additional models if needed and resources allow
        if (
            len(local_models) < count
            and self.current_metrics.get_threshold_level() == ResourceThreshold.LOW
        ):
            available_models = [
                mid
                for mid, spec in self._available_models.items()
                if mid not in self._loaded_models
                and self._model_meets_requirements(spec, requirements)
            ]

            for model_id in available_models[: count - len(local_models)]:
                if await self.load_model(model_id):
                    local_models.append(model_id)

        # Prioritize preferred models
        preferred_local = [m for m in preferred if m in local_models]
        other_local = [m for m in local_models if m not in preferred]

        return preferred_local + other_local

    async def _select_local_preferred(
        self, requirements: List[str], count: int, preferred: List[str]
    ) -> List[str]:
        """Prefer local models, fallback to remote if needed"""
        selected = []

        # First, try to get local models
        local_models = await self._select_local_models_only(
            requirements, count, preferred
        )
        selected.extend(local_models)

        # If we need more models, add remote ones
        if len(selected) < count:
            remaining_count = count - len(selected)
            remote_models = await self._select_remote_models(
                requirements, remaining_count, preferred
            )
            selected.extend(remote_models)

        return selected

    async def _select_balanced(
        self, requirements: List[str], count: int, preferred: List[str]
    ) -> List[str]:
        """Balance between local and remote models"""
        selected = []

        # Split count between local and remote
        local_count = count // 2
        remote_count = count - local_count

        # Get local models
        local_models = await self._select_local_models_only(
            requirements, local_count, preferred
        )
        selected.extend(local_models)

        # Get remote models
        remote_models = await self._select_remote_models(
            requirements, remote_count, preferred
        )
        selected.extend(remote_models)

        # If one category is short, fill from the other
        if len(selected) < count:
            remaining = count - len(selected)
            if len(local_models) < local_count:
                # Need more remote models
                additional_remote = await self._select_remote_models(
                    requirements, remaining, preferred
                )
                selected.extend(additional_remote)
            else:
                # Need more local models
                additional_local = await self._select_local_models_only(
                    requirements, remaining, preferred
                )
                selected.extend(additional_local)

        return selected

    async def _select_remote_preferred(
        self, requirements: List[str], count: int, preferred: List[str]
    ) -> List[str]:
        """Prefer remote models, fallback to local if needed"""
        selected = []

        # First, try to get remote models
        remote_models = await self._select_remote_models(requirements, count, preferred)
        selected.extend(remote_models)

        # If we need more models, add local ones
        if len(selected) < count:
            remaining_count = count - len(selected)
            local_models = await self._select_local_models_only(
                requirements, remaining_count, preferred
            )
            selected.extend(local_models)

        return selected

    async def _select_remote_models_only(
        self, requirements: List[str], count: int, preferred: List[str]
    ) -> List[str]:
        """Select only remote models"""
        return await self._select_remote_models(requirements, count, preferred)

    async def _select_remote_models(
        self, requirements: List[str], count: int, preferred: List[str]
    ) -> List[str]:
        """Select remote models based on requirements"""
        suitable_remote = []

        for endpoint_id, endpoint in self.remote_endpoints.items():
            if self._endpoint_meets_requirements(endpoint, requirements):
                suitable_remote.append(endpoint_id)

        # Prioritize preferred models
        preferred_remote = [m for m in preferred if m in suitable_remote]
        other_remote = [m for m in suitable_remote if m not in preferred]

        selected = preferred_remote + other_remote
        return selected[:count]

    async def _select_cost_optimized(
        self, requirements: List[str], count: int, preferred: List[str]
    ) -> List[str]:
        """Select models optimized for cost"""
        # Calculate cost per model
        model_costs = {}

        # Local models have minimal cost (just electricity/compute)
        for model_id in self._loaded_models:
            model_costs[model_id] = 0.001  # Very low cost for local

        # Remote models have API costs
        for endpoint_id, endpoint in self.remote_endpoints.items():
            if self._endpoint_meets_requirements(endpoint, requirements):
                model_costs[endpoint_id] = endpoint.cost_per_token

        # Sort by cost (lowest first)
        sorted_models = sorted(model_costs.items(), key=lambda x: x[1])

        # Select lowest cost models that meet requirements
        selected = []
        for model_id, cost in sorted_models:
            if len(selected) >= count:
                break

            # Verify model meets requirements
            if model_id in self._loaded_models:
                instance = self._loaded_models[model_id]
                if self._model_meets_requirements(instance.spec, requirements):
                    selected.append(model_id)
            elif model_id in self.remote_endpoints:
                endpoint = self.remote_endpoints[model_id]
                if self._endpoint_meets_requirements(endpoint, requirements):
                    selected.append(model_id)

        return selected

    async def _select_default_models(
        self, requirements: List[str], count: int, preferred: List[str]
    ) -> List[str]:
        """Default model selection fallback"""
        # Use the original model selection logic
        suitable_models = await self._find_suitable_models_enhanced(requirements)

        # Prioritize preferred models
        preferred_suitable = [m for m in preferred if m in suitable_models]
        other_suitable = [m for m in suitable_models if m not in preferred]

        return (preferred_suitable + other_suitable)[:count]

    async def _find_suitable_models_enhanced(
        self, requirements: List[str]
    ) -> List[str]:
        """Enhanced model finding that includes remote models"""
        suitable = []

        # Add local models
        for model_id, instance in self._loaded_models.items():
            if self._model_meets_requirements(instance.spec, requirements):
                suitable.append(model_id)

        # Add available local models
        for model_id, spec in self._available_models.items():
            if model_id not in self._loaded_models and self._model_meets_requirements(
                spec, requirements
            ):
                suitable.append(model_id)

        # Add remote models
        for endpoint_id, endpoint in self.remote_endpoints.items():
            if self._endpoint_meets_requirements(endpoint, requirements):
                suitable.append(endpoint_id)

        return suitable

    def _model_meets_requirements(
        self, spec: ModelSpec, requirements: List[str]
    ) -> bool:
        """Check if a model spec meets requirements"""
        if not requirements:
            return True

        model_caps = [cap.value for cap in spec.capabilities]
        return all(req in model_caps for req in requirements)

    def _endpoint_meets_requirements(
        self, endpoint: RemoteModelEndpoint, requirements: List[str]
    ) -> bool:
        """Check if a remote endpoint meets requirements"""
        if not requirements:
            return True

        return all(req in endpoint.capabilities for req in requirements)

    async def _execute_on_model(
        self, task: ParallelTask, model_id: str
    ) -> Dict[str, Any]:
        """Execute task on model (local or remote)"""

        # Check if it's a local model
        if model_id in self._loaded_models:
            # Track local execution cost
            self.cost_tracking["local"] += 0.001  # Minimal local cost
            return await super()._execute_on_model(task, model_id)

        # Check if it's a remote model
        elif model_id in self.remote_endpoints:
            return await self._execute_on_remote_model(task, model_id)

        else:
            raise Exception(f"Unknown model: {model_id}")

    async def _execute_on_remote_model(
        self, task: ParallelTask, endpoint_id: str
    ) -> Dict[str, Any]:
        """Execute task on remote model endpoint"""
        if endpoint_id not in self.remote_endpoints:
            raise Exception(f"Remote endpoint {endpoint_id} not found")

        endpoint = self.remote_endpoints[endpoint_id]

        try:
            start_time = datetime.now(timezone.utc)

            # Prepare request payload
            payload = await self._prepare_remote_payload(task, endpoint)

            # Make API request
            async with aiohttp.ClientSession() as session:
                headers = await self._prepare_remote_headers(endpoint)

                async with session.post(
                    endpoint.endpoint_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=task.timeout_seconds),
                ) as response:

                    if response.status == 200:
                        result_data = await response.json()

                        end_time = datetime.now(timezone.utc)
                        execution_time = (end_time - start_time).total_seconds()

                        # Calculate and track cost
                        estimated_tokens = (
                            len(task.prompt.split()) * 1.3
                        )  # Rough estimate
                        cost = estimated_tokens * endpoint.cost_per_token
                        self.cost_tracking["remote"] += cost

                        return {
                            "model_id": endpoint_id,
                            "model_name": endpoint.name,
                            "result": result_data,
                            "execution_time": execution_time,
                            "timestamp": end_time.isoformat(),
                            "cost": cost,
                            "endpoint_type": "remote",
                        }
                    else:
                        raise Exception(
                            f"Remote API error: {response.status} - {await response.text()}"
                        )

        except Exception as e:
            logger.error(f"Remote execution failed on {endpoint_id}: {e}")
            raise

    async def _prepare_remote_payload(
        self, task: ParallelTask, endpoint: RemoteModelEndpoint
    ) -> Dict[str, Any]:
        """Prepare payload for remote API call"""
        max_tokens = min(task.max_tokens, endpoint.max_tokens)
        provider = (endpoint.provider or "openai").lower()

        if provider == "anthropic":
            return {
                "model": endpoint.model_name,
                "max_tokens": max_tokens,
                "temperature": task.temperature,
                "messages": [{"role": "user", "content": task.prompt}],
            }

        if provider == "gemini":
            return {
                "contents": [{"parts": [{"text": task.prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": task.temperature,
                },
            }

        return {
            "model": endpoint.model_name,
            "messages": [{"role": "user", "content": task.prompt}],
            "max_tokens": max_tokens,
            "temperature": task.temperature,
        }

    async def _prepare_remote_headers(
        self, endpoint: RemoteModelEndpoint
    ) -> Dict[str, str]:
        """Prepare headers for remote API call"""
        headers = {"Content-Type": "application/json"}

        provider = (endpoint.provider or "openai").lower()
        if endpoint.api_key:
            if provider == "anthropic":
                headers["x-api-key"] = endpoint.api_key
                headers.setdefault("anthropic-version", "2023-06-01")
            elif provider == "gemini":
                headers["x-goog-api-key"] = endpoint.api_key
            else:
                headers["Authorization"] = f"Bearer {endpoint.api_key}"

        return headers

    def get_resource_aware_status(self) -> Dict[str, Any]:
        """Get status of resource-aware model management"""
        status = self.get_health()

        # Add resource-aware specific information
        status.update(
            {
                "resource_awareness_enabled": self.enable_resource_awareness,
                "current_strategy": self.current_strategy.value,
                "current_metrics": (
                    self.current_metrics.to_dict() if self.current_metrics else None
                ),
                "resource_threshold": (
                    self.current_metrics.get_threshold_level().value
                    if self.current_metrics
                    else "unknown"
                ),
                "remote_endpoints": len(self.remote_endpoints),
                "cost_tracking": self.cost_tracking.copy(),
                "routing_decisions_count": len(self.routing_decisions),
                "recent_routing_decisions": (
                    self.routing_decisions[-5:] if self.routing_decisions else []
                ),
            }
        )

        return status

    async def set_resource_thresholds(self, thresholds: Dict[str, Dict[str, Any]]):
        """Update resource thresholds configuration"""
        for threshold_name, config in thresholds.items():
            try:
                threshold_level = ResourceThreshold(threshold_name)
                self.resource_thresholds[threshold_level].update(config)
                logger.info(f"Updated resource threshold: {threshold_name}")
            except ValueError:
                logger.warning(f"Unknown resource threshold: {threshold_name}")

    async def add_remote_endpoint(self, endpoint_config: Dict[str, Any]) -> bool:
        """Add a new remote model endpoint"""
        try:
            endpoint = RemoteModelEndpoint(**endpoint_config)
            self.remote_endpoints[endpoint.id] = endpoint
            logger.info(f"Added remote endpoint: {endpoint.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add remote endpoint: {e}")
            return False

    async def remove_remote_endpoint(self, endpoint_id: str) -> bool:
        """Remove a remote model endpoint"""
        if endpoint_id in self.remote_endpoints:
            del self.remote_endpoints[endpoint_id]
            logger.info(f"Removed remote endpoint: {endpoint_id}")
            return True
        return False

    def get_cost_analysis(self) -> Dict[str, Any]:
        """Get cost analysis of local vs remote usage"""
        total_local = self.cost_tracking["local"]
        total_remote = self.cost_tracking["remote"]
        total_cost = total_local + total_remote

        return {
            "total_cost": total_cost,
            "local_cost": total_local,
            "remote_cost": total_remote,
            "local_percentage": (
                (total_local / total_cost * 100) if total_cost > 0 else 0
            ),
            "remote_percentage": (
                (total_remote / total_cost * 100) if total_cost > 0 else 0
            ),
            "cost_savings_vs_remote_only": max(
                0, total_remote * 2 - total_cost
            ),  # Estimated savings
            "recommendations": self._generate_cost_recommendations(),
        }

    def _generate_cost_recommendations(self) -> List[str]:
        """Generate cost optimization recommendations"""
        recommendations = []

        local_cost = self.cost_tracking["local"]
        remote_cost = self.cost_tracking["remote"]

        if remote_cost > local_cost * 5:
            recommendations.append(
                "Consider loading more local models to reduce remote API costs"
            )

        if len(self._loaded_models) == 0 and len(self._available_models) > 0:
            recommendations.append(
                "Load local models to reduce dependency on remote APIs"
            )

        if (
            self.current_metrics
            and self.current_metrics.get_threshold_level() == ResourceThreshold.LOW
        ):
            recommendations.append(
                "System resources are low - good time to use local models"
            )

        return recommendations
