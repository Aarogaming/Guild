"""
Resource-Aware Model Management Example

This example demonstrates how to use the Guild system with resource-aware
model management that automatically switches between local and remote models
based on system resource usage.
"""

import asyncio
import psutil
from Guild.core import GuildCore, GuildConfig
from Guild.advanced.resource_aware_model_manager import (
    ResourceThreshold,
    ModelRoutingStrategy,
)


async def demonstrate_resource_aware_management():
    """Demonstrate resource-aware model management"""

    print("🤖 Guild Resource-Aware Model Management Demo")
    print("=" * 50)

    # Configure Guild with resource awareness
    config = GuildConfig(
        enable_model_management=True,
        enable_resource_awareness=True,
        resource_check_interval=5,  # Check every 5 seconds
        cpu_threshold_high=70.0,
        memory_threshold_high=75.0,
        cost_optimization_enabled=True,
    )

    # Initialize Guild
    guild = GuildCore(config=config)
    await guild.start()

    try:
        print(f"✅ Guild started with resource-aware model management")

        # Show initial system resources
        await show_system_resources()

        # Show current routing strategy
        if guild.model_manager:
            status = guild.model_manager.get_resource_aware_status()
            print(f"📊 Current routing strategy: {status['current_strategy']}")
            print(f"📊 Resource threshold: {status['resource_threshold']}")

        # Submit some tasks to see resource-aware routing in action
        print("\n🚀 Submitting tasks to demonstrate resource-aware routing...")

        tasks = [
            "Explain quantum computing in simple terms",
            "Write a Python function for binary search",
            "Analyze the pros and cons of renewable energy",
            "Create a marketing strategy for a new product",
        ]

        task_ids = []
        for i, prompt in enumerate(tasks):
            print(f"\n📝 Task {i+1}: {prompt[:50]}...")

            task_id = await guild.submit_parallel_inference(
                prompt=prompt,
                model_requirements=["text_generation"],
                parallel_count=2,
                consensus_required=True,
            )

            if task_id:
                task_ids.append(task_id)
                print(f"✅ Task submitted: {task_id}")

                # Show which models were selected
                if guild.model_manager:
                    status = guild.model_manager.get_resource_aware_status()
                    recent_decisions = status.get("recent_routing_decisions", [])
                    if recent_decisions:
                        latest = recent_decisions[-1]
                        local_models = latest.get("local_models", [])
                        remote_models = latest.get("remote_models", [])
                        print(f"   📍 Local models: {local_models}")
                        print(f"   🌐 Remote models: {remote_models}")

            # Wait a bit between tasks
            await asyncio.sleep(2)

        # Wait for tasks to complete
        print("\n⏳ Waiting for tasks to complete...")
        await asyncio.sleep(10)

        # Show results
        print("\n📊 Task Results:")
        for task_id in task_ids:
            result = await guild.get_inference_result(task_id)
            if result:
                print(f"✅ Task {task_id}: {result.get('status', 'unknown')}")
                if result.get("consensus"):
                    confidence = result["consensus"].get("confidence", 0)
                    print(f"   🎯 Consensus confidence: {confidence:.2f}")

        # Show cost analysis
        if guild.model_manager and hasattr(guild.model_manager, "get_cost_analysis"):
            print("\n💰 Cost Analysis:")
            cost_analysis = guild.model_manager.get_cost_analysis()
            print(f"   Total cost: ${cost_analysis['total_cost']:.4f}")
            print(
                f"   Local cost: ${cost_analysis['local_cost']:.4f} ({cost_analysis['local_percentage']:.1f}%)"
            )
            print(
                f"   Remote cost: ${cost_analysis['remote_cost']:.4f} ({cost_analysis['remote_percentage']:.1f}%)"
            )

            recommendations = cost_analysis.get("recommendations", [])
            if recommendations:
                print("   💡 Recommendations:")
                for rec in recommendations:
                    print(f"      • {rec}")

        # Demonstrate resource threshold changes
        print("\n🔄 Demonstrating resource threshold simulation...")
        await simulate_resource_changes(guild)

    finally:
        await guild.stop()
        print("\n✅ Guild stopped")


