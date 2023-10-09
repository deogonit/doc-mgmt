from itertools import groupby
from operator import attrgetter
from typing import Any

from fastapi import HTTPException

from app.base.schema import HTTPBaseError

DESCRIPTION_NAME_FIELD = "description"


class BaseHTTPException(HTTPException):
    status_code: int
    message: str
    field_name: str | None = None

    # We mark exception as expected when we raise exception to send information to the client,
    # and it's a normal (expected) behavior, so we don't need to trigger alerts.
    # By default, we expect all custom errors, because we already handled such edge case in code,
    # and we only want to give feedback to the client
    is_expected: bool = True

    # We mark exception as ignored and don't log and notice this error
    # when exception can have sensitive data or any other specific reason
    # By default, we want to log (don't ignore) all custom errors to have visibility and history of all transactions
    is_ignored: bool = False
    if_ignored: str | None = None

    def __init__(
        self,
        *,
        status_code: int | None = None,
        message: str | None = None,
        field_value: Any | None = None,
        addition_message: str | None = None,
        headers: dict[str, Any] | None = None,
    ):
        if status_code:
            self.status_code = status_code
        if message:
            self.message = message

        self.field_value = field_value
        self.addition_message = addition_message
        detail = {
            "message": f"{self.message} {self.addition_message}" if self.addition_message else self.message
        }

        if self.field_name:
            detail["field"] = self.field_name

        if self.field_value:
            detail["value"] = self.field_value

        super().__init__(
            status_code=self.status_code,
            detail=detail,
            headers=headers
        )

    def __str__(self):
        class_name = self.__class__.__name__
        message = f"{self.message} {self.addition_message}" if self.addition_message else self.message
        return (
            f"{class_name}(status_code={self.status_code!r}, message={message!r}, "
            + f"field_name={self.field_name!r}, field_value={self.field_value!r})"
        )

    @classmethod
    def transform_to_description(cls) -> dict:
        return {
            cls.status_code: {
                DESCRIPTION_NAME_FIELD: {
                    "field": cls.field_name,
                    "message": cls.message,
                }
            }
        }


def merge_exception_descriptions(*exceptions: type[BaseHTTPException]) -> dict:
    response_description: dict[int, dict] = {}

    sorted_by_status_code = sorted(exceptions, key=attrgetter("status_code"))
    grouped_by_status_code = groupby(sorted_by_status_code, key=attrgetter("status_code"))
    for status_code, grouped_exceptions in grouped_by_status_code:
        response_description[status_code] = {
            DESCRIPTION_NAME_FIELD: " / ".join(
                [exception.message for exception in list(grouped_exceptions)]
            ),
            "model": HTTPBaseError,
        }

    return response_description
