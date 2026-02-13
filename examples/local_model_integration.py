"""
Example: Local Model Integration with Guild System

This example demonstrates how to use the Guild system as a local LM Studio
model manager with parallel agent tasking capabilities.
"""

import asyncio
from pathlib import Path
from loguru import logger

# Import Guild components
from Guild.core import GuildCore, GuildConfig
from Guild.agents.parallel_inference_agent import ParallelInferenceAgent


async def main():
    """Main example demonstrating local model management and parallel inference"""

    # Configure Guild with model management enabled
    config = GuildConfig(
        task_board_path="guild/ACTIVE_TASKS.md",
        artifact_dir="artifacts/guild",
        enable_model_management=True,
        lm_studio_host="localhost",
        lm_studio_base_port=1234,
        max_parallel_models=5,
        enable_auto_batching=True,
        enable_workspace_monitoring=True,
    )

    # Initialize Guild system
    guild = GuildCore(config=config)
    await guild.start()

    logger.info("Guild system started with model management enabled")

    try:
        # Example 1: Model Discovery and Management
        await example_model_discovery(guild)

        # Example 2: Parallel Inference Agent
        await example_parallel_inference_agent(guild)

        # Example 3: Task-Based Model Selection
        await example_task_based_inference(guild)

        # Example 4: Consensus Generation
        await example_consensus_generation(guild)

        # Example 5: Integration with Guild Tasks
        await example_guild_task_integration(guild)

    finally:
        # Cleanup
        await guild.stop()
        logger.info("Guild system stopped")


async def example_model_discovery(guild: GuildCore):
    """Example 1: Discover and manage local models"""
    logger.info("=== Example 1: Model Discovery and Management ===")

    if not guild.model_manager:
        logger.warning("Model management not enabled")
        return

    # Get available models
    available_models = guild.get_available_models()
    logger.info(f"Found {len(available_models)} available models:")

    for model_id, model_info in available_models.items():
        logger.info(
            f"  - {model_id}: {model_info['name']} ({model_info['parameters']})"
        )
        logger.info(f"    Capabilities: {model_info['capabilities']}")
        logger.info(f"    Memory required: {model_info['memory_required_gb']:.1f}GB")

    # Load a model (if available)
    if available_models:
        model_id = list(available_models.keys())[0]
        logger.info(f"Loading model: {model_id}")

        success = await guild.load_model(model_id)
        if success:
            logger.info(f"✓ Model {model_id} loaded successfully")

            # Check loaded models
            loaded_models = guild.get_loaded_models()
            logger.info(f"Currently loaded models: {list(loaded_models.keys())}")
        else:
            logger.error(f"✗ Failed to load model {model_id}")


async def example_parallel_inference_agent(guild: GuildCore):
    """Example 2: Use parallel inference agent"""
    logger.info("=== Example 2: Parallel Inference Agent ===")

    # Create and start parallel inference agent
    inference_agent = ParallelInferenceAgent(guild)
    await inference_agent.start()

    try:
        # Submit a parallel inference request
        prompt = """
        Explain the concept of recursion in programming with a simple example.
        Make sure to include both the theory and a practical code example.
        """

        request_id = await inference_agent.submit_inference_request(
            prompt=prompt,
            model_requirements=["text_generation", "code_generation"],
            parallel_count=3,
            consensus_required=True,
            requester="example_user",
        )

        if request_id:
            logger.info(f"Submitted inference request: {request_id}")

            # Monitor request status
            for i in range(30):  # Wait up to 30 seconds
                status = await inference_agent.get_request_status(request_id)
                if status:
                    logger.info(f"Request status: {status.get('status', 'unknown')}")

                    if status.get("status") == "completed":
                        results = status.get("results", [])
                        consensus = status.get("consensus")

                        logger.info(f"✓ Request completed with {len(results)} results")
                        if consensus:
                            logger.info(
                                f"Consensus confidence: {consensus.get('confidence', 0):.2f}"
                            )
                        break

                await asyncio.sleep(1)

        # Get performance summary
        performance = inference_agent.get_performance_summary()
        logger.info(f"Agent performance: {performance}")

    finally:
        await inference_agent.stop()


async def example_task_based_inference(guild: GuildCore):
    """Example 3: Task-based model selection and inference"""
    logger.info("=== Example 3: Task-Based Model Selection ===")

    if not guild.model_manager:
        logger.warning("Model management not enabled")
        return

    # Create a coding task
    task_id = await guild.task_director.create_task(
        title="Generate Python function for binary search",
        description="Create a well-documented Python function that implements binary search algorithm",
        capabilities_required=["code_generation", "documentation"],
    )

    logger.info(f"Created task: {task_id}")

    # Submit parallel inference for this task
    prompt = """
    Create a Python function that implements the binary search algorithm.
    Requirements:
    - Function should be well-documented with docstring
    - Include type hints
    - Handle edge cases
    - Include example usage
    """

    parallel_task_id = await guild.submit_parallel_inference(
        prompt=prompt,
        model_requirements=["code_generation"],
        parallel_count=2,
        consensus_required=True,
        metadata={"task_id": task_id},
    )

    if parallel_task_id:
        logger.info(f"Submitted parallel inference: {parallel_task_id}")

        # Wait for results
        for i in range(60):  # Wait up to 60 seconds
            result = await guild.get_inference_result(parallel_task_id)
            if result and result.get("consensus"):
                logger.info("✓ Parallel inference completed with consensus")

                # Complete the task with the result
                await guild.complete_task(
                    task_id=task_id,
                    agent_id="model_manager",
                    result={
                        "implementation": result["consensus"]["consensus_text"],
                        "confidence": result["consensus"]["confidence"],
                        "parallel_task_id": parallel_task_id,
                    },
                )

                logger.info(f"✓ Task {task_id} completed with AI-generated solution")
                break

            await asyncio.sleep(1)


