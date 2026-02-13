#!/usr/bin/env python3
"""
Guild Model Management CLI

Command-line interface for managing local models and parallel inference.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from loguru import logger

# Add Guild to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Guild.core import GuildCore, GuildConfig
from Guild.agents.parallel_inference_agent import ParallelInferenceAgent


async def list_models(guild: GuildCore):
    """List available and loaded models"""
    if not guild.model_manager:
        print("❌ Model management not enabled")
        return

    available = guild.get_available_models()
    loaded = guild.get_loaded_models()

    print(f"📚 Available Models ({len(available)}):")
    for model_id, info in available.items():
        status = "🟢 LOADED" if model_id in loaded else "⚪ AVAILABLE"
        print(f"  {status} {model_id}")
        print(f"    Name: {info['name']}")
        print(f"    Size: {info['parameters']} ({info['size']})")
        print(f"    Capabilities: {', '.join(info['capabilities'])}")
        print(f"    Memory: {info['memory_required_gb']:.1f}GB")
        print()


async def load_model(guild: GuildCore, model_id: str):
    """Load a specific model"""
    if not guild.model_manager:
        print("❌ Model management not enabled")
        return

    print(f"🔄 Loading model: {model_id}")
    success = await guild.load_model(model_id)

    if success:
        print(f"✅ Model {model_id} loaded successfully")
    else:
        print(f"❌ Failed to load model {model_id}")


async def unload_model(guild: GuildCore, model_id: str):
    """Unload a specific model"""
    if not guild.model_manager:
        print("❌ Model management not enabled")
        return

    print(f"🔄 Unloading model: {model_id}")
    success = await guild.unload_model(model_id)

    if success:
        print(f"✅ Model {model_id} unloaded successfully")
    else:
        print(f"❌ Failed to unload model {model_id}")


async def parallel_inference(
    guild: GuildCore, prompt: str, count: int = 3, consensus: bool = True
):
    """Run parallel inference across multiple models"""
    if not guild.model_manager:
        print("❌ Model management not enabled")
        return

    print(f"🚀 Starting parallel inference with {count} models...")
    print(f"📝 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

    task_id = await guild.submit_parallel_inference(
        prompt=prompt,
        parallel_count=count,
        consensus_required=consensus,
        model_requirements=["text_generation"],
    )

    if not task_id:
        print("❌ Failed to submit parallel inference task")
        return

    print(f"⏳ Task submitted: {task_id}")
    print("Waiting for results...")

    # Wait for results
    for i in range(120):  # Wait up to 2 minutes
        result = await guild.get_inference_result(task_id)

        if result:
            results = result.get("results", [])
            consensus_result = result.get("consensus")

            if results:
                print(f"\n📊 Results from {len(results)} models:")

                for i, model_result in enumerate(results, 1):
                    model_name = model_result.get("model_name", "Unknown")
                    execution_time = model_result.get("execution_time", 0)

                    print(f"\n🤖 Model {i}: {model_name} ({execution_time:.2f}s)")

                    if "result" in model_result and "choices" in model_result["result"]:
                        choices = model_result["result"]["choices"]
                        if choices and "message" in choices[0]:
                            response = choices[0]["message"]["content"]
                            print(
                                f"Response: {response[:200]}{'...' if len(response) > 200 else ''}"
                            )

                if consensus_result and consensus:
                    print(f"\n🎯 Consensus Result:")
                    print(f"Confidence: {consensus_result.get('confidence', 0):.2f}")
                    print(
                        f"Unique responses: {consensus_result.get('unique_responses', 0)}"
                    )
                    consensus_text = consensus_result.get("consensus_text", "")
                    print(
                        f"Consensus: {consensus_text[:300]}{'...' if len(consensus_text) > 300 else ''}"
                    )

                break

        await asyncio.sleep(1)
        if i % 10 == 0:
            print(f"⏳ Still waiting... ({i}s)")

    print("✅ Parallel inference completed")


async def system_status(guild: GuildCore):
    """Show system status"""
    health = await guild.get_health_status()

    print("🏥 Guild System Health:")
    for component, status in health.items():
        if isinstance(status, dict):
            component_status = status.get("status", "unknown")
            emoji = "✅" if component_status == "healthy" else "❌"
            print(f"  {emoji} {component}: {component_status}")

            # Show additional details for model manager
            if component == "model_manager" and component_status == "healthy":
                print(f"    📚 Available models: {status.get('available_models', 0)}")
                print(f"    🟢 Loaded models: {status.get('loaded_models', 0)}")
                print(f"    ⚡ Active tasks: {status.get('active_tasks', 0)}")

                resources = status.get("system_resources", {})
                memory_pct = resources.get("memory_percent", 0)
                print(f"    💾 Memory usage: {memory_pct:.1f}%")


async def interactive_mode(guild: GuildCore):
    """Interactive mode for model management"""
    print("🎮 Guild Model Management - Interactive Mode")
    print("Commands: list, load <model>, unload <model>, infer <prompt>, status, quit")

    while True:
        try:
            command = input("\n> ").strip().split()
            if not command:
                continue

            cmd = command[0].lower()

            if cmd == "quit" or cmd == "exit":
                break
            elif cmd == "list":
                await list_models(guild)
            elif cmd == "load" and len(command) > 1:
                await load_model(guild, command[1])
            elif cmd == "unload" and len(command) > 1:
                await unload_model(guild, command[1])
            elif cmd == "infer" and len(command) > 1:
                prompt = " ".join(command[1:])
                await parallel_inference(guild, prompt, count=2, consensus=True)
            elif cmd == "status":
                await system_status(guild)
            else:
                print(
                    "❓ Unknown command. Available: list, load, unload, infer, status, quit"
                )

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

    print("👋 Goodbye!")


async def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Guild Model Management CLI")
    parser.add_argument("--config", help="Guild configuration file")
    parser.add_argument("--host", default="localhost", help="LM Studio host")
    parser.add_argument("--port", type=int, default=1234, help="LM Studio base port")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    subparsers.add_parser("list", help="List available and loaded models")

    # Load command
    load_parser = subparsers.add_parser("load", help="Load a model")
    load_parser.add_argument("model_id", help="Model ID to load")

    # Unload command
    unload_parser = subparsers.add_parser("unload", help="Unload a model")
    unload_parser.add_argument("model_id", help="Model ID to unload")

    # Inference command
    infer_parser = subparsers.add_parser("infer", help="Run parallel inference")
    infer_parser.add_argument("prompt", help="Prompt for inference")
    infer_parser.add_argument(
        "--count", type=int, default=3, help="Number of parallel models"
    )
    infer_parser.add_argument(
        "--no-consensus", action="store_true", help="Disable consensus generation"
    )

    # Status command
    subparsers.add_parser("status", help="Show system status")

    # Interactive command
    subparsers.add_parser("interactive", help="Start interactive mode")

    args = parser.parse_args()

    # Configure Guild
    config = GuildConfig(
        enable_model_management=True,
        lm_studio_host=args.host,
        lm_studio_base_port=args.port,
        artifact_dir="artifacts/guild_cli",
    )

    # Initialize Guild
    guild = GuildCore(config=config)

    try:
        print("🚀 Starting Guild system...")
        await guild.start()

        if not args.command:
            await interactive_mode(guild)
        elif args.command == "list":
            await list_models(guild)
        elif args.command == "load":
            await load_model(guild, args.model_id)
        elif args.command == "unload":
            await unload_model(guild, args.model_id)
        elif args.command == "infer":
            await parallel_inference(
                guild, args.prompt, count=args.count, consensus=not args.no_consensus
            )
        elif args.command == "status":
            await system_status(guild)
        elif args.command == "interactive":
            await interactive_mode(guild)

    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("CLI error")
    finally:
        print("🛑 Stopping Guild system...")
        await guild.stop()


if __name__ == "__main__":
    asyncio.run(main())
