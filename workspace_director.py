"""
Guild Workspace Director - Unified workspace and directory management system
"""

import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from loguru import logger
from datetime import datetime, timezone, timedelta
import json
import hashlib
import shutil
import os

from .communication_hub import CommunicationChannel, MessagePriority


class WorkspaceHealth(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    NEEDS_ATTENTION = "needs_attention"
    CRITICAL = "critical"


class CleanupAction(Enum):
    REMOVE_DUPLICATES = "remove_duplicates"
    ARCHIVE_OLD_FILES = "archive_old_files"
    COMPRESS_LOGS = "compress_logs"
    DEFRAGMENT_ARTIFACTS = "defragment_artifacts"
    CLEANUP_TEMP_FILES = "cleanup_temp_files"


@dataclass
class WorkspaceMetrics:
    """Comprehensive workspace health metrics"""

    total_files: int = 0
    total_size_mb: float = 0.0
    duplicate_files: int = 0
    duplicate_size_mb: float = 0.0
    large_files: int = 0
    temp_files: int = 0
    old_files: int = 0
    health_score: float = 0.0
    health_status: WorkspaceHealth = WorkspaceHealth.GOOD
    last_cleanup: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": self.total_files,
            "total_size_mb": self.total_size_mb,
            "duplicate_files": self.duplicate_files,
            "duplicate_size_mb": self.duplicate_size_mb,
            "large_files": self.large_files,
            "temp_files": self.temp_files,
            "old_files": self.old_files,
            "health_score": self.health_score,
            "health_status": self.health_status.value,
            "last_cleanup": self.last_cleanup,
            "recommendations": self.recommendations,
        }


@dataclass
class DirectoryStructure:
    """Represents the organized directory structure"""

    path: Path
    purpose: str
    max_size_mb: Optional[float] = None
    retention_days: Optional[int] = None
    auto_cleanup: bool = False
    subdirectories: Dict[str, "DirectoryStructure"] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "purpose": self.purpose,
            "max_size_mb": self.max_size_mb,
            "retention_days": self.retention_days,
            "auto_cleanup": self.auto_cleanup,
            "subdirectories": {k: v.to_dict() for k, v in self.subdirectories.items()},
        }


