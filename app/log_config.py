import logging
import os
from logging import config as logging_config
from types import MappingProxyType
from typing import Any

console_handler = {
    "formatter": "default",
    "class": "logging.StreamHandler",
    "stream": "ext://sys.stdout",
    "level": os.getenv("LOGGER_LEVEL", "INFO"),
}

log_file_path = os.getenv("LOG_FILE_PATH", None)
file_handler = {
    "formatter": "default",
    "class": "logging.handlers.RotatingFileHandler",
    "filename": log_file_path,
    "maxBytes": 100000000,
    "backupCount": 1,
    "level": os.getenv("LOGGER_LEVEL", "INFO"),
} if log_file_path else None

handlers: dict[str, Any] = {
    "console": console_handler
}
if log_file_path is not None:
    handlers["file"] = file_handler

LOG_CONFIG = MappingProxyType({
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "format": "%(asctime)s.%(msecs)d | %(levelname)s | %(name)s | %(message)s",  # noqa: WPS323
            "datefmt": "%Y-%m-%d %H:%M:%S"  # noqa: WPS323
        }
    },
    "handlers": handlers,
    "root": {
        "handlers": handlers.keys(),
        "level": os.getenv("LOGGER_LEVEL", "INFO")
    },
    "loggers": {
        logger_name: {
            "propagate": True
        }
        for logger_name in (
            "gunicorn",
            "gunicorn.access",
            "gunicorn.error",
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
        )
    },
})

logging_config.dictConfig(dict(LOG_CONFIG))

# Disable future loggers, prevent them from unnecessary logs
logging.getLogger("httpx").setLevel(logging.WARNING)
