import asyncio
from typing import Any, Callable, Coroutine
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, status
from httpx import Request, Response

from app.api_client.gotenberg_api_client import GotenbergApiClient


@pytest.fixture(scope="module")
def gotenberg_url(global_settings: dict) -> str:
    return global_settings["gotenberg"]["url"]


@pytest.fixture(scope="module")
def gotenberg_max_attempt(global_settings: dict) -> str:
    return global_settings["gotenberg"]["max_attempt"]


def get_response(fail_count: int, sleep_time: float = 0) -> Callable[..., Coroutine[Any, Any, Response]]:
    attempt = 1

    async def _get_response(*args, **kwargs) -> Response:
        nonlocal attempt  # noqa: WPS420

        await asyncio.sleep(sleep_time)

        if fail_count < attempt:
            return Response(
                status_code=status.HTTP_200_OK,
                text="Ok",
                request=Request("post", "localhost"),
            )

        attempt += 1

        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            text="Internal Server Error",
            request=Request("post", "localhost"),
        )

    return _get_response


@pytest.mark.asyncio
async def test_should_get_response_for_docx_on_valid_attempt_number(gotenberg_url: str, gotenberg_max_attempt: int):
    gotenberg_service = GotenbergApiClient(base_url=gotenberg_url, headers={})

    client = Mock()
    client.request = get_response(fail_count=gotenberg_max_attempt - 1)
    gotenberg_service.client = client

    resp = await gotenberg_service.convert_docx_to_pdf(Mock(), "file.docx")

    assert resp.read() == b"Ok"


@pytest.mark.asyncio
async def test_should_raise_error_for_docx_on_max_attempt_exceeded(gotenberg_url: str, gotenberg_max_attempt: int):
    gotenberg_service = GotenbergApiClient(base_url=gotenberg_url, headers={})

    client = Mock()
    client.request = get_response(fail_count=gotenberg_max_attempt)
    gotenberg_service.client = client

    try:
        await gotenberg_service.convert_docx_to_pdf(Mock(), "file.docx")
    except HTTPException as exc:
        assert exc.status_code == status.HTTP_408_REQUEST_TIMEOUT
        assert exc.detail == {
            "message": "Document converting failed. Timeout exceeded.",
        }
    else:
        raise AssertionError()


@pytest.mark.asyncio
async def test_should_get_response_for_html_on_valid_attempt_number(gotenberg_url: str, gotenberg_max_attempt: int):
    gotenberg_service = GotenbergApiClient(base_url=gotenberg_url, headers={})

    client = Mock()
    client.request = get_response(fail_count=gotenberg_max_attempt - 1)
    gotenberg_service.client = client

    resp = await gotenberg_service.convert_html_to_pdf(Mock(), Mock(), Mock())

    assert resp.read() == b"Ok"


@pytest.mark.asyncio
async def test_should_raise_error_for_html_on_max_attempt_exceeded(gotenberg_url: str, gotenberg_max_attempt: int):
    gotenberg_service = GotenbergApiClient(base_url=gotenberg_url, headers={})

    client = Mock()
    client.request = get_response(fail_count=gotenberg_max_attempt)
    gotenberg_service.client = client

    try:
        await gotenberg_service.convert_html_to_pdf(Mock(), Mock(), Mock())
    except HTTPException as exc:
        assert exc.status_code == status.HTTP_408_REQUEST_TIMEOUT
        assert exc.detail == {
            "message": "Document converting failed. Timeout exceeded.",
        }
    else:
        raise AssertionError()
