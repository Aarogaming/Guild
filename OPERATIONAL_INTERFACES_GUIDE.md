# 🎯 Guild System - Operational Interfaces Guide

## 📋 Overview

The Guild system provides three clean, efficient interfaces that abstract away the mystical complexity while preserving enhanced functionality and engagement features:

1. **Operational Interface** - Core system management
2. **Hub Integration Interface** - For AAS Hub integration
3. **Developer Interface** - For individual developers
4. **AI Agent Interface** - For AI agents to register and work

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Guild System Interfaces                  │
├─────────────────────────────────────────────────────────────┤
│  Hub Interface    │  Developer Interface  │  AI Agent Interface │
│  - Task submission │  - CLI commands      │  - Agent registration │
│  - Batch operations│  - Personal tasks    │  - Task processing    │
│  - Analytics       │  - Quick helpers     │  - Progress reporting │
│  - Monitoring      │  - Configuration     │  - Performance tracking│
├─────────────────────────────────────────────────────────────┤
│                 Operational Interface                       │
│  - Task management    │  - Agent coordination               │
│  - Resource routing   │  - Performance tracking             │
│  - Intelligent assignment │  - System monitoring           │
├─────────────────────────────────────────────────────────────┤
│              Core Guild System (Background)                 │
│  - Resource-aware routing  │  - Mystical enhancements      │
│  - Neural orchestration    │  - Quest system (optional)    │
│  - Performance optimization│  - Artifact crafting (optional)│
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Operational Interface

**File**: `Guild/interfaces/operational_interface.py`

The core interface that provides clean task management without mystical complexity.

### Key Features

- **Simple Task Creation**: Clean API for submitting work requests
- **Intelligent Agent Assignment**: Resource-aware routing and capability matching
- **Performance Tracking**: Completion stats and agent performance metrics
- **Resource Management**: CPU/memory monitoring with local/remote model routing
- **Background Mystical Enhancement**: Optional magical features run transparently

### Usage Example

```python
from Guild.interfaces.operational_interface import create_operational_guild

# Create and start the guild
guild = await create_operational_guild(enable_mystical=True)

# Submit a task
result = await guild.submit_work_request(
    title="Implement user authentication",
    description="Create JWT-based auth system",
    priority="high",
    capabilities=["code", "test"],
    estimated_minutes=120
)

# Check status
status = await guild.check_work_status(result["task_id"])
print(f"Task status: {status['status']}")

# Get system dashboard
dashboard = await guild.get_system_status()
print(f"Active tasks: {dashboard['tasks']['active']}")
```

### API Methods

- `submit_work_request()` - Submit new tasks
- `check_work_status()` - Check task progress
- `get_system_status()` - System health and metrics
- `register_agent()` - Register new AI agents
- `get_available_agents()` - Find suitable agents
- `auto_assign_task()` - Intelligent task assignment

## 🏢 Hub Integration Interface

**File**: `Guild/examples/hub_integration_example.py`

Specialized interface for AAS Hub integration with batch operations and analytics.

### Key Features

- **AAS-Specific Agents**: Pre-configured agents for AAS workflows
- **Task Type Mapping**: Automatic capability mapping for AAS task types
- **Batch Operations**: Submit and monitor multiple tasks
- **Performance Analytics**: Detailed metrics and reporting
- **Priority Assignment**: Urgent task handling

### Usage Example

```python
from Guild.examples.hub_integration_example import AASHubGuildIntegration

# Initialize hub integration
hub = AASHubGuildIntegration()
await hub.initialize()

# Submit development task
result = await hub.submit_development_task("hub_task_001", {
    "title": "Fix authentication bug",
    "description": "Resolve JWT token validation issue",
    "type": "bug_fix",
    "priority": "urgent",
    "estimated_minutes": 90
})

# Get system dashboard
dashboard = await hub.get_system_dashboard()

# Submit batch tasks
batch_result = await hub.submit_batch_tasks([
    {"title": "Task 1", "type": "code_generation"},
    {"title": "Task 2", "type": "testing"},
    {"title": "Task 3", "type": "documentation"}
])
```

### Hub-Specific Features

- **AAS Task Types**: `code_generation`, `bug_fix`, `optimization`, `testing`, etc.
- **Agent Recommendations**: Get best agents for specific task types
- **Batch Processing**: Handle multiple related tasks efficiently
- **Performance Analytics**: Historical data and trend analysis
- **Resource Monitoring**: System health and capacity planning

## 👨‍💻 Developer Interface

**File**: `Guild/interfaces/developer_interface.py`

Personal interface for individual developers with CLI and configuration support.

