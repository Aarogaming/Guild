# Guild System - Unified Task Management & Orchestration

The Guild system is AAS's next-generation unified task management and orchestration platform. It consolidates previously scattered functionality into a cohesive, dedicated sub-module for autonomous task execution and agent cooperation.

## Architecture Overview

The Guild system consists of five core components:

```
Guild/
├── core.py                 # Central orchestration hub
├── task_director.py        # Unified task lifecycle management
├── agent_coordinator.py    # Multi-agent coordination system
├── batch_orchestrator.py   # Intelligent batch processing
├── workspace_director.py   # Workspace and directory management
├── communication_hub.py    # Inter-module communication
├── model_manager.py        # Local LM Studio model management
├── integration.py          # Legacy system integration
├── agents/                 # Specialized agents
│   └── parallel_inference_agent.py  # Multi-model inference agent
└── examples/               # Usage examples and demos
    └── local_model_integration.py   # Model management examples
```

## Module Contracts

Guild is wired as an AAS first-class module with explicit contracts:

1. Module manifest: `guild/aas-module.json`
2. Hive communication policy: `guild/aas-hive.json`
3. Hub I/O protocol: `guild/protocols/HUB_IO_NETWORK.md`
4. Local plugin allowance: `guild/plugins/`

## Key Features

### 🎯 **Unified Task Management**
- **Centralized Task Board**: Single source of truth for all tasks
- **Dependency Resolution**: Automatic blocking/unblocking based on dependencies
- **Priority-Based Routing**: Intelligent task assignment based on priority and capabilities
- **Real-time Status Tracking**: Live updates across all systems

### 🤝 **Advanced Agent Coordination**
- **Capability-Based Routing**: Tasks routed to agents with required capabilities
- **Load Balancing**: Automatic workload distribution across agents
- **Cooperation Requests**: Peer review, knowledge sharing, task handoff
- **Health Monitoring**: Heartbeat tracking and automatic failover

### 🚀 **Intelligent Batch Processing**
- **Auto-Batching**: Automatic grouping of similar tasks for cost optimization
- **50% Cost Savings**: Integration with OpenAI Batch API
- **Priority Scheduling**: Urgent tasks processed immediately
- **Result Distribution**: Automatic processing and distribution of batch results

### 🤖 **Resource-Aware Model Management**
- **Local Model Preference**: Automatically prefer local models when system resources are available
- **Dynamic Fallback**: Switch to remote/cloud models when local resources are constrained
- **Real-time Resource Monitoring**: Monitor CPU, memory, GPU usage in real-time
- **Cost Optimization**: Intelligent routing to minimize API costs while maintaining performance
- **Configurable Thresholds**: Customize resource thresholds for different routing strategies
- **Multi-Provider Support**: Support for OpenAI, Anthropic, Google, and custom endpoints

### 🤖 **Local Model Management**
- **LM Studio Integration**: Seamless integration with LM Studio for local model hosting
- **Parallel Inference**: Execute prompts across multiple models simultaneously
- **Consensus Generation**: Aggregate results from multiple models for higher accuracy
- **Dynamic Model Loading**: Automatic model loading/unloading based on demand
- **Resource Optimization**: Intelligent resource management and model selection
### 🏗️ **Workspace Management**
- **Health Monitoring**: Comprehensive workspace health scoring
- **Automated Cleanup**: Duplicate removal, temp file cleanup, log compression
- **Directory Organization**: Intelligent file organization and defragmentation
- **Storage Optimization**: Automatic archival and compression

### 📡 **Enhanced Communication**
- **Multi-Channel Messaging**: Dedicated channels for different event types
- **Priority-Based Routing**: Urgent messages processed immediately
- **Event History**: Complete audit trail of all communications
- **Cross-System Bridging**: Seamless integration with existing systems

## Quick Start

### 1. Basic Integration

```python
from core.managers_enhanced import EnhancedManagerHub

# Create enhanced hub with Guild system
hub = EnhancedManagerHub.create(enable_guild=True)

# Initialize Guild system
await hub.initialize_guild()

# Use unified API
task = await hub.tasks.claim_task(agent_id="my_agent")
batch_id = await hub.batch_manager.submit_batch(task_ids, "Analysis batch")
```

### 2. Direct Guild Usage

```python
from Guild.core import GuildCore, GuildConfig

# Configure Guild system
config = GuildConfig(
    task_board_path="guild/ACTIVE_TASKS.md",
    artifact_dir="artifacts/guild",
    enable_auto_batching=True,
    enable_workspace_monitoring=True
)

# Initialize Guild
guild = GuildCore(config=config)
await guild.start()

# Use Guild directly
task = await guild.claim_task("agent_id")
await guild.complete_task("task_id", "agent_id", {"result": "success"})
```

