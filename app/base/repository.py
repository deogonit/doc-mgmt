import logging
from abc import ABC, abstractmethod
from typing import Generic, Type, TypeVar

from types_aiobotocore_dynamodb import DynamoDBClient

from app.base.models import (
    DeleteItemBaseModel,
    ItemBaseModel,
    PutItemBaseModel,
    SearchItemBaseModel,
    UpdateItemBaseModel,
)

GenericItemBaseModel = TypeVar("GenericItemBaseModel", bound=ItemBaseModel)
GenericSearchBaseModel = TypeVar("GenericSearchBaseModel", bound=SearchItemBaseModel)
GenericPutBaseModel = TypeVar("GenericPutBaseModel", bound=PutItemBaseModel)
GenericDeleteBaseModel = TypeVar("GenericDeleteBaseModel", bound=DeleteItemBaseModel)
GenericUpdateBaseModel = TypeVar("GenericUpdateBaseModel", bound=UpdateItemBaseModel)


class DynamoDBBaseRepository(
    Generic[
        GenericItemBaseModel,
        GenericSearchBaseModel,
        GenericPutBaseModel,
        GenericDeleteBaseModel,
        GenericUpdateBaseModel
    ],
    ABC
):
    def __init__(self, dynamodb_client: DynamoDBClient, table_name: str):
        self._dynamodb_client = dynamodb_client
        self._table_name = table_name
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def base_model(self) -> Type[GenericItemBaseModel]:
        """Pydantic base model for base model"""

    @property
    @abstractmethod
    def search_model(self) -> Type[GenericSearchBaseModel]:
        """Pydantic base model for scan base model"""

    @property
    @abstractmethod
    def put_model(self) -> Type[GenericPutBaseModel]:
        """Pydantic base model for put base model"""

    @property
    @abstractmethod
    def update_model(self) -> Type[GenericUpdateBaseModel]:
        """Pydantic base model for update base model"""

    @property
    @abstractmethod
    def delete_model(self) -> Type[GenericDeleteBaseModel]:
        """Pydantic base model for delete base model"""

    async def put_item(self, put_item_model: PutItemBaseModel) -> None:
        await self._dynamodb_client.put_item(**put_item_model.to_put_item_object(self._table_name))

    async def search_item(self, search_item_model: SearchItemBaseModel) -> GenericItemBaseModel | None:
        """
        This method client can use for retrieving one element from the database and
        when the client has to find a record based on simple fields without primary/sort keys.
        Also, the scan method has a limit of fetched data (1 Mb), so we should retrieve data in a loop.
        """
        start_key = None
        done = False
        scan_kwargs = search_item_model.to_scan_object(self._table_name)
        elements: list[dict] = []

        while not done:
            if start_key:
                scan_kwargs["ExclusiveStartKey"] = start_key

            scan_result = await self._dynamodb_client.scan(**scan_kwargs)
            elements.extend(scan_result.get("Items", []))
            start_key = scan_result.get("LastEvaluatedKey", None)
            done = start_key is None

        if not elements:
            return None

        return self.base_model.from_record(elements[0])

    async def get_item(self, search_item_model: SearchItemBaseModel) -> GenericItemBaseModel | None:
        """
        This method client can use for fethching one element from database
        and when client has primary/sort keys for searching element
        """
        get_item_result = await self._dynamodb_client.get_item(**search_item_model.to_get_item_object(self._table_name))
        if "Item" not in get_item_result:
            return None

        return self.base_model.from_record(get_item_result["Item"])

    async def delete_item(self, delete_item_model: DeleteItemBaseModel) -> None:
        await self._dynamodb_client.delete_item(**delete_item_model.to_delete_object(self._table_name))

    async def update_item(self, update_item_model: UpdateItemBaseModel) -> None:
        await self._dynamodb_client.update_item(**update_item_model.to_update_object(self._table_name))
