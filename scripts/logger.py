import logging
import os

is_debug = bool(int(os.environ.get("DEBUG", 0)))
logging.basicConfig(
    format="%(asctime)s.%(msecs)d | %(levelname)s | %(name)s | %(message)s",  # noqa: WPS323
    datefmt="%Y-%m-%d %H:%M:%S",  # noqa: WPS323
    level=logging.DEBUG if is_debug else logging.INFO
)  # noqa: WPS323


def get_logger() -> logging.Logger:
    return logging.getLogger("scripts")
