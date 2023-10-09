from typing import Type

from app.base.repository import DynamoDBBaseRepository
from app.doc_generation.models.document import (
    DocumentDeleteItem,
    DocumentItemModel,
    DocumentPutItem,
    DocumentSearchItem,
    DocumentUpdateItem,
)


class DocumentRepository(
    DynamoDBBaseRepository[
        DocumentItemModel,
        DocumentSearchItem,
        DocumentPutItem,
        DocumentDeleteItem,
        DocumentUpdateItem
    ]
):
    """
    Table 'Documents' will contain these columns:
        'id' - primary key of table. will contain uuid value
        'data' - compressed and encoded data to md5
        'bucket' - name of bucket where template is exists
        'etags' - list of etags of templates
        'result' - path to result document
    """

    @property
    def delete_model(self) -> Type[DocumentDeleteItem]:
        return DocumentDeleteItem

    @property
    def base_model(self) -> Type[DocumentItemModel]:
        return DocumentItemModel

    @property
    def search_model(self) -> Type[DocumentSearchItem]:
        return DocumentSearchItem

    @property
    def put_model(self) -> Type[DocumentPutItem]:
        return DocumentPutItem

    @property
    def update_model(self) -> Type[DocumentUpdateItem]:
        return DocumentUpdateItem
