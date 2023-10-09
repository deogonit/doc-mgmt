from typing import Final

from app.base.components import BaseEnum


class DynamoDBColumnTypes(BaseEnum):
    string: Final = "S"
    byte: Final = "B"
    number: Final = "N"
    boolean: Final = "BOOL"
    map: Final = "M"
    list: Final = "L"


class DatetimeFormats:
    utc_string_format = "%Y-%m-%dT%H:%M:%S.%fZ"  # noqa: WPS323