### Key Features

- **CLI Commands**: Full command-line interface for task management
- **Personal Configuration**: Customizable preferences and defaults
- **Quick Helpers**: Shortcuts for common development tasks
- **Task Recommendations**: Personalized task suggestions
- **Performance Insights**: Individual productivity metrics

### CLI Usage

```bash
# Create a task
guild create "Fix login bug" -d "JWT validation issue" -p urgent -t debug

# List tasks
guild list --status pending

# Show task details
guild show task_001

# Quick task creation
guild quick code "Implement user registration API"
guild quick review src/auth.py
guild quick debug "Memory leak in data processor"

# Show dashboard
guild dashboard

# List agents
guild agents --available

# Get recommendations
guild recommend -t optimization
```

### Python API Usage

```python
from Guild.interfaces.developer_interface import DeveloperGuildInterface

# Initialize developer interface
dev = DeveloperGuildInterface()
await dev.initialize()

# Create tasks with shortcuts
task_id = await dev.quick_code_task(
    "Implement OAuth integration",
    priority="high"
)

# Batch file reviews
task_ids = await dev.batch_file_review([
    "src/auth.py",
    "src/user.py",
    "src/session.py"
])

# Show personal dashboard
await dev.show_dashboard()
```

### Developer Features

- **Personal Config**: Stored in `~/.guild_config.json`
- **Quick Commands**: `quick_code_task()`, `quick_review_task()`, `quick_debug_task()`
- **Batch Operations**: Review multiple files, create related tasks
- **Customization**: Default priorities, preferred agents, notification settings

## 🤖 AI Agent Interface

**File**: `Guild/interfaces/ai_agent_interface.py`

Interface for AI agents to register, receive tasks, and report progress.

### Key Features

- **Agent Registration**: Declare capabilities and specializations
- **Task Processing**: Receive and handle assigned tasks
- **Progress Reporting**: Real-time progress updates
- **Performance Tracking**: Success rates and completion times
- **Resource Management**: Load balancing and capacity management

### Usage Example

```python
from Guild.interfaces.ai_agent_interface import AIAgentInterface, AgentCapabilities, AgentCapability

# Create agent
agent = AIAgentInterface("Code Generation Specialist")

# Connect to guild
await agent.connect_to_guild(guild)

# Register capabilities
capabilities = AgentCapabilities(
    primary_skills=[AgentCapability.CODE_GENERATION],
    secondary_skills=[AgentCapability.DOCUMENTATION],
    specializations=["Python", "JavaScript", "API Development"],
    performance_metrics={"base_rating": 0.9},
    max_concurrent_tasks=3
)

await agent.register_capabilities(capabilities)

# Register task handler
async def handle_code_generation(task):
    # Process the task
    await agent.report_task_progress(task.id, TaskProgress(
        task_id=task.id,
        progress_percentage=50.0,
        status_message="Generating code..."
    ))

    # Return result
    return "Generated code here..."

agent.register_task_handler(AgentCapability.CODE_GENERATION, handle_code_generation)

# Start agent
await agent.start()
```

### Agent Features

- **Capability Declaration**: Primary/secondary skills and specializations
- **Task Handlers**: Register functions for different capability types
- **Progress Reporting**: Real-time updates with percentage and status
- **Performance Metrics**: Automatic tracking of success rates and timing
- **Load Management**: Respect concurrent task limits

## 🔧 Configuration

### Operational Interface Config

```python
# Enable/disable mystical features
guild = await create_operational_guild(enable_mystical=True)

# Resource thresholds
config = {
    "cpu_threshold_high": 70.0,
    "memory_threshold_high": 75.0,
    "prefer_local_models": True
}
```

### Developer Interface Config

```json
{
  "developer_name": "John Developer",
  "preferred_agents": ["Code Specialist", "Debug Expert"],
  "default_priority": "normal",
  "enable_mystical_features": true,
  "auto_assign_tasks": true,
  "notification_preferences": {
    "task_completion": true,
    "agent_assignments": true,
    "system_alerts": false
  }
}
```

### Hub Integration Config

```python
# Initialize with AAS-specific settings
hub = AASHubGuildIntegration()
await hub.initialize(enable_mystical_background=True)

# Configure batch processing
batch_config = {
    "max_batch_size": 50,
    "batch_timeout": 3600,
    "priority_escalation": True
}
```

## 📊 Monitoring and Analytics

### System Health Monitoring

