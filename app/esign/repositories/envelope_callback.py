from typing import Type

from app.base.repository import DynamoDBBaseRepository
from app.esign.models.envelope_callback import (
    EnvelopeCallbackDeleteItem,
    EnvelopeCallbackItemModel,
    EnvelopeCallbackPutItem,
    EnvelopeCallbackSearchItem,
    EnvelopeCallbackUpdateItem,
)


class EnvelopeCallbackRepository(
    DynamoDBBaseRepository[
        EnvelopeCallbackItemModel,
        EnvelopeCallbackSearchItem,
        EnvelopeCallbackPutItem,
        EnvelopeCallbackDeleteItem,
        EnvelopeCallbackUpdateItem
    ]
):
    """
    Table 'EnvelopeCallbacks' will contain these columns:
        - 'envelope_id' - id of envelope. uuid value
        - 'created_at' - time when record was created
        - 'callback_url' - url of application which will receive data from DocMGMT service
    """

    @property
    def delete_model(self) -> Type[EnvelopeCallbackDeleteItem]:
        return EnvelopeCallbackDeleteItem

    @property
    def base_model(self) -> Type[EnvelopeCallbackItemModel]:
        return EnvelopeCallbackItemModel

    @property
    def search_model(self) -> Type[EnvelopeCallbackSearchItem]:
        return EnvelopeCallbackSearchItem

    @property
    def put_model(self) -> Type[EnvelopeCallbackPutItem]:
        return EnvelopeCallbackPutItem

    @property
    def update_model(self) -> Type[EnvelopeCallbackUpdateItem]:
        return EnvelopeCallbackUpdateItem
