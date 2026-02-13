"""
Guild Model Manager - Local LM Studio integration with parallel agent tasking
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from loguru import logger
from datetime import datetime, timezone, timedelta
import uuid
import psutil

try:
    import GPUtil
except ImportError:  # pragma: no cover - optional GPU dependency
    GPUtil = None

from .communication_hub import CommunicationChannel, MessagePriority


class ModelStatus(Enum):
    AVAILABLE = "available"
    LOADING = "loading"
    LOADED = "loaded"
    BUSY = "busy"
    ERROR = "error"
    UNLOADED = "unloaded"


class ModelCapability(Enum):
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    CONVERSATION = "conversation"
    INSTRUCTION_FOLLOWING = "instruction_following"
    REASONING = "reasoning"
    MATH = "math"
    CODING = "coding"
    CREATIVE_WRITING = "creative_writing"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"


class ModelSize(Enum):
    TINY = "tiny"  # < 1B parameters
    SMALL = "small"  # 1B - 7B parameters
    MEDIUM = "medium"  # 7B - 13B parameters
    LARGE = "large"  # 13B - 30B parameters
    XLARGE = "xlarge"  # 30B+ parameters


@dataclass
class ModelSpec:
    """Specification for a local language model"""

    id: str
    name: str
    path: str
    size: ModelSize
    parameters: str  # e.g., "7B", "13B"
    capabilities: List[ModelCapability]
    context_length: int = 4096
    quantization: Optional[str] = None  # e.g., "Q4_K_M", "Q8_0"
    architecture: Optional[str] = None  # e.g., "llama", "mistral"
    memory_required_gb: float = 0.0
    vram_required_gb: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "size": self.size.value,
            "parameters": self.parameters,
            "capabilities": [cap.value for cap in self.capabilities],
            "context_length": self.context_length,
            "quantization": self.quantization,
            "architecture": self.architecture,
            "memory_required_gb": self.memory_required_gb,
            "vram_required_gb": self.vram_required_gb,
            "metadata": self.metadata,
        }


@dataclass
class ModelInstance:
    """Running instance of a language model"""

    spec: ModelSpec
    status: ModelStatus
    endpoint: str
    port: int
    process_id: Optional[int] = None
    loaded_at: Optional[str] = None
    last_used: Optional[str] = None
    active_sessions: Set[str] = field(default_factory=set)
    total_requests: int = 0
    total_tokens: int = 0
    error_message: Optional[str] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec": self.spec.to_dict(),
            "status": self.status.value,
            "endpoint": self.endpoint,
            "port": self.port,
            "process_id": self.process_id,
            "loaded_at": self.loaded_at,
            "last_used": self.last_used,
            "active_sessions": list(self.active_sessions),
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "error_message": self.error_message,
            "performance_metrics": self.performance_metrics,
        }


@dataclass
class ParallelTask:
    """Task that can be executed in parallel across multiple models"""

    id: str
    prompt: str
    model_requirements: List[ModelCapability]
    preferred_models: List[str] = field(default_factory=list)
    max_tokens: int = 1000
    temperature: float = 0.7
    parallel_count: int = 1  # Number of parallel executions
    consensus_required: bool = False  # Require consensus across results
    priority: str = "normal"
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Execution tracking
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: List[Dict[str, Any]] = field(default_factory=list)
    consensus_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "model_requirements": [req.value for req in self.model_requirements],
            "preferred_models": self.preferred_models,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "parallel_count": self.parallel_count,
            "consensus_required": self.consensus_required,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "results": self.results,
            "consensus_result": self.consensus_result,
        }


class ModelManager:
    """
    Local LM Studio model manager with parallel agent tasking capabilities.

    Features:
    - Automatic model discovery and management
    - Dynamic model loading/unloading based on demand
    - Parallel task execution across multiple models
    - Consensus-based result aggregation
    - Resource optimization and load balancing
    - Integration with Guild agent system
    """

    def __init__(self, config, guild_core):
        self.config = config
        self.guild_core = guild_core
        self._running = False

        # LM Studio configuration
        self.lm_studio_host = "localhost"
        self.lm_studio_base_port = 1234
        self.lm_studio_models_path = Path.home() / ".cache" / "lm-studio" / "models"
        self.model_routing_path = (
            Path(__file__).resolve().parent / "config" / "model_routing.json"
        )
        self.model_routing: Dict[str, Any] = {}
        self._model_routing_mtime: Optional[float] = None

        # Model management
        self._available_models: Dict[str, ModelSpec] = {}
        self._loaded_models: Dict[str, ModelInstance] = {}
        self._model_queue: asyncio.Queue = asyncio.Queue()
        self._port_pool = list(range(1234, 1244))  # 10 available ports
        self._used_ports: Set[int] = set()

        # Parallel tasking
        self._parallel_tasks: Dict[str, ParallelTask] = {}
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._execution_semaphore = asyncio.Semaphore(5)  # Max 5 concurrent tasks

        # Resource monitoring
        self._resource_monitor_task: Optional[asyncio.Task] = None
        self._task_processor_task: Optional[asyncio.Task] = None
        self._model_manager_task: Optional[asyncio.Task] = None

        # Performance tracking
        self._performance_history: List[Dict[str, Any]] = []

        # Routing configuration
        self._load_model_routing()

        logger.info("Model Manager initialized")

    async def start(self) -> None:
        """Start the model manager"""
        if self._running:
            return

        self._running = True

        # Discover available models
        await self._discover_models()

        # Start background tasks
        self._resource_monitor_task = asyncio.create_task(self._resource_monitor_loop())
        self._task_processor_task = asyncio.create_task(self._task_processor_loop())
        self._model_manager_task = asyncio.create_task(self._model_manager_loop())

        # Subscribe to Guild events
        self.guild_core.communication_hub.subscribe(
            CommunicationChannel.AGENT_COORDINATION, self._handle_agent_event
        )

        # Register as model management capability
        await self.guild_core.agent_coordinator.register_agent(
            agent_id="model_manager",
            name="Local Model Manager",
            capabilities=[
                "model_management",
                "parallel_inference",
                "consensus_generation",
            ],
            metadata={
                "type": "model_manager",
                "models_available": len(self._available_models),
            },
        )

        logger.info(
            f"Model Manager started with {len(self._available_models)} available models"
        )

    async def stop(self) -> None:
        """Stop the model manager"""
        if not self._running:
            return

        self._running = False

        # Unload all models
        await self._unload_all_models()

        # Cancel background tasks
        for task in [
            self._resource_monitor_task,
            self._task_processor_task,
            self._model_manager_task,
        ]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("Model Manager stopped")

    async def _discover_models(self) -> None:
        """Discover available models from LM Studio"""
        try:
            # Check if LM Studio models directory exists
            if not self.lm_studio_models_path.exists():
                logger.warning(
                    f"LM Studio models path not found: {self.lm_studio_models_path}"
                )
                return

            # Scan for model files
            model_files = []
            for pattern in ["*.gguf", "*.bin", "*.safetensors"]:
                model_files.extend(self.lm_studio_models_path.rglob(pattern))

            # Parse model specifications
            for model_file in model_files:
                try:
                    model_spec = await self._parse_model_file(model_file)
                    if model_spec:
                        self._available_models[model_spec.id] = model_spec
                        logger.debug(f"Discovered model: {model_spec.name}")
                except Exception as e:
                    logger.warning(f"Failed to parse model file {model_file}: {e}")

            # Also try to discover via LM Studio API
            await self._discover_via_api()

            logger.info(f"Discovered {len(self._available_models)} models")

        except Exception as e:
            logger.error(f"Failed to discover models: {e}")

    async def _parse_model_file(self, model_file: Path) -> Optional[ModelSpec]:
        """Parse a model file to extract specifications"""
        try:
            # Extract model info from path and filename
            relative_path = model_file.relative_to(self.lm_studio_models_path)
            parts = relative_path.parts

            if len(parts) < 2:
                return None

            # Typical structure: publisher/model-name/model-file.gguf
            publisher = parts[0]
            model_name = parts[1] if len(parts) > 1 else "unknown"
            filename = model_file.name

            # Extract quantization from filename
            quantization = None
            if "Q4_K_M" in filename:
                quantization = "Q4_K_M"
            elif "Q8_0" in filename:
                quantization = "Q8_0"
            elif "Q5_K_M" in filename:
                quantization = "Q5_K_M"

            # Estimate parameters from model name
            parameters = "7B"  # Default
            size = ModelSize.MEDIUM

            if any(x in filename.lower() for x in ["1b", "1.1b"]):
                parameters = "1B"
                size = ModelSize.TINY
            elif any(x in filename.lower() for x in ["3b", "3.8b"]):
                parameters = "3B"
                size = ModelSize.SMALL
            elif any(x in filename.lower() for x in ["7b", "6.7b"]):
                parameters = "7B"
                size = ModelSize.MEDIUM
            elif any(x in filename.lower() for x in ["13b", "14b"]):
                parameters = "13B"
                size = ModelSize.LARGE
            elif any(x in filename.lower() for x in ["30b", "33b", "34b", "70b"]):
                parameters = "30B+"
                size = ModelSize.XLARGE

            # Determine capabilities based on model name
            capabilities = [
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CONVERSATION,
            ]

            if any(x in model_name.lower() for x in ["code", "coder", "coding"]):
                capabilities.extend(
                    [ModelCapability.CODE_GENERATION, ModelCapability.CODING]
                )

            if any(x in model_name.lower() for x in ["instruct", "chat"]):
                capabilities.append(ModelCapability.INSTRUCTION_FOLLOWING)

            if any(x in model_name.lower() for x in ["math", "reasoning"]):
                capabilities.extend([ModelCapability.MATH, ModelCapability.REASONING])

            # Estimate resource requirements
            memory_gb = self._estimate_memory_requirements(parameters, quantization)
            vram_gb = memory_gb * 0.8  # Estimate VRAM as 80% of total memory

            model_spec = ModelSpec(
                id=f"{publisher}_{model_name}_{filename}".replace("/", "_").replace(
                    " ", "_"
                ),
                name=f"{publisher}/{model_name}",
                path=str(model_file),
                size=size,
                parameters=parameters,
                capabilities=capabilities,
                quantization=quantization,
                memory_required_gb=memory_gb,
                vram_required_gb=vram_gb,
                metadata={
                    "publisher": publisher,
                    "filename": filename,
                    "file_size_mb": model_file.stat().st_size / (1024 * 1024),
                },
            )

            return model_spec

        except Exception as e:
            logger.error(f"Failed to parse model file {model_file}: {e}")
            return None

    def _estimate_memory_requirements(
        self, parameters: str, quantization: Optional[str]
    ) -> float:
        """Estimate memory requirements for a model"""
        # Base memory requirements (in GB)
        param_memory = {"1B": 2.0, "3B": 4.0, "7B": 8.0, "13B": 16.0, "30B+": 32.0}

        base_memory = param_memory.get(parameters, 8.0)

        # Adjust for quantization
        if quantization:
            if "Q4" in quantization:
                base_memory *= 0.5  # 4-bit quantization roughly halves memory
            elif "Q8" in quantization:
                base_memory *= 0.75  # 8-bit quantization reduces by ~25%

        return base_memory

    async def _discover_via_api(self) -> None:
        """Discover models via LM Studio API"""
        try:
            async with aiohttp.ClientSession() as session:
                # Try to get models from LM Studio API
                async with session.get(
                    f"http://{self.lm_studio_host}:{self.lm_studio_base_port}/v1/models"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        for model_data in data.get("data", []):
                            model_id = model_data.get("id", "")
                            if model_id and model_id not in self._available_models:
                                # Create spec from API data
                                model_spec = ModelSpec(
                                    id=model_id,
                                    name=model_id,
                                    path="",  # API-based model
                                    size=ModelSize.MEDIUM,  # Default
                                    parameters="7B",  # Default
                                    capabilities=[
                                        ModelCapability.TEXT_GENERATION,
                                        ModelCapability.CONVERSATION,
                                    ],
                                    metadata={"source": "api", "api_data": model_data},
                                )
                                self._available_models[model_id] = model_spec

        except Exception as e:
            logger.debug(f"Could not discover models via API: {e}")

    async def load_model(self, model_id: str, force: bool = False) -> bool:
        """Load a specific model"""
        try:
            if model_id in self._loaded_models and not force:
                logger.info(f"Model {model_id} already loaded")
                return True

            if model_id not in self._available_models:
                logger.error(f"Model {model_id} not available")
                return False

            model_spec = self._available_models[model_id]

            # Check resource availability
            if not await self._check_resources_available(model_spec):
                logger.warning(f"Insufficient resources to load model {model_id}")
                return False

            # Get available port
            port = await self._get_available_port()
            if not port:
                logger.error("No available ports for model loading")
                return False

            # Load model via LM Studio
            success = await self._load_model_via_lm_studio(model_spec, port)

            if success:
                # Create model instance
                instance = ModelInstance(
                    spec=model_spec,
                    status=ModelStatus.LOADED,
                    endpoint=f"http://{self.lm_studio_host}:{port}",
                    port=port,
                    loaded_at=datetime.now(timezone.utc).isoformat(),
                )

                self._loaded_models[model_id] = instance
                self._used_ports.add(port)

                # Emit event
                await self.guild_core.communication_hub.emit_event(
                    "model.loaded",
                    {"model_id": model_id, "model_name": model_spec.name, "port": port},
                    CommunicationChannel.SYSTEM_ALERTS,
                    MessagePriority.NORMAL,
                )

                logger.info(f"Model {model_id} loaded successfully on port {port}")
                return True
            else:
                self._port_pool.append(port)  # Return port to pool
                return False

        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            return False

    async def _check_resources_available(self, model_spec: ModelSpec) -> bool:
        """Check if sufficient resources are available to load model"""
        try:
            # Check system memory
            memory = psutil.virtual_memory()
            available_memory_gb = memory.available / (1024**3)

            if available_memory_gb < model_spec.memory_required_gb:
                logger.warning(
                    f"Insufficient RAM: need {model_spec.memory_required_gb}GB, have {available_memory_gb:.1f}GB"
                )
                return False

            # Check GPU memory if required
            if model_spec.vram_required_gb > 0:
                try:
                    if GPUtil is None:
                        logger.debug("GPUtil not installed; skipping GPU memory check")
                    else:
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            max_free_vram = max(
                                gpu.memoryFree / 1024 for gpu in gpus
                            )  # Convert MB to GB
                            if max_free_vram < model_spec.vram_required_gb:
                                logger.warning(
                                    "Insufficient VRAM: need "
                                    f"{model_spec.vram_required_gb}GB, have {max_free_vram:.1f}GB"
                                )
                                return False
                except Exception:
                    logger.debug("Could not check GPU memory")

            return True

        except Exception as e:
            logger.error(f"Failed to check resources: {e}")
            return False

    async def _get_available_port(self) -> Optional[int]:
        """Get an available port from the pool"""
        if self._port_pool:
            return self._port_pool.pop(0)
        return None

    async def _load_model_via_lm_studio(self, model_spec: ModelSpec, port: int) -> bool:
        """Load model via LM Studio API or CLI"""
        try:
            # Try API approach first
            if await self._load_via_api(model_spec, port):
                return True

            # Fallback to CLI approach
            return await self._load_via_cli(model_spec, port)

        except Exception as e:
            logger.error(f"Failed to load model via LM Studio: {e}")
            return False

    async def _load_via_api(self, model_spec: ModelSpec, port: int) -> bool:
        """Load model via LM Studio API"""
        try:
            async with aiohttp.ClientSession():
                # This would depend on LM Studio's specific API
                # For now, simulate successful loading
                await asyncio.sleep(2)  # Simulate loading time
                return True

        except Exception as e:
            logger.debug(f"API loading failed: {e}")
            return False

    async def _load_via_cli(self, model_spec: ModelSpec, port: int) -> bool:
        """Load model via LM Studio CLI"""
        try:
            # This would use subprocess to start LM Studio with specific model
            # For now, simulate successful loading
            await asyncio.sleep(3)  # Simulate loading time
            return True

        except Exception as e:
            logger.debug(f"CLI loading failed: {e}")
            return False

    async def unload_model(self, model_id: str) -> bool:
        """Unload a specific model"""
        try:
            if model_id not in self._loaded_models:
                logger.warning(f"Model {model_id} not loaded")
                return True

            instance = self._loaded_models[model_id]

            # Stop model process/service
            success = await self._unload_model_instance(instance)

            if success:
                # Return port to pool
                self._used_ports.discard(instance.port)
                self._port_pool.append(instance.port)

                # Remove from loaded models
                del self._loaded_models[model_id]

                # Emit event
                await self.guild_core.communication_hub.emit_event(
                    "model.unloaded",
                    {"model_id": model_id, "model_name": instance.spec.name},
                    CommunicationChannel.SYSTEM_ALERTS,
                    MessagePriority.NORMAL,
                )

                logger.info(f"Model {model_id} unloaded successfully")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to unload model {model_id}: {e}")
            return False

    async def _unload_model_instance(self, instance: ModelInstance) -> bool:
        """Unload a specific model instance"""
        try:
            # Terminate any active sessions
            instance.active_sessions.clear()

            # Stop the model service (implementation depends on how models are started)
            if instance.process_id:
                try:
                    import psutil

                    process = psutil.Process(instance.process_id)
                    process.terminate()
                    await asyncio.sleep(2)
                    if process.is_running():
                        process.kill()
                except Exception as e:
                    logger.warning(
                        f"Failed to terminate process {instance.process_id}: {e}"
                    )

            return True

        except Exception as e:
            logger.error(f"Failed to unload model instance: {e}")
            return False

    async def _unload_all_models(self) -> None:
        """Unload all loaded models"""
        model_ids = list(self._loaded_models.keys())
        for model_id in model_ids:
            await self.unload_model(model_id)

    async def submit_parallel_task(
        self,
        prompt: str,
        model_requirements: List[str] = None,
        parallel_count: int = 3,
        consensus_required: bool = True,
        preferred_models: List[str] = None,
        **kwargs,
    ) -> str:
        """Submit a task for parallel execution across multiple models"""
        try:
            # Convert string requirements to enum
            requirements = []
            if model_requirements:
                for req in model_requirements:
                    try:
                        requirements.append(ModelCapability(req))
                    except ValueError:
                        logger.warning(f"Unknown model capability: {req}")

            if not requirements:
                requirements = [ModelCapability.TEXT_GENERATION]

            # Create parallel task
            task_id = f"parallel-{uuid.uuid4().hex[:8]}"

            routing_preferred = self._get_routing_preferred(
                requirements,
                kwargs.get("metadata", {}),
            )
            merged_preferred = self._merge_preferred_models(
                preferred_models or [],
                routing_preferred,
            )

            task = ParallelTask(
                id=task_id,
                prompt=prompt,
                model_requirements=requirements,
                preferred_models=merged_preferred,
                parallel_count=parallel_count,
                consensus_required=consensus_required,
                max_tokens=kwargs.get("max_tokens", 1000),
                temperature=kwargs.get("temperature", 0.7),
                priority=kwargs.get("priority", "normal"),
                timeout_seconds=kwargs.get("timeout_seconds", 300),
                metadata=kwargs.get("metadata", {}),
            )

            self._parallel_tasks[task_id] = task

            # Queue for processing
            await self._task_queue.put(task_id)

            # Emit event
            await self.guild_core.communication_hub.emit_event(
                "parallel_task.submitted",
                {
                    "task_id": task_id,
                    "parallel_count": parallel_count,
                    "consensus_required": consensus_required,
                    "requirements": [req.value for req in requirements],
                },
                CommunicationChannel.BATCH_PROCESSING,
                MessagePriority.NORMAL,
            )

            logger.info(
                f"Parallel task {task_id} submitted for {parallel_count} models"
            )
            return task_id

        except Exception as e:
            logger.error(f"Failed to submit parallel task: {e}")
            return ""

    def _merge_preferred_models(
        self, explicit: List[str], routed: List[str]
    ) -> List[str]:
        """Merge explicit and routed preferred models without duplicates."""
        merged: List[str] = []
        for model_id in explicit + routed:
            if model_id and model_id not in merged:
                merged.append(model_id)
        return merged

    def _load_model_routing(self) -> None:
        """Load routing preferences from config."""
        try:
            if not self.model_routing_path.exists():
                return
            mtime = self.model_routing_path.stat().st_mtime
            if self._model_routing_mtime and mtime <= self._model_routing_mtime:
                return
            self.model_routing = json.loads(
                self.model_routing_path.read_text(encoding="utf-8")
            )
            self._model_routing_mtime = mtime
        except Exception as exc:
            logger.warning(f"Failed to load model routing config: {exc}")

    def _get_routing_preferred(
        self,
        requirements: List[ModelCapability],
        metadata: Dict[str, Any],
    ) -> List[str]:
        """Return preferred models based on routing config and task context."""
        self._load_model_routing()
        if not self.model_routing:
            return []

        category = metadata.get("routing_category") or metadata.get("category")
        if not category:
            category = self._infer_routing_category(requirements)
        if not category:
            category = self.model_routing.get("default_category", "chat")

        categories = self.model_routing.get("categories", {})
        preferred = categories.get(category, [])
        return list(preferred) if isinstance(preferred, list) else []

    def _infer_routing_category(
        self, requirements: List[ModelCapability]
    ) -> Optional[str]:
        """Infer routing category from capability requirements."""
        if any(
            cap in requirements
            for cap in [ModelCapability.CODE_GENERATION, ModelCapability.CODING]
        ):
            return "code"
        if any(
            cap in requirements
            for cap in [ModelCapability.REASONING, ModelCapability.MATH]
        ):
            return "reasoning"
        if any(
            cap in requirements
            for cap in [
                ModelCapability.CONVERSATION,
                ModelCapability.INSTRUCTION_FOLLOWING,
            ]
        ):
            return "chat"
        return None

    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a parallel task"""
        if task_id not in self._parallel_tasks:
            return None

        task = self._parallel_tasks[task_id]

        if task.consensus_result:
            return task.consensus_result
        elif task.results:
            return {
                "task_id": task_id,
                "status": "completed" if task.completed_at else "in_progress",
                "results": task.results,
                "consensus": task.consensus_result,
            }
        else:
            return {
                "task_id": task_id,
                "status": "pending" if not task.started_at else "in_progress",
                "results": [],
                "consensus": None,
            }

    async def _task_processor_loop(self) -> None:
        """Process parallel tasks from the queue"""
        while self._running:
            try:
                # Get task with timeout
                task_id = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)

                # Process task with semaphore to limit concurrency
                async with self._execution_semaphore:
                    await self._process_parallel_task(task_id)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in task processor loop: {e}")

    async def _process_parallel_task(self, task_id: str) -> None:
        """Process a single parallel task"""
        try:
            if task_id not in self._parallel_tasks:
                return

            task = self._parallel_tasks[task_id]
            task.started_at = datetime.now(timezone.utc).isoformat()

            # Find suitable models
            suitable_models = await self._find_suitable_models(task)

            if len(suitable_models) < task.parallel_count:
                # Load additional models if needed
                await self._ensure_models_available(task, suitable_models)
                suitable_models = await self._find_suitable_models(task)

            if not suitable_models:
                logger.error(f"No suitable models found for task {task_id}")
                return

            # Select models for parallel execution
            selected_models = suitable_models[: task.parallel_count]

            # Execute task in parallel across selected models
            execution_tasks = []
            for model_id in selected_models:
                execution_tasks.append(self._execute_on_model(task, model_id))

            # Wait for all executions to complete
            results = await asyncio.gather(*execution_tasks, return_exceptions=True)

            # Process results
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Execution failed on model {selected_models[i]}: {result}"
                    )
                else:
                    valid_results.append(result)

            task.results = valid_results
            task.completed_at = datetime.now(timezone.utc).isoformat()

            # Generate consensus if required
            if task.consensus_required and len(valid_results) > 1:
                task.consensus_result = await self._generate_consensus(
                    task, valid_results
                )

            # Emit completion event
            await self.guild_core.communication_hub.emit_event(
                "parallel_task.completed",
                {
                    "task_id": task_id,
                    "results_count": len(valid_results),
                    "consensus_generated": task.consensus_result is not None,
                    "execution_time": self._calculate_execution_time(task),
                },
                CommunicationChannel.BATCH_PROCESSING,
                MessagePriority.HIGH,
            )

            logger.info(
                f"Parallel task {task_id} completed with {len(valid_results)} results"
            )

        except Exception as e:
            logger.error(f"Failed to process parallel task {task_id}: {e}")
            if task_id in self._parallel_tasks:
                task = self._parallel_tasks[task_id]
                task.completed_at = datetime.now(timezone.utc).isoformat()
                task.metadata["error"] = str(e)

    async def _find_suitable_models(self, task: ParallelTask) -> List[str]:
        """Find models suitable for the given task"""
        suitable_models = []

        # Check loaded models first
        for model_id, instance in self._loaded_models.items():
            if instance.status == ModelStatus.LOADED and self._model_has_capabilities(
                instance.spec, task.model_requirements
            ):
                suitable_models.append(model_id)

        # Add preferred models if they're suitable
        for preferred_model in task.preferred_models:
            if (
                preferred_model in self._available_models
                and preferred_model not in suitable_models
                and self._model_has_capabilities(
                    self._available_models[preferred_model], task.model_requirements
                )
            ):
                suitable_models.insert(
                    0, preferred_model
                )  # Prioritize preferred models

        return suitable_models

    def _model_has_capabilities(
        self, model_spec: ModelSpec, required_capabilities: List[ModelCapability]
    ) -> bool:
        """Check if model has required capabilities"""
        return all(cap in model_spec.capabilities for cap in required_capabilities)

    async def _ensure_models_available(
        self, task: ParallelTask, current_models: List[str]
    ) -> None:
        """Ensure enough suitable models are loaded"""
        needed_count = task.parallel_count - len(current_models)

        if needed_count <= 0:
            return

        # Find additional models to load
        candidates = []
        for model_id, model_spec in self._available_models.items():
            if (
                model_id not in self._loaded_models
                and model_id not in current_models
                and self._model_has_capabilities(model_spec, task.model_requirements)
            ):
                candidates.append(model_id)

        # Sort by preference and resource requirements
        candidates.sort(
            key=lambda x: (
                x not in task.preferred_models,  # Preferred models first
                self._available_models[x].memory_required_gb,  # Smaller models first
            )
        )

        # Load additional models
        for model_id in candidates[:needed_count]:
            success = await self.load_model(model_id)
            if success:
                logger.info(f"Loaded additional model {model_id} for parallel task")
            else:
                logger.warning(f"Failed to load additional model {model_id}")

    async def _execute_on_model(
        self, task: ParallelTask, model_id: str
    ) -> Dict[str, Any]:
        """Execute task on a specific model"""
        try:
            if model_id not in self._loaded_models:
                raise Exception(f"Model {model_id} not loaded")

            instance = self._loaded_models[model_id]
            session_id = str(uuid.uuid4())

            # Add to active sessions
            instance.active_sessions.add(session_id)

            try:
                # Make request to model
                start_time = datetime.now(timezone.utc)

                async with aiohttp.ClientSession() as session:
                    payload = {
                        "model": instance.spec.name,
                        "messages": [{"role": "user", "content": task.prompt}],
                        "max_tokens": task.max_tokens,
                        "temperature": task.temperature,
                        "stream": False,
                    }

                    async with session.post(
                        f"{instance.endpoint}/v1/chat/completions",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=task.timeout_seconds),
                    ) as response:
                        if response.status == 200:
                            result_data = await response.json()

                            end_time = datetime.now(timezone.utc)
                            execution_time = (end_time - start_time).total_seconds()

                            # Update instance metrics
                            instance.total_requests += 1
                            instance.last_used = end_time.isoformat()

                            if "usage" in result_data:
                                instance.total_tokens += result_data["usage"].get(
                                    "total_tokens", 0
                                )

                            # Update performance metrics
                            instance.performance_metrics["avg_response_time"] = (
                                instance.performance_metrics.get("avg_response_time", 0)
                                * 0.9
                                + execution_time * 0.1
                            )

                            return {
                                "model_id": model_id,
                                "model_name": instance.spec.name,
                                "result": result_data,
                                "execution_time": execution_time,
                                "timestamp": end_time.isoformat(),
                                "session_id": session_id,
                            }
                        else:
                            raise Exception(
                                f"HTTP {response.status}: {await response.text()}"
                            )

            finally:
                # Remove from active sessions
                instance.active_sessions.discard(session_id)

        except Exception as e:
            logger.error(f"Execution failed on model {model_id}: {e}")
            raise

    async def _generate_consensus(
        self, task: ParallelTask, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate consensus from multiple model results"""
        try:
            if len(results) < 2:
                return results[0] if results else {}

            # Extract text responses
            responses = []
            for result in results:
                if "result" in result and "choices" in result["result"]:
                    choices = result["result"]["choices"]
                    if choices and "message" in choices[0]:
                        responses.append(choices[0]["message"]["content"])

            if not responses:
                return {}

            # Simple consensus: use the most common response or the longest one
            if len(set(responses)) == 1:
                # All responses are identical
                consensus_text = responses[0]
                confidence = 1.0
            else:
                # Find most common response
                from collections import Counter

                response_counts = Counter(responses)
                most_common = response_counts.most_common(1)[0]

                if most_common[1] > 1:
                    # Multiple models gave the same response
                    consensus_text = most_common[0]
                    confidence = most_common[1] / len(responses)
                else:
                    # All responses are different, use the longest one
                    consensus_text = max(responses, key=len)
                    confidence = 0.5  # Low confidence for diverse responses

            return {
                "consensus_text": consensus_text,
                "confidence": confidence,
                "total_responses": len(responses),
                "unique_responses": len(set(responses)),
                "all_responses": responses,
                "method": "simple_consensus",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to generate consensus: {e}")
            return {"error": str(e)}

    def _calculate_execution_time(self, task: ParallelTask) -> Optional[float]:
        """Calculate task execution time in seconds"""
        if not task.started_at or not task.completed_at:
            return None

        start = datetime.fromisoformat(task.started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(task.completed_at.replace("Z", "+00:00"))

        return (end - start).total_seconds()

    async def _resource_monitor_loop(self) -> None:
        """Monitor system resources and manage models accordingly"""
        while self._running:
            try:
                await self._monitor_resources()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitor error: {e}")
                await asyncio.sleep(10)

    async def _monitor_resources(self) -> None:
        """Monitor system resources and optimize model loading"""
        try:
            # Get system resource usage
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)

            # Check if we need to unload unused models
            if memory.percent > 85:  # High memory usage
                await self._unload_unused_models()

            # Update performance history
            self._performance_history.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "memory_percent": memory.percent,
                    "cpu_percent": cpu_percent,
                    "loaded_models": len(self._loaded_models),
                    "active_tasks": len(
                        [
                            t
                            for t in self._parallel_tasks.values()
                            if t.started_at and not t.completed_at
                        ]
                    ),
                }
            )

            # Keep history manageable
            if len(self._performance_history) > 1000:
                self._performance_history = self._performance_history[-500:]

        except Exception as e:
            logger.error(f"Failed to monitor resources: {e}")

    async def _unload_unused_models(self) -> None:
        """Unload models that haven't been used recently"""
        try:
            now = datetime.now(timezone.utc)
            unused_threshold = 300  # 5 minutes

            models_to_unload = []

            for model_id, instance in self._loaded_models.items():
                # Skip if model has active sessions
                if instance.active_sessions:
                    continue

                # Check last used time
                if instance.last_used:
                    last_used = datetime.fromisoformat(
                        instance.last_used.replace("Z", "+00:00")
                    )
                    if (now - last_used).total_seconds() > unused_threshold:
                        models_to_unload.append(model_id)
                elif instance.loaded_at:
                    # Never used, check load time
                    loaded_at = datetime.fromisoformat(
                        instance.loaded_at.replace("Z", "+00:00")
                    )
                    if (now - loaded_at).total_seconds() > unused_threshold:
                        models_to_unload.append(model_id)

            # Unload unused models
            for model_id in models_to_unload:
                await self.unload_model(model_id)
                logger.info(f"Unloaded unused model: {model_id}")

        except Exception as e:
            logger.error(f"Failed to unload unused models: {e}")

    async def _model_manager_loop(self) -> None:
        """Manage model lifecycle and optimization"""
        while self._running:
            try:
                await self._optimize_model_loading()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Model manager loop error: {e}")
                await asyncio.sleep(10)

    async def _optimize_model_loading(self) -> None:
        """Optimize model loading based on usage patterns"""
        try:
            # Analyze task patterns and preload frequently used models
            # This is a placeholder for more sophisticated optimization
            pass

        except Exception as e:
            logger.error(f"Failed to optimize model loading: {e}")

    async def get_health(self) -> Dict[str, Any]:
        """Get health status of model manager"""
        try:
            memory = psutil.virtual_memory()

            return {
                "status": "healthy" if self._running else "stopped",
                "available_models": len(self._available_models),
                "loaded_models": len(self._loaded_models),
                "active_tasks": len(
                    [
                        t
                        for t in self._parallel_tasks.values()
                        if t.started_at and not t.completed_at
                    ]
                ),
                "total_tasks": len(self._parallel_tasks),
                "system_resources": {
                    "memory_percent": memory.percent,
                    "available_ports": len(self._port_pool),
                    "used_ports": len(self._used_ports),
                },
                "model_details": {
                    model_id: {
                        "status": instance.status.value,
                        "active_sessions": len(instance.active_sessions),
                        "total_requests": instance.total_requests,
                        "total_tokens": instance.total_tokens,
                    }
                    for model_id, instance in self._loaded_models.items()
                },
            }

        except Exception as e:
            logger.error(f"Failed to get model manager health: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_agent_event(self, message) -> None:
        """Handle agent coordination events"""
        try:
            event_type = message.event_type
            data = message.payload

            if event_type == "agent.capability_request":
                # Handle requests for model management capabilities
                if "model_management" in data.get("capabilities", []):
                    await self._handle_model_management_request(data)
            elif event_type == "parallel_inference.request":
                # Handle parallel inference requests from other agents
                await self._handle_parallel_inference_request(data)

        except Exception as e:
            logger.error(f"Failed to handle agent event: {e}")

    async def _handle_model_management_request(self, data: Dict[str, Any]) -> None:
        """Handle model management requests from other agents"""
        try:
            request_type = data.get("request_type")

            if request_type == "load_model":
                model_id = data.get("model_id")
                if model_id:
                    await self.load_model(model_id)
            elif request_type == "unload_model":
                model_id = data.get("model_id")
                if model_id:
                    await self.unload_model(model_id)
            elif request_type == "list_models":
                # Return available models
                models_info = {
                    model_id: spec.to_dict()
                    for model_id, spec in self._available_models.items()
                }
                logger.debug(
                    "Model list requested; %s models available",
                    len(models_info),
                )
                # Send response (implementation depends on communication system)

        except Exception as e:
            logger.error(f"Failed to handle model management request: {e}")

    async def _handle_parallel_inference_request(self, data: Dict[str, Any]) -> None:
        """Handle parallel inference requests from other agents"""
        try:
            prompt = data.get("prompt")
            if not prompt:
                return

            # Submit parallel task
            task_id = await self.submit_parallel_task(
                prompt=prompt,
                model_requirements=data.get("model_requirements", []),
                parallel_count=data.get("parallel_count", 3),
                consensus_required=data.get("consensus_required", True),
                preferred_models=data.get("preferred_models", []),
                **data.get("options", {}),
            )

            # Send task ID back to requesting agent
            # (implementation depends on communication system)
            logger.debug("Submitted parallel inference task %s", task_id)

        except Exception as e:
            logger.error(f"Failed to handle parallel inference request: {e}")

    # Public API methods for integration with Guild system

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available models"""
        return {
            model_id: spec.to_dict()
            for model_id, spec in self._available_models.items()
        }

    def get_loaded_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of loaded models"""
        return {
            model_id: instance.to_dict()
            for model_id, instance in self._loaded_models.items()
        }

    def get_parallel_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get list of parallel tasks"""
        return {
            task_id: task.to_dict() for task_id, task in self._parallel_tasks.items()
        }

    async def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up completed tasks older than specified age"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

            tasks_to_remove = []
            for task_id, task in self._parallel_tasks.items():
                if (
                    task.completed_at
                    and datetime.fromisoformat(task.completed_at.replace("Z", "+00:00"))
                    < cutoff_time
                ):
                    tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del self._parallel_tasks[task_id]

            logger.info(f"Cleaned up {len(tasks_to_remove)} completed tasks")
            return len(tasks_to_remove)

        except Exception as e:
            logger.error(f"Failed to cleanup completed tasks: {e}")
            return 0
