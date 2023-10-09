import uuid
from datetime import datetime
from typing import Type, TypeVar

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

DocumentItemModelType = TypeVar("DocumentItemModelType", bound="DocumentItemModel")


class DocumentItemModel(ItemBaseModel):
    bucket: str
    result_file: str

    @classmethod
    def from_record(cls: Type[DocumentItemModelType], object_item: dict) -> DocumentItemModelType | None:
        if not object_item.get("result") or not object_item.get("bucket"):
            return None

        document_path = object_item["result"][DynamoDBColumnTypes.string]
        document_bucket = object_item["bucket"][DynamoDBColumnTypes.string]
        return cls(bucket=document_bucket, result_file=document_path)


class DocumentPutItem(PutItemBaseModel):
    item_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    etags: list[str]
    bucket: str
    hashed_request: str
    result_file: str
    app_version: str
    expiration_time: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    def to_put_item_object(self, table_name: str) -> PutItemInputRequestTypeDef:
        return {
            "TableName": "Studies",
            "Item": {
                "study_number": {
                    "S": "CPK-22-0234"
                },
                "bio_eln_number": {
                    "S": ""
                },
                "study_number": {
                    "S": "CPK-22-0234"
                },
                "created_by": {
                    "M": {
                        "id": {
                            "S": "123"
                        },
                        "first_name": {
                            "S": "FirstName"
                        },
                        "last_name": {
                            "S": "LastName"
                        },
                    }
                },
                "created_at": {
                    "S": "2020-03-20T14:28:23.382748"
                },
                "updated_by": {
                    "M": {
                        "id": {
                            "S": "123"
                        },
                        "first_name": {
                            "S": "FirstName"
                        },
                        "last_name": {
                            "S": "LastName"
                        },
                    }
                },
                "updated_at": {
                    "S": "2020-03-20T15:28:23.382748"
                },
                "status": {
                    "S": "preprocessed"
                },
                "type": {
                    "S": "mouse_trap"
                },
                "files": {
                    "L": [
                        {
                            "key": {
                                "S": "directory/ab1c05ad-192e-4e3d-90ea-6da542b872c1.xlsx"
                            },
                            "bucket": {
                                "S": "studies"
                            },
                            "status": {
                                "S": "preprocessed"
                            },
                            "created_at": {
                                "S": "2020-03-20T14:28:23.382748"
                            },
                            "created_by": {
                                "M": {
                                    "id": {
                                        "S": "123"
                                    },
                                    "first_name": {
                                        "S": "FirstName"
                                    },
                                    "last_name": {
                                        "S": "LastName"
                                    },
                                }
                            }
                        }
                    ]
                }
            }
        }
        return {
            "TableName": table_name,
            "Item": {
                "id": {
                    DynamoDBColumnTypes.string.value: str(self.item_id)
                },
                "etags": {
                    DynamoDBColumnTypes.string.value: ",".join(self.etags)
                },
                "bucket": {
                    DynamoDBColumnTypes.string.value: self.bucket
                },
                "data": {
                    DynamoDBColumnTypes.byte.value: self.hashed_request.encode("utf-8")
                },
                "result": {
                    DynamoDBColumnTypes.string.value: self.result_file
                },
                "expiration_time": {
                    DynamoDBColumnTypes.number.value: str(self.expiration_time)
                },
                "app_version": {
                    DynamoDBColumnTypes.string.value: self.app_version
                },
                "created_at": {
                    DynamoDBColumnTypes.string.value: self.created_at.strftime(DatetimeFormats.utc_string_format)
                },
                "updated_at": {
                    DynamoDBColumnTypes.string.value: ""
                },
            },
        }


class DocumentSearchItem(SearchItemBaseModel):
    etags: list[str]
    bucket: str
    hashed_request: str
    app_version: str

    def to_get_item_object(self, table_name: str) -> GetItemInputRequestTypeDef:
        raise NotImplementedError("Document table doesn't support get_item right now")

    def to_scan_object(self, table_name: str) -> ScanInputRequestTypeDef:
        return {
            "TableName": table_name,
            "ExpressionAttributeNames": {
                "#n_data": "data",
                "#n_etags": "etags",
                "#n_bucket": "bucket",
                "#n_app_version": "app_version",
            },
            "ExpressionAttributeValues": {
                ":v_data": {
                    DynamoDBColumnTypes.byte.value: self.hashed_request.encode("utf-8")
                },
                ":v_etags": {
                    DynamoDBColumnTypes.string.value: ",".join(self.etags)
                },
                ":v_bucket": {
                    DynamoDBColumnTypes.string.value: self.bucket
                },
                ":v_app_version": {
                    DynamoDBColumnTypes.string.value: self.app_version
                },
            },
            "FilterExpression": (
                "#n_data = :v_data AND #n_etags = :v_etags AND #n_bucket = :v_bucket AND "
                + "#n_app_version = :v_app_version"
            )
        }


class DocumentDeleteItem(DeleteItemBaseModel):
    item_id: str

    def to_delete_object(self, table_name: str) -> DeleteItemInputRequestTypeDef:
        return {
            "TableName": table_name,
            "Key": {
                "id": {
                    DynamoDBColumnTypes.string.value: self.item_id
                }
            }
        }


class DocumentUpdateItem(UpdateItemBaseModel):
    def to_update_object(self, table_name: str) -> UpdateItemInputRequestTypeDef:
        raise NotImplementedError()
