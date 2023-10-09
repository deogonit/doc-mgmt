import json
import logging
import traceback
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from app.base.components import BaseEnum
from app.base.exception import BaseHTTPException
from app.new_relic import notice_error


class LogType(BaseEnum):
    request = "request"
    response = "response"
    exception = "exception"


class LoggingRoute(APIRoute):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request_id = str(uuid4())[:8]

            await self.log_request(request_id, request)
            try:
                response: Response = await original_route_handler(request)
            except Exception as exception:
                self.log_exception(request_id, request, exception)
                notice_error(exception)
                raise
            await self.log_response(request_id, request, response)

            return response

        return custom_route_handler

    async def log_request(self, request_id: str, request: Request) -> None:
        try:
            body = await request.json() if await request.body() else None
        except json.JSONDecodeError as exc:
            body = {
                "message:": "Body parsing failed",
                "exc_message": str(exc),
            }

        log_data: dict = {}

        if request.path_params:
            log_data["path_params"] = request.path_params

        if request.query_params:
            log_data["query_params"] = str(request.query_params)

        if body:
            log_data["body"] = body

        self._log(request_id, LogType.request, request, log_data)

    async def log_response(self, request_id: str, request: Request, response: Response) -> None:
        try:
            body = json.loads(response.body) if response.body else None
        except json.JSONDecodeError as exc:
            body = {
                "message:": "Body parsing failed",
                "exc_message": str(exc),
            }

        log_data = {"body": body} if body else {}

        self._log(request_id, LogType.response, request, log_data)

    def log_exception(self, request_id: str, request: Request, exception: Exception) -> None:
        log_data = {
            "traceback": traceback.format_exception(exception),
            "is_expected": True,
            "is_ignored": False,
        }

        if isinstance(exception, BaseHTTPException):
            log_data.update({
                "is_expected": exception.is_expected,
                "is_ignored": exception.is_ignored,
            })
            if exception.is_ignored:
                log_data["traceback"] = exception.if_ignored
        elif isinstance(exception, RequestValidationError):
            log_data["is_expected"] = True

        self._log(request_id, LogType.exception, request, log_data)

    def _log(
        self,
        request_id: str,
        log_type: LogType,
        request: Request,
        log_data: dict,
    ) -> None:
        host, port = request.client.host, request.client.port  # type: ignore
        address = f"{host}:{port}" if request.client else None
        log = '{address} - "{method} {path}" {request_id} {log_type}_data {log_data}'.format(
            request_id=request_id,
            address=address,
            method=request.method,
            path=request.url.path,
            log_type=log_type.value,
            log_data=json.dumps(log_data),
        )
        self._logger.info(log)
