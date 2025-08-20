"""
Slack API Mock

Mock implementation of Slack API for testing and development.
Simulates Slack webhooks, bot API, and user interactions.
"""

import logging
import asyncio
import random
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class SlackMock:
    """Mock Slack API implementation."""
    
    def __init__(self, failure_rate: float = 0.03):
        self.failure_rate = failure_rate
        self.response_delay = (0.2, 1.0)
        
        # Mock Slack data
        self._channels = {
            "general": {"id": "C1234567890", "name": "general", "members": 50},
            "random": {"id": "C1234567891", "name": "random", "members": 30},
            "operations": {"id": "C1234567892", "name": "operations", "members": 15},
            "alerts": {"id": "C1234567893", "name": "alerts", "members": 8}
        }
        
        self._users = {
            "U123456": {"name": "john.doe", "real_name": "John Doe", "status": "active"},
            "U123457": {"name": "jane.smith", "real_name": "Jane Smith", "status": "active"},
            "U123458": {"name": "bot.assistant", "real_name": "Bot Assistant", "status": "bot"}
        }
        
        self._sent_messages = []
        self._webhooks = {}
        
        # Metrics
        self._message_count = 0
        self._error_count = 0
        
        logger.info("SlackMock initialized")
    
    async def send_message(self, channel: str, text: str, username: str = "System Bot",
                          attachments: List[Dict] = None, blocks: List[Dict] = None) -> Dict[str, Any]:
        """Send message to Slack channel."""
        start_time = time.time()
        self._message_count += 1
        
        try:
            await self._simulate_delay()
            
            if self._should_fail():
                self._error_count += 1
                raise Exception(f"Slack API error: {self._generate_slack_error()}")
            
            # Validate channel
            if not self._is_valid_channel(channel):
                raise Exception(f"Channel not found: {channel}")
            
            # Generate message timestamp
            message_ts = str(time.time())
            
            # Create message record
            message = {
                "ts": message_ts,
                "channel": channel,
                "text": text,
                "username": username,
                "attachments": attachments or [],
                "blocks": blocks or [],
                "sent_at": datetime.utcnow().isoformat(),
                "message_id": str(uuid.uuid4())
            }
            
            self._sent_messages.append(message)
            
            execution_time = time.time() - start_time
            
            result = {
                "ok": True,
                "channel": self._get_channel_id(channel),
                "ts": message_ts,
                "message": message,
                "execution_time_ms": execution_time * 1000
            }
            
            logger.info(f"Slack message sent to #{channel}: {text[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Slack message send failed: {e}")
            raise
    
    async def send_direct_message(self, user_id: str, text: str) -> Dict[str, Any]:
        """Send direct message to user."""
        try:
            await self._simulate_delay()
            
            if user_id not in self._users:
                raise Exception(f"User not found: {user_id}")
            
            # Simulate DM channel creation
            dm_channel = f"D{random.randint(100000000, 999999999)}"
            
            result = await self.send_message(
                channel=dm_channel,
                text=text,
                username="Direct Message Bot"
            )
            
            result["user_id"] = user_id
            result["dm_channel"] = dm_channel
            
            logger.info(f"Slack DM sent to user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Slack DM send failed: {e}")
            raise
    
    async def post_webhook(self, webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Post to Slack webhook."""
        start_time = time.time()
        
        try:
            await self._simulate_delay()
            
            if self._should_fail():
                raise Exception("Webhook delivery failed: Connection timeout")
            
            # Extract webhook ID from URL (simplified)
            webhook_id = webhook_url.split("/")[-1] if "/" in webhook_url else webhook_url
            
            # Store webhook delivery
            webhook_delivery = {
                "webhook_id": webhook_id,
                "webhook_url": webhook_url,
                "payload": payload,
                "delivered_at": datetime.utcnow().isoformat(),
                "status": "delivered"
            }
            
            self._webhooks[webhook_id] = webhook_delivery
            
            execution_time = time.time() - start_time
            
            result = {
                "ok": True,
                "webhook_id": webhook_id,
                "status": "delivered",
                "execution_time_ms": execution_time * 1000
            }
            
            logger.info(f"Slack webhook delivered: {webhook_id}")
            return result
            
        except Exception as e:
            logger.error(f"Slack webhook delivery failed: {e}")
            raise
    
    async def create_thread_reply(self, channel: str, thread_ts: str, text: str) -> Dict[str, Any]:
        """Reply to a message thread."""
        try:
            await self._simulate_delay(factor=0.5)
            
            result = await self.send_message(channel, text)
            result["thread_ts"] = thread_ts
            result["is_thread_reply"] = True
            
            logger.info(f"Slack thread reply sent to #{channel}")
            return result
            
        except Exception as e:
            logger.error(f"Slack thread reply failed: {e}")
            raise
    
    async def add_reaction(self, channel: str, timestamp: str, emoji: str) -> Dict[str, Any]:
        """Add emoji reaction to message."""
        try:
            await self._simulate_delay(factor=0.2)
            
            if self._should_fail():
                raise Exception("Failed to add reaction: Message not found")
            
            reaction = {
                "channel": channel,
                "timestamp": timestamp,
                "emoji": emoji,
                "added_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Slack reaction added: {emoji} to message {timestamp}")
            return {"ok": True, "reaction": reaction}
            
        except Exception as e:
            logger.error(f"Slack add reaction failed: {e}")
            raise
    
    async def get_channel_info(self, channel: str) -> Dict[str, Any]:
        """Get information about a channel."""
        try:
            await self._simulate_delay(factor=0.3)
            
            if not self._is_valid_channel(channel):
                raise Exception(f"Channel not found: {channel}")
            
            channel_info = self._channels[channel].copy()
            channel_info.update({
                "is_channel": True,
                "is_group": False,
                "is_im": False,
                "created": int(time.time()) - 86400,  # Created yesterday
                "creator": "U123456",
                "is_archived": False,
                "is_general": channel == "general"
            })
            
            logger.info(f"Slack channel info retrieved: #{channel}")
            return {"ok": True, "channel": channel_info}
            
        except Exception as e:
            logger.error(f"Slack get channel info failed: {e}")
            raise
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get information about a user."""
        try:
            await self._simulate_delay(factor=0.3)
            
            if user_id not in self._users:
                raise Exception(f"User not found: {user_id}")
            
            user_info = self._users[user_id].copy()
            user_info.update({
                "id": user_id,
                "team_id": "T1234567890",
                "deleted": False,
                "profile": {
                    "display_name": user_info["real_name"],
                    "email": f"{user_info['name']}@company.com",
                    "image_24": f"https://avatar.example.com/{user_id}_24.png"
                }
            })
            
            logger.info(f"Slack user info retrieved: {user_id}")
            return {"ok": True, "user": user_info}
            
        except Exception as e:
            logger.error(f"Slack get user info failed: {e}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get Slack integration metrics."""
        return {
            "total_messages_sent": self._message_count,
            "total_errors": self._error_count,
            "error_rate": (self._error_count / self._message_count) if self._message_count > 0 else 0,
            "channels_configured": len(self._channels),
            "users_configured": len(self._users),
            "webhooks_delivered": len(self._webhooks),
            "recent_messages": len(self._sent_messages)
        }
    
    def get_sent_messages(self, channel: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of sent messages, optionally filtered by channel."""
        messages = self._sent_messages
        
        if channel:
            messages = [msg for msg in messages if msg["channel"] == channel]
        
        return messages[-limit:]
    
    def get_channels(self) -> Dict[str, Dict[str, Any]]:
        """Get all configured channels."""
        return self._channels.copy()
    
    def add_channel(self, name: str, channel_id: str, members: int = 0) -> None:
        """Add a new channel configuration."""
        self._channels[name] = {
            "id": channel_id,
            "name": name,
            "members": members
        }
        logger.info(f"Added Slack channel: #{name}")
    
    def add_user(self, user_id: str, name: str, real_name: str, status: str = "active") -> None:
        """Add a new user configuration."""
        self._users[user_id] = {
            "name": name,
            "real_name": real_name,
            "status": status
        }
        logger.info(f"Added Slack user: {name}")
    
    def clear_message_history(self) -> None:
        """Clear all message history."""
        self._sent_messages.clear()
        self._webhooks.clear()
        logger.info("Slack message history cleared")
    
    def set_failure_rate(self, rate: float) -> None:
        """Set the failure rate for Slack operations."""
        self.failure_rate = max(0.0, min(1.0, rate))
        logger.info(f"Slack failure rate set to {self.failure_rate:.1%}")
    
    # Private methods
    
    async def _simulate_delay(self, factor: float = 1.0) -> None:
        """Simulate realistic Slack API response delay."""
        min_delay, max_delay = self.response_delay
        delay = random.uniform(min_delay, max_delay) * factor
        await asyncio.sleep(delay)
    
    def _should_fail(self) -> bool:
        """Determine if operation should fail based on configured rate."""
        return random.random() < self.failure_rate
    
    def _is_valid_channel(self, channel: str) -> bool:
        """Check if channel exists."""
        return channel in self._channels or channel.startswith("D")  # DM channels
    
    def _get_channel_id(self, channel: str) -> str:
        """Get channel ID from channel name."""
        if channel in self._channels:
            return self._channels[channel]["id"]
        return channel  # Assume it's already an ID
    
    def _generate_slack_error(self) -> str:
        """Generate realistic Slack API error messages."""
        errors = [
            "channel_not_found",
            "not_in_channel",
            "rate_limited",
            "invalid_auth",
            "message_too_long",
            "channel_is_archived",
            "user_not_found",
            "account_inactive",
            "missing_scope",
            "internal_error"
        ]
        return random.choice(errors)