### 3. Agent Registration

```python
# Register an agent with capabilities
await hub.agent_coordinator.register_agent(
    agent_id="code_generator",
    name="Code Generation Agent",
    capabilities=["code_generation", "testing", "documentation"],
    max_concurrent_tasks=5
)

# Request cooperation between agents
request_id = await hub.agent_coordinator.request_cooperation(
    requesting_agent="agent_1",
    request_type="peer_review",
    payload={"code": "...", "task_id": "AAS-123"},
    target_agent="agent_2"
)
```

## Migration from Legacy Systems

The Guild system provides seamless migration from existing AAS components:

### Phase 1: Hybrid Mode (Default)
- Guild system runs alongside existing systems
- Automatic bridging between old and new components
- Gradual migration of functionality

### Phase 2: Guild-Primary Mode
- Most operations route through Guild system
- Legacy systems provide fallback support
- Enhanced features available

### Phase 3: Guild-Only Mode
- Complete migration to Guild system
- Legacy systems deprecated
- Full feature set available

### Migration Commands

```python
# Check current integration status
health = await hub.get_system_health()
print(f"Status: {health['overall_status']}")

# Migrate existing data to Guild
success = await hub.migrate_to_guild()

# Switch to Guild-only mode
await hub._guild_integration.set_integration_mode("guild_only")
```

## Configuration

### Guild Configuration Options

```python
from Guild.core import GuildConfig

config = GuildConfig(
    # Task management
    task_board_path="guild/ACTIVE_TASKS.md",
    max_concurrent_tasks=10,

    # Batch processing
    batch_size=20,
    enable_auto_batching=True,

    # Model management
    enable_model_management=True,
    lm_studio_host="localhost",
    lm_studio_base_port=1234,
    max_parallel_models=5,

    # Monitoring
    heartbeat_interval=30,  # seconds
    enable_workspace_monitoring=True,

    # Storage
    artifact_dir="artifacts/guild"
)
```

### Environment Variables

```bash
# Guild system configuration
GUILD_ENABLED=true
GUILD_TASK_BOARD_PATH=guild/ACTIVE_TASKS.md
GUILD_ARTIFACT_DIR=artifacts/guild
GUILD_AUTO_BATCH=true
GUILD_BATCH_SIZE=20
GUILD_HEARTBEAT_INTERVAL=30

# Integration mode
GUILD_INTEGRATION_MODE=hybrid  # hybrid, guild_only, legacy_only
```

## API Reference

### Task Management

```python
# Create a task
task_id = await guild.task_director.create_task(
    title="Implement feature X",
    description="Add new functionality...",
    priority=TaskPriority.HIGH,
    dependencies=["AAS-001", "AAS-002"],
    capabilities_required=["code_generation", "testing"]
)

# Claim a task
task = await guild.task_director.claim_task(
    agent_id="my_agent",
    task_id="AAS-123"  # Optional, finds next available if None
)

# Complete a task
success = await guild.task_director.complete_task(
    task_id="AAS-123",
    agent_id="my_agent",
    result={"implementation": "...", "tests": "..."}
)
```

### Agent Coordination

```python
# Register agent
await guild.agent_coordinator.register_agent(
    agent_id="specialist_agent",
    name="Specialist Agent",
    capabilities=["specialized_task", "code_review"],
    max_concurrent_tasks=3
)

# Find capable agents
agents = await guild.agent_coordinator.find_capable_agents(
    required_capabilities=["code_generation", "testing"],
    exclude_overloaded=True
)

# Request cooperation
request_id = await guild.agent_coordinator.request_cooperation(
    requesting_agent="agent_1",
    request_type="knowledge_share",
    payload={"topic": "best_practices", "context": "..."},
    timeout_minutes=30
)
```

### Batch Processing

```python
# Submit batch
batch_id = await guild.batch_orchestrator.submit_batch(
    task_ids=["AAS-001", "AAS-002", "AAS-003"],
    description="Code generation batch",
    batch_type=BatchType.CODE_GENERATION,
    priority="high"
)

# Add task to pending batch queue
await guild.batch_orchestrator.add_task_to_pending("AAS-004")

# Check auto-batch status
await guild.batch_orchestrator.check_auto_batch()
```

### Resource-Aware Model Selection