class WorkspaceDirector:
    """
    Unified workspace and directory management system.

    Features:
    - Intelligent workspace organization
    - Automated cleanup and maintenance
    - Duplicate file detection and removal
    - Storage optimization and defragmentation
    - Health monitoring and reporting
    - Directory structure management
    - Integration with existing workspace systems
    """

    def __init__(self, config, guild_core):
        self.config = config
        self.guild_core = guild_core
        self._running = False

        # Workspace configuration
        self.workspace_root = Path(".")
        self.ignore_dirs = {
            ".git",
            ".venv",
            "__pycache__",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            "venv",
            "env",
            "build",
            "dist",
            "*.egg-info",
        }
        self.ignore_extensions = {".pyc", ".pyo", ".pyd", ".so", ".dll"}
        self.temp_patterns = ["temp_", "tmp_", ".tmp", "~", ".bak"]

        # Directory structure management
        self._directory_structure = self._initialize_directory_structure()

        # Metrics and monitoring
        self._current_metrics: Optional[WorkspaceMetrics] = None
        self._metrics_history: List[WorkspaceMetrics] = []

        # Cleanup scheduling
        self._cleanup_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self.cleanup_interval = timedelta(hours=6)  # Clean every 6 hours
        self.monitoring_interval = timedelta(minutes=30)  # Monitor every 30 minutes

        # Integration with existing systems
        self._workspace_coordinator = None

        # State persistence
        self.state_file = Path(config.artifact_dir) / "workspace_director_state.json"

        logger.info("Workspace Director initialized")

    def _initialize_directory_structure(self) -> Dict[str, DirectoryStructure]:
        """Initialize the standard AAS directory structure"""
        return {
            "artifacts": DirectoryStructure(
                path=Path("artifacts"),
                purpose="Runtime outputs and generated content",
                max_size_mb=1000.0,
                retention_days=30,
                auto_cleanup=True,
                subdirectories={
                    "batch": DirectoryStructure(
                        path=Path("artifacts/batch"),
                        purpose="Batch processing results",
                        retention_days=14,
                        auto_cleanup=True,
                    ),
                    "handoff": DirectoryStructure(
                        path=Path("artifacts/handoff"),
                        purpose="Task handoff artifacts",
                        retention_days=7,
                        auto_cleanup=False,
                    ),
                    "guild": DirectoryStructure(
                        path=Path("artifacts/guild"),
                        purpose="Guild system artifacts",
                        retention_days=30,
                        auto_cleanup=True,
                    ),
                    "logs": DirectoryStructure(
                        path=Path("artifacts/logs"),
                        purpose="Application logs",
                        max_size_mb=500.0,
                        retention_days=7,
                        auto_cleanup=True,
                    ),
                },
            ),
            "temp": DirectoryStructure(
                path=Path("temp"),
                purpose="Temporary files and processing",
                max_size_mb=200.0,
                retention_days=1,
                auto_cleanup=True,
            ),
            "screenshots": DirectoryStructure(
                path=Path("screenshots"),
                purpose="Screenshot captures",
                max_size_mb=500.0,
                retention_days=14,
                auto_cleanup=True,
            ),
            "logs": DirectoryStructure(
                path=Path("logs"),
                purpose="System logs",
                max_size_mb=300.0,
                retention_days=7,
                auto_cleanup=True,
            ),
        }

    async def start(self) -> None:
        """Start the workspace director"""
        if self._running:
            return

        self._running = True

        # Load existing state
        await self._load_state()

        # Initialize integration with existing workspace systems
        await self._initialize_workspace_integration()

        # Ensure directory structure exists
        await self._ensure_directory_structure()

        # Start monitoring and cleanup tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Subscribe to communication events
        self.guild_core.communication_hub.subscribe(
            CommunicationChannel.WORKSPACE_EVENTS, self._handle_workspace_event
        )

        # Perform initial health check
        await self._perform_health_check()

        logger.info("Workspace Director started")

    async def stop(self) -> None:
        """Stop the workspace director"""
        if not self._running:
            return

        self._running = False

        # Cancel tasks
        for task in [self._monitoring_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Save current state
        await self._save_state()

        logger.info("Workspace Director stopped")

    async def _initialize_workspace_integration(self) -> None:
        """Initialize integration with existing workspace systems"""
        try:
            # Integrate with existing WorkspaceCoordinator
            if self.guild_core.hub and hasattr(
                self.guild_core.hub, "workspace_coordinator"
            ):
                self._workspace_coordinator = self.guild_core.hub.workspace_coordinator
                logger.info("Integrated with existing WorkspaceCoordinator")

        except Exception as e:
            logger.warning(f"Failed to initialize workspace integration: {e}")

    async def _ensure_directory_structure(self) -> None:
        """Ensure the standard directory structure exists"""
        try:
            for name, dir_struct in self._directory_structure.items():
                await self._create_directory_structure(dir_struct)

        except Exception as e:
            logger.error(f"Failed to ensure directory structure: {e}")

    async def _create_directory_structure(self, dir_struct: DirectoryStructure) -> None:
        """Create a directory structure if it doesn't exist"""
        try:
            # Create main directory
            dir_struct.path.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            for subdir_struct in dir_struct.subdirectories.values():
                await self._create_directory_structure(subdir_struct)

        except Exception as e:
            logger.error(f"Failed to create directory structure {dir_struct.path}: {e}")

    async def periodic_cleanup(self) -> None:
        """Perform periodic workspace cleanup"""
        try:
            # Check if cleanup is needed
            if not await self._should_perform_cleanup():
                return

            logger.info("Starting periodic workspace cleanup")

            # Perform various cleanup actions
            cleanup_results = {}

            # Remove duplicate files
            cleanup_results["duplicates"] = await self._cleanup_duplicates()

            # Clean temporary files
            cleanup_results["temp_files"] = await self._cleanup_temp_files()

            # Archive old files
            cleanup_results["old_files"] = await self._archive_old_files()

            # Compress logs
            cleanup_results["logs"] = await self._compress_old_logs()

            # Defragment artifacts
            cleanup_results["defragment"] = await self._defragment_artifacts()

            # Update metrics
            await self._perform_health_check()

            # Emit cleanup event
            await self.guild_core.communication_hub.emit_event(
                "workspace.cleanup_completed",
                {
                    "cleanup_results": cleanup_results,
                    "health_score": (
                        self._current_metrics.health_score
                        if self._current_metrics
                        else 0
                    ),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                CommunicationChannel.WORKSPACE_EVENTS,
                MessagePriority.NORMAL,
            )

            logger.info("Periodic workspace cleanup completed")

        except Exception as e:
            logger.error(f"Failed to perform periodic cleanup: {e}")

    async def _should_perform_cleanup(self) -> bool:
        """Check if cleanup should be performed"""
        try:
            # Check if enough time has passed since last cleanup
            if self._current_metrics and self._current_metrics.last_cleanup:
                last_cleanup = datetime.fromisoformat(
                    self._current_metrics.last_cleanup.replace("Z", "+00:00")
                )
                if datetime.now(timezone.utc) - last_cleanup < self.cleanup_interval:
                    return False

            # Check if health score is below threshold
            if self._current_metrics and self._current_metrics.health_score < 70:
                return True

            # Check if there are many duplicates or temp files
            if self._current_metrics:
                if (
                    self._current_metrics.duplicate_files > 10
                    or self._current_metrics.temp_files > 50
                ):
                    return True

            return True  # Default to performing cleanup

        except Exception as e:
            logger.error(f"Failed to check cleanup necessity: {e}")
            return False

    async def _cleanup_duplicates(self) -> Dict[str, Any]:
        """Remove duplicate files"""
        try:
            if self._workspace_coordinator:
                # Use existing WorkspaceCoordinator functionality
                duplicates = self._workspace_coordinator.find_duplicates()
                removed_count = 0
                saved_space_mb = 0.0

                for file_hash, file_paths in duplicates.items():
                    if len(file_paths) > 1:
                        # Keep the first file, remove others
                        for duplicate_path in file_paths[1:]:
                            try:
                                file_size = duplicate_path.stat().st_size
                                duplicate_path.unlink()
                                removed_count += 1
                                saved_space_mb += file_size / (1024 * 1024)
                            except Exception as e:
                                logger.warning(
                                    f"Failed to remove duplicate {duplicate_path}: {e}"
                                )

                return {
                    "removed_count": removed_count,
                    "saved_space_mb": round(saved_space_mb, 2),
                }
            else:
                # Fallback duplicate detection
                return await self._fallback_duplicate_cleanup()

        except Exception as e:
            logger.error(f"Failed to cleanup duplicates: {e}")
            return {"error": str(e)}

    async def _fallback_duplicate_cleanup(self) -> Dict[str, Any]:
        """Fallback duplicate cleanup implementation"""
        try:
            file_hashes = {}
            removed_count = 0
            saved_space_mb = 0.0

            for file_path in self.workspace_root.rglob("*"):
                if (
                    file_path.is_file()
                    and not self._should_ignore_file(file_path)
                    and file_path.stat().st_size > 1024
                ):  # Only check files > 1KB

                    file_hash = await self._compute_file_hash(file_path)
                    if file_hash in file_hashes:
                        # Duplicate found
                        try:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            removed_count += 1
                            saved_space_mb += file_size / (1024 * 1024)
                        except Exception as e:
                            logger.warning(
                                f"Failed to remove duplicate {file_path}: {e}"
                            )
                    else:
                        file_hashes[file_hash] = file_path

            return {
                "removed_count": removed_count,
                "saved_space_mb": round(saved_space_mb, 2),
            }

        except Exception as e:
            logger.error(f"Fallback duplicate cleanup failed: {e}")
            return {"error": str(e)}

    async def _compute_file_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """Compute SHA256 hash of file content"""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash file {file_path}: {e}")
            return ""

    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored during processing"""
        # Check if any parent directory is in ignore list
        for part in file_path.parts:
            if part in self.ignore_dirs or part.startswith("."):
                return True

        # Check file extension
        if file_path.suffix in self.ignore_extensions:
            return True

        return False

    async def _cleanup_temp_files(self) -> Dict[str, Any]:
        """Clean up temporary files"""
        try:
            removed_count = 0
            saved_space_mb = 0.0

            # Clean temp directories
            for dir_name, dir_struct in self._directory_structure.items():
                if dir_struct.auto_cleanup and dir_struct.retention_days:
                    result = await self._cleanup_directory_by_age(
                        dir_struct.path, dir_struct.retention_days
                    )
                    removed_count += result["removed_count"]
                    saved_space_mb += result["saved_space_mb"]

            # Clean files matching temp patterns
            for pattern in self.temp_patterns:
                for file_path in self.workspace_root.rglob(f"*{pattern}*"):
                    if file_path.is_file() and not self._should_ignore_file(file_path):
                        try:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            removed_count += 1
                            saved_space_mb += file_size / (1024 * 1024)
                        except Exception as e:
                            logger.warning(
                                f"Failed to remove temp file {file_path}: {e}"
                            )

            return {
                "removed_count": removed_count,
                "saved_space_mb": round(saved_space_mb, 2),
            }

        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
            return {"error": str(e)}

    async def _cleanup_directory_by_age(
        self, directory: Path, retention_days: int
    ) -> Dict[str, Any]:
        """Clean up files in directory older than retention period"""
        try:
            if not directory.exists():
                return {"removed_count": 0, "saved_space_mb": 0.0}

            cutoff_time = datetime.now() - timedelta(days=retention_days)
            removed_count = 0
            saved_space_mb = 0.0

            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    try:
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_time:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            removed_count += 1
                            saved_space_mb += file_size / (1024 * 1024)
                    except Exception as e:
                        logger.warning(f"Failed to remove old file {file_path}: {e}")

            return {
                "removed_count": removed_count,
                "saved_space_mb": round(saved_space_mb, 2),
            }

        except Exception as e:
            logger.error(f"Failed to cleanup directory {directory}: {e}")
            return {"error": str(e)}

    async def _archive_old_files(self) -> Dict[str, Any]:
        """Archive old files to reduce workspace clutter"""
        try:
            # Create archive directory
            archive_dir = Path("artifacts/archive")
            archive_dir.mkdir(parents=True, exist_ok=True)

            archived_count = 0
            saved_space_mb = 0.0

            # Archive old screenshots
            screenshots_dir = Path("screenshots")
            if screenshots_dir.exists():
                cutoff_time = datetime.now() - timedelta(days=30)

                for file_path in screenshots_dir.rglob("*.png"):
                    try:
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_time:
                            # Move to archive
                            archive_path = archive_dir / "screenshots" / file_path.name
                            archive_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(file_path), str(archive_path))
                            archived_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to archive file {file_path}: {e}")

            return {
                "archived_count": archived_count,
                "saved_space_mb": round(saved_space_mb, 2),
            }

        except Exception as e:
            logger.error(f"Failed to archive old files: {e}")
            return {"error": str(e)}

    async def _compress_old_logs(self) -> Dict[str, Any]:
        """Compress old log files"""
        try:
            import gzip

            compressed_count = 0
            saved_space_mb = 0.0

            # Compress logs older than 3 days
            cutoff_time = datetime.now() - timedelta(days=3)

            for log_dir in [Path("logs"), Path("artifacts/logs")]:
                if not log_dir.exists():
                    continue

                for log_file in log_dir.rglob("*.log"):
                    try:
                        file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                        if file_mtime < cutoff_time and not log_file.name.endswith(
                            ".gz"
                        ):
                            # Compress the file
                            original_size = log_file.stat().st_size
                            compressed_path = log_file.with_suffix(
                                log_file.suffix + ".gz"
                            )

                            with open(log_file, "rb") as f_in:
                                with gzip.open(compressed_path, "wb") as f_out:
                                    shutil.copyfileobj(f_in, f_out)

                            # Remove original
                            log_file.unlink()

                            compressed_size = compressed_path.stat().st_size
                            saved_space_mb += (original_size - compressed_size) / (
                                1024 * 1024
                            )
                            compressed_count += 1

                    except Exception as e:
                        logger.warning(f"Failed to compress log {log_file}: {e}")

            return {
                "compressed_count": compressed_count,
                "saved_space_mb": round(saved_space_mb, 2),
            }

        except Exception as e:
            logger.error(f"Failed to compress logs: {e}")
            return {"error": str(e)}

    async def _defragment_artifacts(self) -> Dict[str, Any]:
        """Defragment and organize artifacts directory"""
        try:
            organized_count = 0

            artifacts_dir = Path("artifacts")
            if not artifacts_dir.exists():
                return {"organized_count": 0}

            # Organize files by type and date
            for file_path in artifacts_dir.rglob("*"):
                if file_path.is_file() and file_path.parent == artifacts_dir:
                    try:
                        # Determine appropriate subdirectory
                        target_subdir = self._determine_artifact_category(file_path)
                        if target_subdir:
                            target_dir = artifacts_dir / target_subdir
                            target_dir.mkdir(parents=True, exist_ok=True)

                            target_path = target_dir / file_path.name
                            if not target_path.exists():
                                shutil.move(str(file_path), str(target_path))
                                organized_count += 1

                    except Exception as e:
                        logger.warning(f"Failed to organize file {file_path}: {e}")

            return {"organized_count": organized_count}

        except Exception as e:
            logger.error(f"Failed to defragment artifacts: {e}")
            return {"error": str(e)}

    def _determine_artifact_category(self, file_path: Path) -> Optional[str]:
        """Determine the appropriate category for an artifact file"""
        name = file_path.name.lower()

        if "batch" in name or "openai" in name:
            return "batch"
        elif "handoff" in name or "task" in name:
            return "handoff"
        elif "guild" in name:
            return "guild"
        elif name.endswith((".log", ".txt")) and "log" in name:
            return "logs"
        elif name.endswith((".json", ".yaml", ".yml")) and "config" in name:
            return "config"
        else:
            return "misc"

    async def _perform_health_check(self) -> None:
        """Perform comprehensive workspace health check"""
        try:
            metrics = WorkspaceMetrics()

            # Collect basic metrics
            total_size = 0
            file_count = 0
            duplicate_count = 0
            large_file_count = 0
            temp_file_count = 0
            old_file_count = 0

            cutoff_time = datetime.now() - timedelta(days=30)
            large_file_threshold = 100 * 1024 * 1024  # 100MB

            # Scan workspace
            file_hashes = {}

            for file_path in self.workspace_root.rglob("*"):
                if file_path.is_file() and not self._should_ignore_file(file_path):
                    try:
                        file_size = file_path.stat().st_size
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                        file_count += 1
                        total_size += file_size

                        # Check for large files
                        if file_size > large_file_threshold:
                            large_file_count += 1

                        # Check for old files
                        if file_mtime < cutoff_time:
                            old_file_count += 1

                        # Check for temp files
                        if any(
                            pattern in file_path.name for pattern in self.temp_patterns
                        ):
                            temp_file_count += 1

                        # Check for duplicates (sample check for performance)
                        if (
                            file_size > 1024 and file_count % 10 == 0
                        ):  # Sample every 10th file
                            file_hash = await self._compute_file_hash(file_path)
                            if file_hash in file_hashes:
                                duplicate_count += 1
                            else:
                                file_hashes[file_hash] = file_path

                    except Exception as e:
                        logger.warning(f"Failed to analyze file {file_path}: {e}")

            # Update metrics
            metrics.total_files = file_count
            metrics.total_size_mb = total_size / (1024 * 1024)
            metrics.duplicate_files = duplicate_count
            metrics.large_files = large_file_count
            metrics.temp_files = temp_file_count
            metrics.old_files = old_file_count

            # Calculate health score
            metrics.health_score = self._calculate_health_score(metrics)
            metrics.health_status = self._determine_health_status(metrics.health_score)

            # Generate recommendations
            metrics.recommendations = self._generate_recommendations(metrics)

            # Update current metrics
            self._current_metrics = metrics
            self._metrics_history.append(metrics)

            # Keep history manageable
            if len(self._metrics_history) > 100:
                self._metrics_history = self._metrics_history[-50:]

            # Emit health check event
            await self.guild_core.communication_hub.emit_event(
                "workspace.health_check",
                metrics.to_dict(),
                CommunicationChannel.WORKSPACE_EVENTS,
                MessagePriority.LOW,
            )

            logger.info(
                f"Workspace health check completed - Score: {metrics.health_score:.1f} ({metrics.health_status.value})"
            )

        except Exception as e:
            logger.error(f"Failed to perform health check: {e}")

    def _calculate_health_score(self, metrics: WorkspaceMetrics) -> float:
        """Calculate overall workspace health score (0-100)"""
        try:
            score = 100.0

            # Penalize for duplicates
            if metrics.duplicate_files > 0:
                duplicate_penalty = min(metrics.duplicate_files * 2, 20)
                score -= duplicate_penalty

            # Penalize for too many temp files
            if metrics.temp_files > 10:
                temp_penalty = min((metrics.temp_files - 10) * 0.5, 15)
                score -= temp_penalty

            # Penalize for too many old files
            if metrics.old_files > 50:
                old_penalty = min((metrics.old_files - 50) * 0.2, 10)
                score -= old_penalty

            # Penalize for excessive size
            if metrics.total_size_mb > 5000:  # 5GB
                size_penalty = min((metrics.total_size_mb - 5000) / 1000 * 5, 20)
                score -= size_penalty

            # Penalize for too many large files
            if metrics.large_files > 5:
                large_file_penalty = min((metrics.large_files - 5) * 2, 15)
                score -= large_file_penalty

            return max(0.0, min(100.0, score))

        except Exception as e:
            logger.error(f"Failed to calculate health score: {e}")
            return 50.0

    def _determine_health_status(self, health_score: float) -> WorkspaceHealth:
        """Determine health status based on score"""
        if health_score >= 90:
            return WorkspaceHealth.EXCELLENT
        elif health_score >= 75:
            return WorkspaceHealth.GOOD
        elif health_score >= 60:
            return WorkspaceHealth.FAIR
        elif health_score >= 40:
            return WorkspaceHealth.NEEDS_ATTENTION
        else:
            return WorkspaceHealth.CRITICAL

    def _generate_recommendations(self, metrics: WorkspaceMetrics) -> List[str]:
        """Generate recommendations based on metrics"""
        recommendations = []

        if metrics.duplicate_files > 5:
            recommendations.append(
                f"Remove {metrics.duplicate_files} duplicate files to save space"
            )

        if metrics.temp_files > 20:
            recommendations.append(f"Clean up {metrics.temp_files} temporary files")

        if metrics.old_files > 100:
            recommendations.append(f"Archive or remove {metrics.old_files} old files")

        if metrics.large_files > 10:
            recommendations.append(
                f"Review {metrics.large_files} large files for archival"
            )

        if metrics.total_size_mb > 10000:  # 10GB
            recommendations.append(
                "Consider archiving old data to reduce workspace size"
            )

        if not recommendations:
            recommendations.append("Workspace is in good condition")

        return recommendations

    async def get_health(self) -> Dict[str, Any]:
        """Get health status of workspace director"""
        return {
            "status": "healthy" if self._running else "stopped",
            "current_metrics": (
                self._current_metrics.to_dict() if self._current_metrics else None
            ),
            "directory_structure": {
                name: struct.to_dict()
                for name, struct in self._directory_structure.items()
            },
            "integration": {
                "workspace_coordinator": self._workspace_coordinator is not None
            },
        }

    async def _handle_workspace_event(self, message) -> None:
        """Handle workspace-related events"""
        try:
            event_type = message.event_type
            data = message.payload

            if event_type == "workspace.cleanup_requested":
                await self.periodic_cleanup()
            elif event_type == "workspace.health_check_requested":
                await self._perform_health_check()
            # Add more event handlers as needed

        except Exception as e:
            logger.error(f"Failed to handle workspace event: {e}")

    async def _monitoring_loop(self) -> None:
        """Periodic monitoring loop"""
        while self._running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.monitoring_interval.total_seconds())
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup loop"""
        while self._running:
            try:
                await self.periodic_cleanup()
                await asyncio.sleep(self.cleanup_interval.total_seconds())
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _load_state(self) -> None:
        """Load workspace director state from disk"""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r") as f:
                    state = json.load(f)

                # Restore metrics history
                for metrics_data in state.get("metrics_history", []):
                    metrics = WorkspaceMetrics(
                        total_files=metrics_data.get("total_files", 0),
                        total_size_mb=metrics_data.get("total_size_mb", 0.0),
                        duplicate_files=metrics_data.get("duplicate_files", 0),
                        duplicate_size_mb=metrics_data.get("duplicate_size_mb", 0.0),
                        large_files=metrics_data.get("large_files", 0),
                        temp_files=metrics_data.get("temp_files", 0),
                        old_files=metrics_data.get("old_files", 0),
                        health_score=metrics_data.get("health_score", 0.0),
                        health_status=WorkspaceHealth(
                            metrics_data.get("health_status", "good")
                        ),
                        last_cleanup=metrics_data.get("last_cleanup"),
                        recommendations=metrics_data.get("recommendations", []),
                    )
                    self._metrics_history.append(metrics)

                logger.info(
                    f"Loaded workspace state with {len(self._metrics_history)} historical metrics"
                )

        except Exception as e:
            logger.error(f"Failed to load workspace state: {e}")

    async def _save_state(self) -> None:
        """Save workspace director state to disk"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                "metrics_history": [
                    metrics.to_dict() for metrics in self._metrics_history[-50:]
                ],  # Keep last 50
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)

            logger.debug("Workspace director state saved")

        except Exception as e:
            logger.error(f"Failed to save workspace state: {e}")
