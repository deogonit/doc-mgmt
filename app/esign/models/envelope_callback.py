from datetime import datetime
from typing import Type, TypeVar

from dateutil import parser
from pydantic import Field
from types_aiobotocore_dynamodb.type_defs import (
    DeleteItemInputRequestTypeDef,
    GetItemInputRequestTypeDef,
    PutItemInputRequestTypeDef,
    ScanInputRequestTypeDef,
    UpdateItemInputRequestTypeDef,
)

from app.base.constants import DatetimeFormats, DynamoDBColumnTypes
from app.base.models import (
    DeleteItemBaseModel,
    ItemBaseModel,
    PutItemBaseModel,
    SearchItemBaseModel,
    UpdateItemBaseModel,
)

EnvelopeCallbackItemModelType = TypeVar("EnvelopeCallbackItemModelType", bound="EnvelopeCallbackItemModel")


class EnvelopeCallbackItemModel(ItemBaseModel):
    envelope_id: str
    callback_url: str
    created_at: datetime
    expiration_time: int | None

    @classmethod
    def from_record(
        cls: Type[EnvelopeCallbackItemModelType],
        object_item: dict
    ) -> EnvelopeCallbackItemModelType | None:
        for field in cls.__fields__.keys():
            if field == "expiration_time":
                continue

            if not object_item.get(field):
                return None

        envelope_id = object_item["envelope_id"][DynamoDBColumnTypes.string.value]
        callback_url = object_item["callback_url"][DynamoDBColumnTypes.string.value]
        expiration_time = (
            int(object_item["expiration_time"][DynamoDBColumnTypes.number.value])
            if "expiration_time" in object_item else None
        )
        created_at = parser.parse(object_item["created_at"][DynamoDBColumnTypes.string.value])

        return cls(
            envelope_id=envelope_id,
            callback_url=callback_url,
            expiration_time=expiration_time,
            created_at=created_at,
        )


class EnvelopeCallbackPutItem(PutItemBaseModel):
    envelope_id: str
    callback_url: str
    expiration_time: int | None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    def to_put_item_object(self, table_name: str) -> PutItemInputRequestTypeDef:
        put_item = {
            "envelope_id": {
                DynamoDBColumnTypes.string.value: self.envelope_id
            },
            "callback_url": {
                DynamoDBColumnTypes.string.value: self.callback_url
            },
            "created_at": {
                DynamoDBColumnTypes.string.value: self.created_at.strftime(DatetimeFormats.utc_string_format)
            },
            "updated_at": {
                DynamoDBColumnTypes.string.value: ""
            }
        }

        if self.expiration_time:
            put_item.update({
                "expiration_time": {
                    DynamoDBColumnTypes.number.value: str(self.expiration_time)
                }
            })

        return {
            "TableName": table_name,
            "Item": put_item,  # type: ignore
        }


class EnvelopeCallbackSearchItem(SearchItemBaseModel):
    envelope_id: str

    def to_get_item_object(self, table_name: str) -> GetItemInputRequestTypeDef:
        return {
            "TableName": table_name,
            "Key": {
                "envelope_id": {
                    DynamoDBColumnTypes.string.value: self.envelope_id
                }
            },
        }

    def to_scan_object(self, table_name: str) -> ScanInputRequestTypeDef:
        return {
            "TableName": table_name,
            "ExpressionAttributeNames": {
                "#n_envelope_id": "envelope_id",
            },
            "ExpressionAttributeValues": {
                ":v_envelope_id": {
                    DynamoDBColumnTypes.string.value: self.envelope_id
                }
            },
            "FilterExpression": "#n_envelope_id = :v_envelope_id"
        }


class EnvelopeCallbackDeleteItem(DeleteItemBaseModel):
    envelope_id: str

    def to_delete_object(self, table_name: str) -> DeleteItemInputRequestTypeDef:
        return {
            "TableName": table_name,
            "Key": {
                "envelope_id": {
                    DynamoDBColumnTypes.string.value: self.envelope_id
                }
            }
        }


class EnvelopeCallbackUpdateItem(UpdateItemBaseModel):
    envelope_id: str
    expiration_time: int | None
    callback_url: str | None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_update_object(self, table_name: str) -> UpdateItemInputRequestTypeDef:
        expression_attribute_values = {
            ":v_updated_at": {
                DynamoDBColumnTypes.string.value: self.updated_at.strftime(
                    DatetimeFormats.utc_string_format
                )
            },
        }
        expression_attribute_names = {
            "#n_updated_at": "updated_at",
        }
        updates_expression_fields = ["#n_updated_at = :v_updated_at"]

        if self.expiration_time:
            expression_attribute_values.update({
                ":v_expiration_time": {
                    DynamoDBColumnTypes.number.value: str(self.expiration_time)
                }
            })
            expression_attribute_names.update({
                "#n_expiration_time": "expiration_time",
            })
            updates_expression_fields.append("#n_expiration_time = :v_expiration_time")

        if self.callback_url:
            expression_attribute_values.update({
                ":v_callback_url": {
                    DynamoDBColumnTypes.string.value: self.callback_url
                }
            })
            expression_attribute_names.update({
                "#n_callback_url": "callback_url",
            })
            updates_expression_fields.append("#n_callback_url = :v_callback_url")

        update_expression = ", ".join(updates_expression_fields)
        update_expression = f"SET {update_expression}"

        return {
            "TableName": table_name,
            "Key": {
                "envelope_id": {
                    DynamoDBColumnTypes.string.value: self.envelope_id
                }
            },
            "ExpressionAttributeNames": expression_attribute_names,
            "ExpressionAttributeValues": expression_attribute_values,  # type: ignore
            "UpdateExpression": update_expression
        }
