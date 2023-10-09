from typing import Type

import docusign_esign

from app.esign.schema.tab_fields import (
    DSAbstractTab,
    DSBaseFields,
    DSCondFields,
    DSMetaFields,
    DSStateFields,
    DSTextFields,
)


class DSRadioTab(DSAbstractTab[docusign_esign.Radio], DSTextFields):
    anchor_string: str | None
    anchor_units: str | None = "pixels"
    anchor_x_offset: int | None
    anchor_y_offset: int | None

    page_number: int | None
    x_position: int | None
    y_position: int | None

    tab_id: str | None

    selected: bool | None

    @property
    def ds_tab_class(self) -> Type[docusign_esign.Radio]:
        return docusign_esign.Radio


class DSRadioGroupTab(DSAbstractTab[docusign_esign.RadioGroup], DSCondFields):
    document_id: int
    group_name: str
    radios: list[DSRadioTab]

    @property
    def ds_tab_class(self) -> Type[docusign_esign.RadioGroup]:
        return docusign_esign.RadioGroup


class DSCheckboxTab(DSAbstractTab[docusign_esign.Checkbox], DSStateFields, DSMetaFields, DSCondFields, DSBaseFields):
    font: str | None
    font_size: str | None

    @property
    def ds_tab_class(self) -> Type[docusign_esign.Checkbox]:
        return docusign_esign.Checkbox
