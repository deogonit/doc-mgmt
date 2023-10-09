from functools import wraps
from typing import Callable

from fastapi.exceptions import RequestValidationError
from newrelic import agent as nr_agent

from app.base.components import BaseEnum
from app.base.exception import BaseHTTPException

TRANSACTION_PREFIX = "Python"


class TransactionGroupName(BaseEnum):
    doc_gen = "DocGen"
    esign = "ESign"


def track_transaction(transaction_group: TransactionGroupName | None = None) -> Callable:

    def route_function_wrapper(route_function: Callable) -> Callable:

        @wraps(route_function)
        async def wrapper(*args, **kwargs):
            transaction = nr_agent.current_transaction(active_only=True)

            if transaction and transaction_group:
                group_name = f"{TRANSACTION_PREFIX}/{transaction_group.value}"
                nr_agent.set_transaction_name(transaction.name, group=group_name)

            return await route_function(*args, **kwargs)

        return wrapper

    return route_function_wrapper


def ignore_transaction(route_function: Callable) -> Callable:

    @wraps(route_function)
    async def wrapper(*args, **kwargs):
        nr_agent.ignore_transaction(flag=True)

        return await route_function(*args, **kwargs)

    return wrapper


def wrapp_web_transaction(function: Callable) -> Callable:
    transaction = nr_agent.current_transaction(active_only=True)

    if transaction is None:
        return function

    return nr_agent.WebTransactionWrapper(function, name=transaction.name)


def notice_error(exception: Exception) -> None:
    if isinstance(exception, BaseHTTPException):
        nr_agent.notice_error(
            expected=exception.is_expected,
            ignore=exception.is_ignored,
        )
    elif isinstance(exception, RequestValidationError):
        nr_agent.notice_error(expected=True)
    else:
        nr_agent.notice_error()
