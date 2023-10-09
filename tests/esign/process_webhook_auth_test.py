from datetime import datetime
from typing import Generator
from unittest import mock

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from jwt import PyJWTError
from pytest_mock import MockerFixture

from app.container import Container
from app.esign.auth import Auth0Authentication
from tests.esign.builders import build_webhook_event

AUTH_DOCU_SIGN_DOMAIN = "dev-1234567890abcdef.eu.auth0.com"
AUTH_DOCU_SIGN_API_AUDIENCE = "https://dev-1234567890abcdef.eu.auth0.com/api/v2/"
ESIGN_WEBHOOK_ADDRESS = "/api/v1/esign/webhook"


@pytest_asyncio.fixture(scope="function")
def mock_process_webhook_service(mocker: MockerFixture) -> Generator:
    mocker.patch("app.esign.services.ESignWebhookService.process_webhook")

    yield


@pytest_asyncio.fixture(scope="function")
def mock_config(app_container: Container) -> Generator:
    updated_config_dict = app_container.config() | {
        "auth_docu_sign": {
            "domain": AUTH_DOCU_SIGN_DOMAIN,
            "api_audience": AUTH_DOCU_SIGN_API_AUDIENCE
        }
    }

    with app_container.config.override(updated_config_dict):
        yield


@pytest.mark.asyncio
async def test_should_return200_because_auth0_domain_was_not_configured(
    client: AsyncClient,
    app_container: Container,
    mock_process_webhook_service
):
    first_request = build_webhook_event(changed_date_time=datetime.utcnow())

    with app_container.esign_webhook_service.reset():
        response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=first_request)

    assert response.status_code == status.HTTP_200_OK
    assert not response.json()  # response.json() == {}


@pytest.mark.asyncio
async def test_should_return401_because_bearer_token_wasnot_passed(
    client: AsyncClient,
    app_container: Container,
    mock_process_webhook_service,
    mock_config
):
    first_request = build_webhook_event(changed_date_time=datetime.utcnow())

    mocked_auth_service = mock.Mock()
    with app_container.webhook_auth_service.override(mocked_auth_service):
        response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=first_request)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_should_return401_because_passed_not_bearer_token(
    client: AsyncClient,
    app_container: Container,
    mock_process_webhook_service,
    mock_config
):
    first_request = build_webhook_event(changed_date_time=datetime.utcnow())
    headers = {
        "Authorization": "Authorization asdf"
    }

    mock_auth_service = mock.Mock()
    with app_container.webhook_auth_service.override(mock_auth_service):
        response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=first_request, headers=headers)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid authentication credentials"}


@pytest.mark.asyncio
async def test_should_return401_because_bearer_token_is_invalid(
    client: AsyncClient,
    app_container: Container,
    mocker: MockerFixture,
    mock_process_webhook_service,
    mock_config,
):
    mocker.patch("app.esign.auth.Auth0Authentication.verify", side_effect=PyJWTError())

    first_request = build_webhook_event(changed_date_time=datetime.utcnow())
    headers = {
        "Authorization": "Bearer asdf"
    }

    mock_auth_service = Auth0Authentication(AUTH_DOCU_SIGN_DOMAIN, AUTH_DOCU_SIGN_API_AUDIENCE)
    with app_container.webhook_auth_service.override(mock_auth_service):
        response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=first_request, headers=headers)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": {"message": "Invalid bearer token"}}


@pytest.mark.asyncio
async def test_should_return200_because_bearer_token_is_valid(
    client: AsyncClient,
    app_container: Container,
    mocker: MockerFixture,
    mock_process_webhook_service,
    mock_config,
):
    mocker.patch("app.esign.auth.Auth0Authentication.verify", return_value={})

    first_request = build_webhook_event(changed_date_time=datetime.utcnow())
    headers = {
        "Authorization": "Bearer asdf"
    }

    mock_auth_service = Auth0Authentication(AUTH_DOCU_SIGN_DOMAIN, AUTH_DOCU_SIGN_API_AUDIENCE)
    with app_container.webhook_auth_service.override(mock_auth_service):
        response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=first_request, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert not response.json()  # response.json() == {}
