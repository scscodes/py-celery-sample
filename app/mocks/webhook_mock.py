"""Webhook Mock"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WebhookMock:
    def __init__(self): pass
    async def send_webhook(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "delivered", "webhook_id": "webhook_123"}