```python
from Guild.core import GuildCore, GuildConfig

# Configure with resource awareness
config = GuildConfig(
    enable_model_management=True,
    enable_resource_awareness=True,
    cpu_threshold_high=70.0,      # Switch to remote when CPU > 70%
    memory_threshold_high=75.0,   # Switch to remote when Memory > 75%
    cost_optimization_enabled=True
)

guild = GuildCore(config=config)
await guild.start()

# Submit task - automatically routes based on current system resources
task_id = await guild.submit_parallel_inference(
    prompt="Analyze this complex dataset",
    model_requirements=["analysis", "reasoning"],
    parallel_count=3,
    consensus_required=True
)

# Get cost analysis
if hasattr(guild.model_manager, 'get_cost_analysis'):
    cost_analysis = guild.model_manager.get_cost_analysis()
    print(f"Total cost: ${cost_analysis['total_cost']:.4f}")
    print(f"Local vs Remote: {cost_analysis['local_percentage']:.1f}% / {cost_analysis['remote_percentage']:.1f}%")
```

### Configure Remote Endpoints

```python
# Add custom remote endpoint
await guild.model_manager.add_remote_endpoint({
    "id": "custom_llm",
    "name": "Custom LLM Service",
    "endpoint_url": "https://api.custom-llm.com/v1/chat/completions",
    "cost_per_token": 0.00001,
    "capabilities": ["text_generation", "reasoning"]
})

# Update resource thresholds
await guild.model_manager.set_resource_thresholds({
    "high": {
        "cpu_max": 80.0,
        "memory_max": 85.0,
        "strategy": "remote_preferred"
    }
})
```

### Model Management

```python
# Load a local model
success = await guild.load_model("microsoft/DialoGPT-medium")

# Submit parallel inference across multiple models
task_id = await guild.submit_parallel_inference(
    prompt="Explain quantum computing in simple terms",
    model_requirements=["text_generation"],
    parallel_count=3,
    consensus_required=True
)

# Get inference results with consensus
result = await guild.get_inference_result(task_id)
if result and result.get("consensus"):
    print(f"Consensus: {result['consensus']['consensus_text']}")
    print(f"Confidence: {result['consensus']['confidence']}")

# Get available and loaded models
available = guild.get_available_models()
loaded = guild.get_loaded_models()
```

### Parallel Inference Agent

```python
from Guild.agents.parallel_inference_agent import ParallelInferenceAgent

# Create specialized inference agent
inference_agent = ParallelInferenceAgent(guild)
await inference_agent.start()

# Submit inference request
request_id = await inference_agent.submit_inference_request(
    prompt="Write a Python function for quicksort",
    model_requirements=["code_generation"],
    parallel_count=4,
    consensus_required=True,
    preferred_models=["codellama", "deepseek-coder"]
)

# Monitor request status
status = await inference_agent.get_request_status(request_id)
```

```python
### Communication

```python
# Subscribe to events
guild.communication_hub.subscribe(
    CommunicationChannel.TASK_UPDATES,
    my_event_handler
)

# Emit event
await guild.communication_hub.emit_event(
    event_type="custom.event",
    data={"key": "value"},
    channel=CommunicationChannel.SYSTEM_ALERTS,
    priority=MessagePriority.HIGH
)

# Send direct message
message = Message(
    id="msg-123",
    channel=CommunicationChannel.AGENT_COORDINATION,
    event_type="agent.request",
    source="agent_1",
    target="agent_2",
    priority=MessagePriority.NORMAL,
    payload={"request": "help"}
)
await guild.communication_hub.send_message(message)
```

## Event System

The Guild system uses a comprehensive event system for communication:

### Event Channels
- `TASK_UPDATES`: Task lifecycle events
- `AGENT_COORDINATION`: Agent cooperation and coordination
- `BATCH_PROCESSING`: Batch job status and results
- `WORKSPACE_EVENTS`: Workspace health and cleanup
- `SYSTEM_ALERTS`: System-wide notifications
- `IPC_BRIDGE`: Cross-process communication

### Event Types
- `task.created`, `task.claimed`, `task.completed`, `task.failed`
- `agent.registered`, `agent.status_changed`, `agent.heartbeat`
- `batch.created`, `batch.submitted`, `batch.completed`
- `workspace.health_check`, `workspace.cleanup_completed`
- `cooperation.request`, `cooperation.response`

### Event Handling

```python
async def handle_task_event(message):
    event_type = message.event_type
    data = message.payload

    if event_type == "task.completed":
        print(f"Task {data['task_id']} completed by {data['agent_id']}")
    elif event_type == "task.failed":
        print(f"Task {data['task_id']} failed: {data['error']}")

# Subscribe to events
guild.communication_hub.subscribe(
    CommunicationChannel.TASK_UPDATES,
    handle_task_event
)
```

## Monitoring and Health

### System Health

```python
# Get comprehensive health status
health = await guild.get_health_status()

