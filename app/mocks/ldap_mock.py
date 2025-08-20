"""LDAP/Active Directory Mock"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class LDAPMock:
    def __init__(self): pass
    async def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        return {"authenticated": True, "user_dn": f"cn={username},ou=users,dc=example,dc=com"}
