from datetime import datetime
from typing import Any, ClassVar, Type, TypeVar

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
    DBBaseModel,
    DeleteItemBaseModel,
    ItemBaseModel,
    PutItemBaseModel,
    SearchItemBaseModel,
    UpdateItemBaseModel,
)

SignerItemType = TypeVar("SignerItemType", bound="SignerItem")
DocumentItemType = TypeVar("DocumentItemType", bound="DocumentItem")
EnvelopeItemModelType = TypeVar("EnvelopeItemModelType", bound="EnvelopeItemModel")


class SignerItem(DBBaseModel):
    email: str
    recipient_id: str
    recipient_id_guid: str
    status: str

    def to_put_item_object(self) -> dict:
        return {
            DynamoDBColumnTypes.map: {
                "email": {
                    DynamoDBColumnTypes.string.value: self.email
                },
                "recipient_id": {
                    DynamoDBColumnTypes.string.value: self.recipient_id
                },
                "recipient_id_guid": {
                    DynamoDBColumnTypes.string.value: self.recipient_id_guid
                },
                "status": {
                    DynamoDBColumnTypes.string.value: self.status
                }
            }
        }

    @classmethod
    def from_record(cls: Type[SignerItemType], object_item: dict) -> SignerItemType | None:
        if not object_item:
            return None

        signer_data = object_item[DynamoDBColumnTypes.map.value]

        return cls(
            email=signer_data["email"][DynamoDBColumnTypes.string.value],
            recipient_id=signer_data["recipient_id"][DynamoDBColumnTypes.string.value],
            recipient_id_guid=signer_data["recipient_id_guid"][DynamoDBColumnTypes.string.value],
            status=signer_data["status"][DynamoDBColumnTypes.string.value],
        )


class DocumentItem(DBBaseModel):
    document_id: str
    document_id_guid: str
    name: str
    uri: str
    order: int
    document_path: str | None
    document_bucket_name: str | None

    def to_put_item_object(self) -> dict:
        main_object = {
            DynamoDBColumnTypes.map: {
                "document_id": {
                    DynamoDBColumnTypes.string.value: self.document_id
                },
                "document_id_guid": {
                    DynamoDBColumnTypes.string.value: self.document_id_guid
                },
                "name": {
                    DynamoDBColumnTypes.string.value: self.name
                },
                "uri": {
                    DynamoDBColumnTypes.string.value: self.uri
                },
                # if value has number type, we should convert value to string
                "order": {
                    DynamoDBColumnTypes.number.value: str(self.order)
                }
            }
        }

        if self.document_path:
            main_object[DynamoDBColumnTypes.map].update({
                "document_path": {
                    DynamoDBColumnTypes.string.value: self.document_path
                }
            })

        if self.document_bucket_name:
            main_object[DynamoDBColumnTypes.map].update({
                "document_bucket_name": {
                    DynamoDBColumnTypes.string.value: self.document_bucket_name
                }
            })

        return main_object

    @classmethod
    def from_record(cls: Type[DocumentItemType], object_item: dict) -> DocumentItemType | None:
        if not object_item:
            return None

        doc_data = object_item[DynamoDBColumnTypes.map.value]

        document_path = (
            doc_data["document_path"][DynamoDBColumnTypes.string.value]
            if "document_path" in doc_data else None
        )
        document_bucket_name = (
            doc_data["document_bucket_name"][DynamoDBColumnTypes.string.value]
            if "document_bucket_name" in doc_data else None
        )

        return cls(
            document_id=doc_data["document_id"][DynamoDBColumnTypes.string.value],
            document_id_guid=doc_data["document_id_guid"][DynamoDBColumnTypes.string.value],
            name=doc_data["name"][DynamoDBColumnTypes.string.value],
            uri=doc_data["uri"][DynamoDBColumnTypes.string.value],
            order=doc_data["order"][DynamoDBColumnTypes.number.value],
            document_path=document_path,
            document_bucket_name=document_bucket_name,
        )


class EnvelopeItemModel(ItemBaseModel):
    envelope_id: str
    envelope_status: str
    status_changed_date_time: datetime
    signers: list[SignerItem] | None
    documents: list[DocumentItem] | None
    expiration_time: int | None

    @classmethod
    def from_record(cls: Type[EnvelopeItemModelType], object_item: dict) -> EnvelopeItemModelType | None:
        for field in ("envelope_id", "envelope_status", "status_changed_date_time"):
            if not object_item.get(field):
                return None

        envelope_id = object_item["envelope_id"][DynamoDBColumnTypes.string.value]
        envelope_status = object_item["envelope_status"][DynamoDBColumnTypes.string.value]
        status_changed_date_time = parser.parse(
            object_item["status_changed_date_time"][DynamoDBColumnTypes.string.value]
        )
        expiration_time = (
            int(object_item["expiration_time"][DynamoDBColumnTypes.number.value])
            if "expiration_time" in object_item else None
        )

        signers = [
            SignerItem.from_record(signer_obj)
            for signer_obj in object_item["signers"][DynamoDBColumnTypes.list.value]
        ] if "signers" in object_item else None

        documents = [
            DocumentItem.from_record(document_obj)
            for document_obj in object_item["documents"][DynamoDBColumnTypes.list.value]
        ] if "documents" in object_item else None

        return cls(
            envelope_id=envelope_id,
            envelope_status=envelope_status,
            status_changed_date_time=status_changed_date_time,
            signers=signers,
            documents=documents,
            expiration_time=expiration_time,
        )


