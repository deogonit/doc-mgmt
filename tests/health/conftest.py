from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest_asyncio

from app.container import Container


@pytest_asyncio.fixture(scope="package", autouse=True)
async def docusign_client_mock(
    app_container: Container,
) -> AsyncGenerator[Mock, None]:
    ds_client_mock = Mock()
    ds_client_mock.is_healthy = AsyncMock(return_value=True)

    with app_container.esign_envelope_service.reset():
        with app_container.docusign_client.override(ds_client_mock):
            yield ds_client_mock