async def example_consensus_generation(guild: GuildCore):
    """Example 4: Demonstrate consensus generation across multiple models"""
    logger.info("=== Example 4: Consensus Generation ===")

    if not guild.model_manager:
        logger.warning("Model management not enabled")
        return

    # Submit a creative writing task that benefits from multiple perspectives
    prompt = """
    Write a short story (2-3 paragraphs) about a robot who discovers emotions.
    The story should be engaging and thought-provoking.
    """

    parallel_task_id = await guild.submit_parallel_inference(
        prompt=prompt,
        model_requirements=["text_generation", "creative_writing"],
        parallel_count=4,  # Use 4 models for diverse perspectives
        consensus_required=True,
        temperature=0.8,  # Higher temperature for creativity
        max_tokens=500,
    )

    if parallel_task_id:
        logger.info(f"Submitted creative writing task: {parallel_task_id}")

        # Monitor progress
        for i in range(90):  # Wait up to 90 seconds
            result = await guild.get_inference_result(parallel_task_id)
            if result:
                results = result.get("results", [])
                consensus = result.get("consensus")

                if results:
                    logger.info(f"Received {len(results)} creative responses")

                    if consensus:
                        logger.info(
                            f"✓ Consensus generated with confidence: {consensus.get('confidence', 0):.2f}"
                        )
                        logger.info(
                            f"Unique responses: {consensus.get('unique_responses', 0)}"
                        )

                        # Log the consensus story
                        consensus_text = consensus.get("consensus_text", "")
                        if consensus_text:
                            logger.info("Generated story (consensus):")
                            logger.info(f"'{consensus_text[:200]}...'")
                        break

            await asyncio.sleep(1)


async def example_guild_task_integration(guild: GuildCore):
    """Example 5: Integration with Guild task system"""
    logger.info("=== Example 5: Guild Task Integration ===")

    # Register a specialized agent that uses model management
    await guild.agent_coordinator.register_agent(
        agent_id="ai_code_reviewer",
        name="AI Code Reviewer",
        capabilities=["code_review", "parallel_inference", "consensus_generation"],
        max_concurrent_tasks=3,
        metadata={"specialization": "code_review_with_ai"},
    )

    # Create a code review task
    task_id = await guild.task_director.create_task(
        title="Review Python function for optimization",
        description="Review the following Python function and suggest optimizations",
        capabilities_required=["code_review", "parallel_inference"],
    )

    logger.info(f"Created code review task: {task_id}")

    # Claim the task as the AI reviewer
    claimed_task = await guild.claim_task("ai_code_reviewer", task_id)

    if claimed_task:
        logger.info(f"✓ Task claimed by AI code reviewer")

        # Simulate code review using parallel inference
        code_to_review = """
def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)
        """

        review_prompt = f"""
        Review the following Python code and provide suggestions for optimization:

        {code_to_review}

        Consider:
        - Performance improvements
        - Code readability
        - Best practices
        - Alternative implementations
        """

        # Submit for parallel review
        parallel_task_id = await guild.submit_parallel_inference(
            prompt=review_prompt,
            model_requirements=["code_generation", "analysis"],
            parallel_count=3,
            consensus_required=True,
            metadata={"task_id": task_id, "review_type": "optimization"},
        )

        if parallel_task_id:
            logger.info(f"Submitted code for parallel review: {parallel_task_id}")

            # Wait for review results
            for i in range(60):
                result = await guild.get_inference_result(parallel_task_id)
                if result and result.get("consensus"):
                    # Complete the task with review results
                    await guild.complete_task(
                        task_id=task_id,
                        agent_id="ai_code_reviewer",
                        result={
                            "review": result["consensus"]["consensus_text"],
                            "confidence": result["consensus"]["confidence"],
                            "reviewers": len(result.get("results", [])),
                            "parallel_task_id": parallel_task_id,
                        },
                    )

                    logger.info(f"✓ Code review completed with AI consensus")
                    break

                await asyncio.sleep(1)

    # Demonstrate cooperation between agents
    logger.info("Requesting cooperation for model recommendations...")

    cooperation_request_id = await guild.agent_coordinator.request_cooperation(
        requesting_agent="ai_code_reviewer",
        request_type="model_recommendation",
        payload={
            "requirements": ["code_generation", "analysis"],
            "task_type": "code_review",
        },
        timeout_minutes=5,
    )

    if cooperation_request_id:
        logger.info(f"Cooperation request submitted: {cooperation_request_id}")

        # Wait for responses
        await asyncio.sleep(2)

        # Check cooperation requests (this would normally be handled by the system)
        logger.info("✓ Cooperation request processed")


async def demonstrate_resource_monitoring(guild: GuildCore):
    """Demonstrate resource monitoring and optimization"""
    logger.info("=== Resource Monitoring Demo ===")

    if not guild.model_manager:
        return

    # Get system health
    health = await guild.get_health_status()

    if "model_manager" in health:
        model_health = health["model_manager"]
        logger.info(f"Model Manager Status: {model_health.get('status')}")
        logger.info(f"Available Models: {model_health.get('available_models', 0)}")
        logger.info(f"Loaded Models: {model_health.get('loaded_models', 0)}")
        logger.info(f"Active Tasks: {model_health.get('active_tasks', 0)}")

        system_resources = model_health.get("system_resources", {})
        logger.info(f"Memory Usage: {system_resources.get('memory_percent', 0):.1f}%")
        logger.info(f"Available Ports: {system_resources.get('available_ports', 0)}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
