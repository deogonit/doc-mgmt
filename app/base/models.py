from abc import ABC, abstractmethod
from typing import Type, TypeVar

from humps import camelize
from pydantic import BaseModel
from types_aiobotocore_dynamodb.type_defs import (
    DeleteItemInputRequestTypeDef,
    GetItemInputRequestTypeDef,
    PutItemInputRequestTypeDef,
    ScanInputRequestTypeDef,
    UpdateItemInputRequestTypeDef,
)

ItemBaseModelType = TypeVar("ItemBaseModelType", bound="ItemBaseModel")


class DBBaseModel(BaseModel):
    class Config:
        alias_generator = camelize
        allow_population_by_field_name = True


class PutItemBaseModel(DBBaseModel, ABC):
    @abstractmethod
    def to_put_item_object(self, table_name: str) -> PutItemInputRequestTypeDef:
        """Should implement method which will return prepared item for saving item in table"""


class SearchItemBaseModel(DBBaseModel, ABC):

    @abstractmethod
    def to_get_item_object(self, table_name: str) -> GetItemInputRequestTypeDef:
        """Should implement method which will return prepared object for getting item in table by id"""

    @abstractmethod
    def to_scan_object(self, table_name: str) -> ScanInputRequestTypeDef:
        """Should implement method which will return prepared object for scanning item in table"""


class DeleteItemBaseModel(DBBaseModel, ABC):
    @abstractmethod
    def to_delete_object(self, table_name: str) -> DeleteItemInputRequestTypeDef:
        """Should implement method which will return prepared object for deleting item in table"""


class UpdateItemBaseModel(DBBaseModel, ABC):
    @abstractmethod
    def to_update_object(self, table_name: str) -> UpdateItemInputRequestTypeDef:
        """Should implement method which will return prepared object for updating item in table"""


class ItemBaseModel(DBBaseModel, ABC):
    @classmethod
    @abstractmethod
    def from_record(cls: Type[ItemBaseModelType], object_item: dict) -> ItemBaseModelType | None:
        """Should implement method which will return parse object from DynamoDB"""
