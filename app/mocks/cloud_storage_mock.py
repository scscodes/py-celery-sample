"""Cloud Storage Mock"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CloudStorageMock:
    def __init__(self): pass
    async def upload_file(self, bucket: str, key: str, data: bytes) -> Dict[str, Any]:
        return {"status": "uploaded", "url": f"https://mock-storage.com/{bucket}/{key}"}
