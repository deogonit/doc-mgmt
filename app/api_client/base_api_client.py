import logging
from types import MappingProxyType

from httpx import AsyncClient

from app.base.components import BaseEnum

DEFAULT_HEADERS = MappingProxyType({
    "Content-Type": "application/json",
})


class HTTPMethod(BaseEnum):
    post = "POST"
    get = "GET"
    patch = "PATCH"
    put = "PUT"
    delete = "DELETE"


def enhance_query_params(query: dict) -> dict:
    return {
        query_key: query_value
        for query_key, query_value in query.items()
        if query_value is not None
    }


class BaseApiClient:
    def __init__(
        self,
        base_url: str,
        headers: dict | None = None,
        auth_token: str | None = None,
    ) -> None:
        self.base_url = base_url
        self.headers = DEFAULT_HEADERS.copy() if headers is None else headers

        if auth_token:
            self.headers.update({"Authorization": auth_token})

        self.client = AsyncClient(headers=self.headers)
        self._logger = logging.getLogger(self.__class__.__name__)

    attempts = 5

    async def close(self) -> None:
        await self.client.aclose()
