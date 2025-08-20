"""SMS Service Mock"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SMSMock:
    def __init__(self): pass
    async def send_sms(self, to: str, message: str) -> Dict[str, Any]:
        return {"status": "sent", "message_id": "sms_123"}