```python
# Get comprehensive system status
status = await guild.get_system_status()

print(f"System Health: {status['system_running']}")
print(f"Active Tasks: {status['tasks']['active']}")
print(f"Available Agents: {status['agents']['available']}")
print(f"CPU Usage: {status['resources']['cpu_usage']:.1f}%")
print(f"Memory Usage: {status['resources']['memory_usage']:.1f}%")

# Mystical enhancements (if enabled)
if status.get('mystical_status'):
    mystical = status['mystical_status']
    print(f"Magical Agents: {mystical['magical_agents']}")
    print(f"Guild Mana: {mystical['guild_mana_pool']}")
    print(f"Active Spells: {mystical['active_spells']}")
```

### Performance Analytics

```python
# Get performance metrics
analytics = await hub.get_performance_analytics("24h")

print(f"Tasks Completed: {analytics['task_completion']['total_completed']}")
print(f"Average Time: {analytics['task_completion']['average_completion_time']:.1f} min")
print(f"Success Rate: {analytics['task_completion']['success_rate'] * 100:.1f}%")

# Agent performance
for agent_id, stats in analytics['agent_performance'].items():
    print(f"Agent {agent_id}: {stats['completed']} tasks completed")
```

## 🚀 Getting Started

### 1. Basic Setup

```python
# Create operational guild
from Guild.interfaces.operational_interface import create_operational_guild

guild = await create_operational_guild(enable_mystical=True)

# Submit a task
result = await guild.submit_work_request(
    "Create REST API endpoint",
    "Implement user management API with CRUD operations",
    "normal",
    ["code", "test"],
    90
)

print(f"Task submitted: {result['task_id']}")
```

### 2. Hub Integration

```python
# Initialize hub integration
from Guild.examples.hub_integration_example import AASHubGuildIntegration

hub = AASHubGuildIntegration()
await hub.initialize()

# Submit AAS-specific task
result = await hub.submit_development_task("aas_task_001", {
    "title": "Optimize database queries",
    "type": "optimization",
    "priority": "high"
})
```

### 3. Developer CLI

```bash
# Install and configure
pip install -e Guild/

# Configure developer settings
guild config -k developer_name -v "Your Name"
guild config -k default_priority -v "normal"

# Create tasks
guild create "Fix authentication bug" -p urgent -t debug
guild quick code "Add user profile endpoint"

# Monitor progress
guild dashboard
guild mytasks
```

### 4. AI Agent Registration

```python
# Create and register an AI agent
from Guild.interfaces.ai_agent_interface import create_ai_agent, AgentCapability

agent = await create_ai_agent(
    "Python Code Generator",
    primary_skills=[AgentCapability.CODE_GENERATION, AgentCapability.TESTING],
    specializations=["Python", "FastAPI", "Database Integration"],
    guild=guild
)

await agent.start()
```

## 🎯 Best Practices

### For Hub Integration

1. **Use Batch Operations**: Submit related tasks together for better resource utilization
2. **Monitor System Health**: Check dashboard regularly for capacity planning
3. **Set Appropriate Priorities**: Use urgent/critical sparingly for true emergencies
4. **Track Performance**: Use analytics to optimize task allocation

### For Developers

1. **Use Quick Commands**: Leverage shortcuts for common tasks
2. **Configure Preferences**: Set up personal defaults and preferred agents
3. **Monitor Your Tasks**: Use `guild mytasks` to track personal work
4. **Provide Good Descriptions**: Help agents understand requirements clearly

### For AI Agents

1. **Declare Accurate Capabilities**: Be specific about what you can handle
2. **Report Progress Regularly**: Keep users informed of task status
3. **Handle Errors Gracefully**: Report failures with useful error messages
4. **Respect Resource Limits**: Don't exceed concurrent task limits

## 🔮 Mystical Features (Optional)

When mystical features are enabled, the system provides enhanced engagement through:

- **Background Magic**: Spells and enchantments run transparently
- **Performance Dragons**: Distributed computing with fantasy flair
- **Quest System**: Tasks become epic adventures with rewards
- **Artifact Crafting**: Create legendary tools through task completion
- **Divine Interventions**: Rare miraculous optimizations

These features enhance motivation and engagement without interfering with operational efficiency.

## 🎉 Summary

The Guild system's operational interfaces provide:

✅ **Clean, efficient APIs** for all user types
✅ **Resource-aware intelligent routing** for optimal performance
✅ **Comprehensive monitoring and analytics** for system health
✅ **Optional mystical enhancements** for engagement without complexity
✅ **Scalable architecture** supporting hub, developers, and AI agents

The system successfully balances practical functionality with engaging fantasy elements, making development work more enjoyable while maintaining professional efficiency.

---

*"The magic happens in the background - the interfaces stay clean and efficient."*
