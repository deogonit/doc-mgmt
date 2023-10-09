
from fastapi import Depends
from fastapi.security import APIKeyHeader

from app.auth.exception import InvalidApiKeyException
from app.config import settings

auth_scheme = APIKeyHeader(name="Authorization")


def verify_api_key(api_key: str = Depends(auth_scheme)):
    known_keys = settings.auth.api_keys

    if not known_keys:
        return

    if api_key not in known_keys:
        raise InvalidApiKeyException(api_key)
