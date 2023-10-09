from abc import ABC, abstractmethod
from typing import Generic, Type, TypeVar

from pydantic import Field

from app.base.schema import ApiBaseModel

GenericDSTabClass = TypeVar("GenericDSTabClass")


class DSAbstractTab(Generic[GenericDSTabClass], ApiBaseModel, ABC):
    @property
    @abstractmethod
    def ds_tab_class(self) -> Type[GenericDSTabClass]:
        """DocuSign tab class"""

    def to_ds_tab(self) -> GenericDSTabClass:
        return self.ds_tab_class(**self.dict())


class DSBaseFields(ApiBaseModel):
    anchor_string: str | None
    anchor_units: str | None = "pixels"
    anchor_x_offset: int | None
    anchor_y_offset: int | None

    document_id: int | None
    page_number: int | None
    x_position: int | None
    y_position: int | None

    tab_id: str | None
    tab_label: str | None


class DSCondFields(ApiBaseModel):
    conditional_parent_label: str | None
    conditional_parent_value: str | None


class DSMetaFields(ApiBaseModel):
    name: str | None
    height: int | None
    width: int | None


class DSStateFields(ApiBaseModel):
    required: bool | None
    locked: bool | None


class DSTextFields(ApiBaseModel):
    font: str | None
    font_size: str | None = Field(default=None, description='Supports values like "size8"', regex=r"^size\d{1,3}$")
    value: str | None  # noqa: WPS110


class DSAbstractTextTab(  # noqa: WPS215
    DSAbstractTab[GenericDSTabClass],
    DSTextFields,
    DSStateFields,
    DSMetaFields,
    DSCondFields,
    DSBaseFields,
    ABC
):
    max_length: str | None


class DSAbstractSignTab(DSAbstractTab[GenericDSTabClass], DSMetaFields, DSCondFields, DSBaseFields, ABC):
    scale_value: float | None
