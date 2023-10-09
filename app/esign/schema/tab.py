from typing import Type

import docusign_esign

from app.base.schema import ApiBaseModel
from app.esign.schema.tab_fields import (
    DSAbstractSignTab,
    DSAbstractTab,
    DSAbstractTextTab,
    DSBaseFields,
    DSCondFields,
    DSMetaFields,
    DSTextFields,
)


class DSInitialHereTab(DSAbstractSignTab[docusign_esign.InitialHere]):
    @property
    def ds_tab_class(self) -> Type[docusign_esign.InitialHere]:
        return docusign_esign.InitialHere


class DSSignHereTab(DSAbstractSignTab[docusign_esign.SignHere]):
    @property
    def ds_tab_class(self) -> Type[docusign_esign.SignHere]:
        return docusign_esign.SignHere


class DSFullNameTab(DSAbstractTab[docusign_esign.FullName], DSTextFields, DSMetaFields, DSCondFields, DSBaseFields):
    @property
    def ds_tab_class(self) -> Type[docusign_esign.FullName]:
        return docusign_esign.FullName


class DSTextTab(DSAbstractTextTab[docusign_esign.Text]):
    @property
    def ds_tab_class(self) -> Type[docusign_esign.Text]:
        return docusign_esign.Text


class DSEmailTab(DSAbstractTextTab[docusign_esign.Email]):
    @property
    def ds_tab_class(self) -> Type[docusign_esign.Email]:
        return docusign_esign.Email


class DSTitleTab(DSAbstractTextTab[docusign_esign.Title]):
    @property
    def ds_tab_class(self) -> Type[docusign_esign.Title]:
        return docusign_esign.Title


class DSDateTab(DSAbstractTextTab[docusign_esign.Date]):
    @property
    def ds_tab_class(self) -> Type[docusign_esign.Date]:
        return docusign_esign.Date


class DSNumberTab(DSAbstractTextTab[docusign_esign.Number]):
    @property
    def ds_tab_class(self) -> Type[docusign_esign.Number]:
        return docusign_esign.Number


class DSListItem(ApiBaseModel):
    selected: bool | None
    text: str
    value: str  # noqa: WPS110


class DSListTab(DSAbstractTextTab[docusign_esign.List]):
    list_items: list[DSListItem]

    @property
    def ds_tab_class(self) -> Type[docusign_esign.List]:
        return docusign_esign.List
