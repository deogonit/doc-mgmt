from typing import Type

from app.base.repository import DynamoDBBaseRepository
from app.esign.exception import EnvelopeInDbDoesntExistException
from app.esign.models.envelope import (
    EnvelopeDeleteItem,
    EnvelopeItemModel,
    EnvelopePutItem,
    EnvelopeSearchItem,
    EnvelopeUpdateItem,
)


class EnvelopeRepository(
    DynamoDBBaseRepository[
        EnvelopeItemModel,
        EnvelopeSearchItem,
        EnvelopePutItem,
        EnvelopeDeleteItem,
        EnvelopeUpdateItem
    ]
):
    """
    Table 'Envelops' will contain these columns:
        - 'id' - primary key of table. will contain uuid value
        - 'status_changed_date_time' - time when status was changed
        - 'envelope_id' - id of envelope. uuid value
        - 'envelope_status' - status of envelope. string value Documentation about statuses https://tinyurl.com/3axnwkzd
        - 'signers' - list of signers which contain list of objects with this structure:
            - 'email' - email of signer. string value
            - 'status' - status of signer. string value
            - 'recipientId' - id of recipient. number value
    """

    @property
    def delete_model(self) -> Type[EnvelopeDeleteItem]:
        return EnvelopeDeleteItem

    @property
    def base_model(self) -> Type[EnvelopeItemModel]:
        return EnvelopeItemModel

    @property
    def search_model(self) -> Type[EnvelopeSearchItem]:
        return EnvelopeSearchItem

    @property
    def put_model(self) -> Type[EnvelopePutItem]:
        return EnvelopePutItem

    @property
    def update_model(self) -> Type[EnvelopeUpdateItem]:
        return EnvelopeUpdateItem

    async def get_envelope(self, envelope_id: str) -> EnvelopeItemModel:
        envelope = await self.get_item(
            EnvelopeSearchItem(envelope_id=envelope_id)
        )
        if not envelope:
            raise EnvelopeInDbDoesntExistException(envelope_id)

        return envelope
