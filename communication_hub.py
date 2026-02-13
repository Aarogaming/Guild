"""
Guild Communication Hub - Unified inter-module communication system
"""

import asyncio
from typing import Dict, Any, List, Callable, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import json
from datetime import datetime, timezone


class MessagePriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class CommunicationChannel(Enum):
    TASK_UPDATES = "task_updates"
    AGENT_COORDINATION = "agent_coordination"
    BATCH_PROCESSING = "batch_processing"
    WORKSPACE_EVENTS = "workspace_events"
    SYSTEM_ALERTS = "system_alerts"
    IPC_BRIDGE = "ipc_bridge"


@dataclass
class Message:
    """Structured message for inter-module communication"""

    id: str
    channel: CommunicationChannel
    event_type: str
    source: str
    target: Optional[str]
    priority: MessagePriority
    payload: Dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl_seconds: Optional[int] = None


class CommunicationHub:
    """
    Unified communication hub for all Guild inter-module communication.

    Features:
    - Multi-channel message routing
    - Priority-based message handling
    - Event subscription and broadcasting
    - Cross-module coordination
    - Message persistence and replay
    - Dead letter queue for failed messages
    """

    def __init__(self, config, guild_core):
        self.config = config
        self.guild_core = guild_core
        self._running = False

        # Message routing and subscriptions
        self._subscribers: Dict[CommunicationChannel, List[Callable]] = {
            channel: [] for channel in CommunicationChannel
        }
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._dead_letter_queue: List[Message] = []
        self._message_history: List[Message] = []

        # Cross-module bridges
        self._ipc_bridge = None
        self._event_bus = None
        self._websocket_manager = None

        # Processing tasks
        self._message_processor_task: Optional[asyncio.Task] = None

        logger.info("Communication Hub initialized")

    async def start(self) -> None:
        """Start the communication hub"""
        if self._running:
            return

        self._running = True

        # Initialize bridges to existing systems
        await self._initialize_bridges()

        # Start message processing
        self._message_processor_task = asyncio.create_task(self._process_messages())

        logger.info("Communication Hub started")

    async def stop(self) -> None:
        """Stop the communication hub"""
        if not self._running:
            return

        self._running = False

        if self._message_processor_task:
            self._message_processor_task.cancel()
            try:
                await self._message_processor_task
            except asyncio.CancelledError:
                pass

        logger.info("Communication Hub stopped")

    async def _initialize_bridges(self) -> None:
        """Initialize bridges to existing AAS communication systems"""
        try:
            # Bridge to existing EventBus
            if self.guild_core.hub and hasattr(self.guild_core.hub, "events"):
                self._event_bus = self.guild_core.hub.events
                logger.info("Bridged to existing EventBus")

            # Bridge to WebSocket manager
            if self.guild_core.hub and hasattr(self.guild_core.hub, "ws_manager"):
                self._websocket_manager = self.guild_core.hub.ws_manager
                logger.info("Bridged to WebSocket manager")

            # Bridge to IPC server
            if self.guild_core.hub and hasattr(self.guild_core.hub, "ipc"):
                self._ipc_bridge = self.guild_core.hub.ipc
                logger.info("Bridged to IPC server")

        except Exception as e:
            logger.warning(f"Failed to initialize some communication bridges: {e}")

    def subscribe(
        self, channel: CommunicationChannel, handler: Callable[[Message], None]
    ) -> None:
        """Subscribe to messages on a specific channel"""
        self._subscribers[channel].append(handler)
        logger.debug(f"New subscriber added to {channel.value}")

    def unsubscribe(
        self, channel: CommunicationChannel, handler: Callable[[Message], None]
    ) -> None:
        """Unsubscribe from messages on a specific channel"""
        if handler in self._subscribers[channel]:
            self._subscribers[channel].remove(handler)
            logger.debug(f"Subscriber removed from {channel.value}")

    async def send_message(self, message: Message) -> None:
        """Send a message through the communication hub"""
        await self._message_queue.put(message)
        logger.debug(f"Message queued: {message.event_type} on {message.channel.value}")

    async def emit_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        channel: CommunicationChannel = CommunicationChannel.SYSTEM_ALERTS,
        priority: MessagePriority = MessagePriority.NORMAL,
        target: Optional[str] = None,
    ) -> None:
        """Emit an event through the communication hub"""
        import uuid

        message = Message(
            id=str(uuid.uuid4()),
            channel=channel,
            event_type=event_type,
            source="guild.communication_hub",
            target=target,
            priority=priority,
            payload=data,
        )

        await self.send_message(message)

    async def _process_messages(self) -> None:
        """Process messages from the queue"""
        while self._running:
            try:
                # Get message with timeout to allow periodic checks
                message = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                await self._handle_message(message)
            except asyncio.TimeoutError:
                continue  # Normal timeout, continue processing
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def _handle_message(self, message: Message) -> None:
        """Handle a single message"""
        try:
            # Add to history
            self._message_history.append(message)

            # Keep history size manageable
            if len(self._message_history) > 1000:
                self._message_history = self._message_history[-500:]

            # Route to subscribers
            subscribers = self._subscribers.get(message.channel, [])

            # Execute subscribers based on priority
            if message.priority == MessagePriority.URGENT:
                # Process urgent messages immediately
                for subscriber in subscribers:
                    try:
                        if asyncio.iscoroutinefunction(subscriber):
                            await subscriber(message)
                        else:
                            subscriber(message)
                    except Exception as e:
                        logger.error(f"Subscriber error for urgent message: {e}")
            else:
                # Process normal messages asynchronously
                tasks = []
                for subscriber in subscribers:
                    if asyncio.iscoroutinefunction(subscriber):
                        tasks.append(asyncio.create_task(subscriber(message)))
                    else:
                        try:
                            subscriber(message)
                        except Exception as e:
                            logger.error(f"Subscriber error: {e}")

                # Wait for async subscribers
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

            # Bridge to existing systems
            await self._bridge_message(message)

            logger.debug(f"Message processed: {message.event_type}")

        except Exception as e:
            logger.error(f"Failed to handle message {message.id}: {e}")
            self._dead_letter_queue.append(message)

    async def _bridge_message(self, message: Message) -> None:
        """Bridge message to existing AAS communication systems"""
        try:
            # Bridge to EventBus
            if self._event_bus:
                await self._event_bus.emit(
                    event_type=message.event_type,
                    data=message.payload,
                    source=message.source,
                    correlation_id=message.correlation_id,
                )

            # Bridge to WebSocket
            if (
                self._websocket_manager
                and message.channel != CommunicationChannel.IPC_BRIDGE
            ):
                await self._websocket_manager.broadcast(
                    {
                        "type": "guild_message",
                        "channel": message.channel.value,
                        "event_type": message.event_type,
                        "data": message.payload,
                        "timestamp": message.timestamp,
                    }
                )

            # Bridge to IPC for cross-process communication
            if (
                self._ipc_bridge
                and message.channel == CommunicationChannel.IPC_BRIDGE
                and message.target
            ):
                # Route to specific IPC target (e.g., Maelstrom)
                pass  # Implementation depends on IPC bridge interface

        except Exception as e:
            logger.warning(f"Failed to bridge message to existing systems: {e}")

    async def get_health(self) -> Dict[str, Any]:
        """Get health status of communication hub"""
        return {
            "status": "healthy" if self._running else "stopped",
            "queue_size": self._message_queue.qsize(),
            "dead_letter_count": len(self._dead_letter_queue),
            "message_history_count": len(self._message_history),
            "active_subscribers": {
                channel.value: len(subscribers)
                for channel, subscribers in self._subscribers.items()
            },
            "bridges": {
                "event_bus": self._event_bus is not None,
                "websocket": self._websocket_manager is not None,
                "ipc": self._ipc_bridge is not None,
            },
        }

    def get_message_history(
        self, channel: Optional[CommunicationChannel] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get message history for debugging and monitoring"""
        messages = self._message_history

        if channel:
            messages = [m for m in messages if m.channel == channel]

        return [
            {
                "id": m.id,
                "channel": m.channel.value,
                "event_type": m.event_type,
                "source": m.source,
                "target": m.target,
                "priority": m.priority.name,
                "timestamp": m.timestamp,
                "payload_keys": list(m.payload.keys()),
            }
            for m in messages[-limit:]
        ]