# Example response:
{
    "core": {"status": "healthy"},
    "task_director": {
        "status": "healthy",
        "total_tasks": 150,
        "by_status": {
            "queued": 45,
            "in_progress": 12,
            "done": 93
        }
    },
    "agent_coordinator": {
        "status": "healthy",
        "total_agents": 8,
        "by_status": {
            "idle": 3,
            "busy": 4,
            "offline": 1
        }
    },
    "batch_orchestrator": {
        "status": "healthy",
        "pending_tasks": 23,
        "active_batches": 2
    },
    "workspace_director": {
        "status": "healthy",
        "health_score": 87.5,
        "health_status": "good"
    }
}
```

### Metrics and Analytics

```python
# Get workspace metrics
metrics = guild.workspace_director._current_metrics
print(f"Health Score: {metrics.health_score}")
print(f"Recommendations: {metrics.recommendations}")

# Get task metrics
task_health = await guild.task_director.get_health()
print(f"Active tasks: {task_health['by_status']['in_progress']}")

# Get agent metrics
agent_health = await guild.agent_coordinator.get_health()
print(f"Active agents: {agent_health['by_status']['idle'] + agent_health['by_status']['busy']}")
```

## Best Practices

### 1. Task Design
- **Clear Dependencies**: Always specify task dependencies explicitly
- **Capability Requirements**: Define required capabilities for proper routing
- **Descriptive Titles**: Use clear, actionable task titles
- **Reasonable Scope**: Keep tasks focused and achievable

### 2. Agent Development
- **Capability Declaration**: Accurately declare agent capabilities
- **Heartbeat Maintenance**: Send regular heartbeats for health monitoring
- **Error Handling**: Implement robust error handling and reporting
- **Cooperation**: Use cooperation requests for complex workflows

### 3. Batch Optimization
- **Similar Tasks**: Group similar tasks for better batch efficiency
- **Priority Management**: Use appropriate priorities for time-sensitive tasks
- **Cost Monitoring**: Monitor batch costs and optimize grouping
- **Result Processing**: Implement proper result handling

### 4. Workspace Management
- **Regular Cleanup**: Allow automatic cleanup to maintain health
- **Directory Structure**: Follow standard directory organization
- **File Naming**: Use consistent naming conventions
- **Size Monitoring**: Monitor workspace size and growth

## Troubleshooting

### Common Issues

#### Guild System Not Starting
```python
# Check configuration
config = GuildConfig()
print(f"Task board path: {config.task_board_path}")
print(f"Artifact dir: {config.artifact_dir}")

# Check permissions
import os
os.makedirs(config.artifact_dir, exist_ok=True)
```

#### Tasks Not Being Claimed
```python
# Check agent registration
agents = await guild.agent_coordinator.find_capable_agents(["required_capability"])
print(f"Available agents: {agents}")

# Check task dependencies
task = guild.task_director._tasks.get("AAS-123")
if task:
    deps_met = await guild.task_director._are_dependencies_met(task)
    print(f"Dependencies met: {deps_met}")
```

#### Batch Jobs Not Processing
```python
# Check batch orchestrator health
health = await guild.batch_orchestrator.get_health()
print(f"Batch health: {health}")

# Check pending tasks
print(f"Pending tasks: {len(guild.batch_orchestrator._pending_tasks)}")
```

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger("Guild").setLevel(logging.DEBUG)

# Get detailed health information
health = await guild.get_health_status()
print(json.dumps(health, indent=2))
```

## Contributing

### Development Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
pytest Guild/tests/
```

3. Code style:
```bash
black Guild/
flake8 Guild/
```

### Adding New Features

1. **New Event Types**: Add to `communication_hub.py`
2. **New Capabilities**: Add to `agent_coordinator.py`
3. **New Batch Types**: Add to `batch_orchestrator.py`
4. **New Cleanup Actions**: Add to `workspace_director.py`

### Testing

```python
# Unit tests
pytest Guild/tests/test_task_director.py

# Integration tests
pytest Guild/tests/test_integration.py

# Performance tests
pytest Guild/tests/test_performance.py
```

## Roadmap

### Version 2.1
- [ ] Advanced workflow orchestration
- [ ] Machine learning-based task routing
- [ ] Enhanced cooperation patterns
- [ ] Real-time dashboard

### Version 2.2
- [ ] Multi-tenant support
- [ ] Advanced analytics
- [ ] Plugin marketplace integration
- [ ] Mobile agent support

### Version 3.0
- [ ] Distributed Guild clusters
- [ ] Advanced AI integration
- [ ] Blockchain-based task verification
- [ ] Quantum-ready architecture

## Support

- **Documentation**: [Guild System Docs](docs/)
- **Issues**: [GitHub Issues](https://github.com/AaroneousAutomationSuite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AaroneousAutomationSuite/discussions)
- **Discord**: [AAS Community](https://discord.gg/aas-community)
