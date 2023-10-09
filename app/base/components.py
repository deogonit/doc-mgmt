import enum


class ExtendedEnum(enum.Enum):
    @classmethod
    def get_names(cls):
        return [enum_item.name for enum_item in cls]

    @classmethod
    def get_values(cls):
        return [enum_item.value for enum_item in cls]

    @classmethod
    def get_dict(cls) -> dict:
        return {
            enum_property.name: enum_property.value for enum_property in cls
        }

    @classmethod
    def get_reversed_dict(cls) -> dict:
        return {
            enum_property.value: enum_property.name for enum_property in cls
        }


class BaseEnum(str, ExtendedEnum):  # noqa: WPS600
    """
    BaseEnum class for all enums
    """