class EnvelopePutItem(PutItemBaseModel):
    envelope_id: str
    envelope_status: str
    status_changed_date_time: datetime
    signers: list[SignerItem] | None
    documents: list[DocumentItem] | None
    expiration_time: int | None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    def to_put_item_object(self, table_name: str) -> PutItemInputRequestTypeDef:
        put_item: dict[str, Any] = {
            "envelope_id": {
                DynamoDBColumnTypes.string.value: self.envelope_id
            },
            "status_changed_date_time": {
                DynamoDBColumnTypes.string.value: self.status_changed_date_time.strftime(
                    DatetimeFormats.utc_string_format
                )
            },
            "envelope_status": {
                DynamoDBColumnTypes.string.value: self.envelope_status
            },
            "created_at": {
                DynamoDBColumnTypes.string.value: self.created_at.strftime(DatetimeFormats.utc_string_format)
            },
            "updated_at": {
                DynamoDBColumnTypes.string.value: ""
            },
        }

        if self.signers is not None:
            put_item["signers"] = {
                DynamoDBColumnTypes.list.value: [
                    signer.to_put_item_object()
                    for signer in self.signers
                ]
            }

        if self.documents is not None:
            put_item["documents"] = {
                DynamoDBColumnTypes.list.value: [
                    document.to_put_item_object()
                    for document in self.documents
                ]
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


class EnvelopeSearchItem(SearchItemBaseModel):
    envelope_id: str
    envelope_id_string_literal: ClassVar[str] = "envelope_id"

    def to_get_item_object(self, table_name: str) -> GetItemInputRequestTypeDef:
        return {
            "TableName": table_name,
            "Key": {
                self.envelope_id_string_literal: {
                    DynamoDBColumnTypes.string.value: self.envelope_id
                }
            },
        }

    def to_scan_object(self, table_name: str) -> ScanInputRequestTypeDef:
        return {
            "TableName": table_name,
            "ExpressionAttributeNames": {
                "#n_envelope_id": self.envelope_id_string_literal,
            },
            "ExpressionAttributeValues": {
                ":v_envelope_id": {
                    DynamoDBColumnTypes.string.value: self.envelope_id
                }
            },
            "FilterExpression": "#n_envelope_id = :v_envelope_id"
        }


class EnvelopeDeleteItem(DeleteItemBaseModel):
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


class EnvelopeUpdateItem(UpdateItemBaseModel):
    envelope_id: str
    envelope_status: str
    signers: list[SignerItem]
    status_changed_date_time: datetime
    documents: list[DocumentItem]
    expiration_time: int | None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_update_object(self, table_name: str) -> UpdateItemInputRequestTypeDef:
        signers = [
            signer.to_put_item_object()
            for signer in self.signers
        ]
        documents = [
            document.to_put_item_object()
            for document in self.documents
        ]

        expression_attribute_values = {
            ":v_envelope_status": {
                DynamoDBColumnTypes.string.value: self.envelope_status
            },
            ":v_signers": {
                DynamoDBColumnTypes.list.value: signers,
            },
            ":v_status_changed_date_time": {
                DynamoDBColumnTypes.string.value: self.status_changed_date_time.strftime(
                    DatetimeFormats.utc_string_format
                )
            },
            ":v_documents": {
                DynamoDBColumnTypes.list.value: documents,
            },
            ":v_updated_at": {
                DynamoDBColumnTypes.string.value: self.updated_at.strftime(
                    DatetimeFormats.utc_string_format
                )
            },
        }
        expression_attribute_names = {
            "#n_envelope_status": "envelope_status",
            "#n_signers": "signers",
            "#n_documents": "documents",
            "#n_status_changed_date_time": "status_changed_date_time",
            "#n_updated_at": "updated_at",
        }
        update_expression = (
            "SET #n_envelope_status = :v_envelope_status, "
            + "#n_signers = :v_signers, "
            + "#n_status_changed_date_time = :v_status_changed_date_time, "
            + "#n_documents = :v_documents, "
            + "#n_updated_at = :v_updated_at"
        )

        if self.expiration_time:
            expression_attribute_values.update({
                ":v_expiration_time": {
                    DynamoDBColumnTypes.number.value: str(self.expiration_time)
                }
            })
            expression_attribute_names.update({
                "#n_expiration_time": "expiration_time",
            })
            update_expression = (
                "SET #n_envelope_status = :v_envelope_status, "
                + "#n_signers = :v_signers, "
                + "#n_status_changed_date_time = :v_status_changed_date_time, "
                + "#n_documents = :v_documents, "
                + "#n_updated_at = :v_updated_at, "
                + "#n_expiration_time = :v_expiration_time"
            )

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