async def show_system_resources():
    """Show current system resource usage"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    print(f"\n📊 Current System Resources:")
    print(f"   CPU: {cpu_percent:.1f}%")
    print(f"   Memory: {memory.percent:.1f}%")
    print(f"   Disk: {disk.percent:.1f}%")

    # Determine resource level
    overall_load = (cpu_percent + memory.percent) / 2
    if overall_load < 50:
        level = "LOW"
        emoji = "🟢"
    elif overall_load < 70:
        level = "MODERATE"
        emoji = "🟡"
    elif overall_load < 85:
        level = "HIGH"
        emoji = "🟠"
    else:
        level = "CRITICAL"
        emoji = "🔴"

    print(f"   Overall Load: {overall_load:.1f}% {emoji} ({level})")


async def simulate_resource_changes(guild):
    """Simulate different resource scenarios"""

    if not guild.model_manager or not hasattr(guild.model_manager, "current_strategy"):
        print("   ⚠️  Resource-aware model manager not available")
        return

    print("   🎭 Simulating different resource scenarios...")

    scenarios = [
        {
            "name": "Low Resource Usage",
            "description": "System has plenty of resources - prefer local models",
            "expected_strategy": ModelRoutingStrategy.LOCAL_PREFERRED,
        },
        {
            "name": "High Resource Usage",
            "description": "System is under load - prefer remote models",
            "expected_strategy": ModelRoutingStrategy.REMOTE_PREFERRED,
        },
        {
            "name": "Balanced Usage",
            "description": "Moderate resource usage - balance local and remote",
            "expected_strategy": ModelRoutingStrategy.BALANCED,
        },
    ]

    for scenario in scenarios:
        print(f"\n   📋 Scenario: {scenario['name']}")
        print(f"      {scenario['description']}")

        # In a real implementation, we might temporarily modify resource thresholds
        # or inject mock resource metrics to demonstrate different strategies

        current_strategy = guild.model_manager.current_strategy
        print(f"      Current strategy: {current_strategy.value}")

        # Submit a test task
        test_task_id = await guild.submit_parallel_inference(
            prompt="Test prompt for resource scenario",
            model_requirements=["text_generation"],
            parallel_count=1,
            consensus_required=False,
        )

        if test_task_id:
            print(f"      ✅ Test task submitted: {test_task_id}")

        await asyncio.sleep(3)


async def configure_remote_endpoints_example():
    """Example of configuring remote model endpoints"""

    config = GuildConfig(
        enable_model_management=True,
        enable_resource_awareness=True,
        openai_api_key="your-openai-api-key",  # Set your actual API keys
        anthropic_api_key="your-anthropic-api-key",
        google_api_key="your-google-api-key",
    )

    guild = GuildCore(config=config)
    await guild.start()

    try:
        if guild.model_manager and hasattr(guild.model_manager, "add_remote_endpoint"):
            # Add custom remote endpoint
            custom_endpoint = {
                "id": "custom_llm",
                "name": "Custom LLM Service",
                "endpoint_url": "https://api.custom-llm.com/v1/chat/completions",
                "api_key": "your-custom-api-key",
                "model_name": "custom-model-v1",
                "cost_per_token": 0.00001,
                "capabilities": ["text_generation", "reasoning"],
            }

            success = await guild.model_manager.add_remote_endpoint(custom_endpoint)
            if success:
                print("✅ Custom remote endpoint added successfully")

            # Show all available endpoints
            status = guild.model_manager.get_resource_aware_status()
            print(f"📡 Total remote endpoints: {status['remote_endpoints']}")

    finally:
        await guild.stop()


async def cost_optimization_example():
    """Example of cost optimization features"""

    config = GuildConfig(
        enable_model_management=True,
        enable_resource_awareness=True,
        cost_optimization_enabled=True,
    )

    guild = GuildCore(config=config)
    await guild.start()

    try:
        print("💰 Cost Optimization Example")
        print("=" * 30)

        # Submit tasks with cost optimization
        cost_sensitive_tasks = [
            "Simple question that can be handled by smaller models",
            "Complex analysis requiring advanced reasoning",
            "Code generation task",
            "Creative writing prompt",
        ]

        for prompt in cost_sensitive_tasks:
            print(f"\n📝 Submitting cost-optimized task: {prompt[:40]}...")

            task_id = await guild.submit_parallel_inference(
                prompt=prompt,
                model_requirements=["text_generation"],
                parallel_count=1,
                consensus_required=False,
            )

            if task_id:
                print(f"✅ Task submitted: {task_id}")

        # Wait for completion
        await asyncio.sleep(5)

        # Show cost analysis
        if guild.model_manager and hasattr(guild.model_manager, "get_cost_analysis"):
            cost_analysis = guild.model_manager.get_cost_analysis()
            print(f"\n💰 Final Cost Analysis:")
            print(f"   Total cost: ${cost_analysis['total_cost']:.4f}")
            print(
                f"   Estimated savings: ${cost_analysis.get('cost_savings_vs_remote_only', 0):.4f}"
            )

    finally:
        await guild.stop()


if __name__ == "__main__":
    print("🚀 Starting Guild Resource-Aware Model Management Examples")

    # Run the main demonstration
    asyncio.run(demonstrate_resource_aware_management())

    print("\n" + "=" * 60)
    print("Additional examples (uncomment to run):")
    print("# asyncio.run(configure_remote_endpoints_example())")
    print("# asyncio.run(cost_optimization_example())")
