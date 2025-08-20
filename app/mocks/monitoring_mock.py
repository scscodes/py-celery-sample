"""Monitoring Service Mock"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MonitoringMock:
    def __init__(self): pass
    async def send_metric(self, metric_name: str, value: float, tags: Dict = None) -> Dict[str, Any]:
        return {"status": "recorded", "metric": metric_name, "value": value}
