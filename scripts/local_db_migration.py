import argparse

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError

ENDPOINT_URL = "http://localhost:4566"
AWS_REGION = "us-east-1"

TABLES_AND_PRIMARY_KEY = (
    ("Documents", "id"),
    ("Envelopes", "envelope_id"),
    ("EnvelopeCallbacks", "envelope_id"),
)


class MigrationOption:
    create_tables = "create_tables"
    delete_tables = "delete_tables"


client = boto3.client(  # noqa: S106
    "dynamodb",
    endpoint_url=ENDPOINT_URL,
    region_name=AWS_REGION,
    config=Config(signature_version=UNSIGNED),
)


def create_table_builder(table_name: str, primary_key_name: str) -> dict:
    return {
        "TableName": table_name,
        "KeySchema": [
            {"AttributeName": primary_key_name, "KeyType": "HASH"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": primary_key_name, "AttributeType": "S"}
        ],
        "ProvisionedThroughput": {
            "ReadCapacityUnits": 10,
            "WriteCapacityUnits": 10
        }
    }


def create_tables():
    for table_for_create in TABLES_AND_PRIMARY_KEY:
        table_name, _ = table_for_create

        try:
            client.create_table(**create_table_builder(*table_for_create))
        except ClientError as ce:
            if ce.response["Error"]["Code"] in {"ResourceNotFoundException", "ResourceInUseException"}:
                raise ValueError(f"Table {table_name} was already created")

            raise

        client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                "Enabled": True,
                "AttributeName": "expiration_time"
            }
        )


def delete_tables():
    for table_for_delete in TABLES_AND_PRIMARY_KEY:
        table_name, _ = table_for_delete
        try:
            client.delete_table(TableName=table_name)
        except ClientError as ce:
            if ce.response["Error"]["Code"] in {"ResourceNotFoundException", "ResourceInUseException"}:
                raise ValueError(f"Table {table_name} doesn't exist")

            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="DynamoDB migration",
        description="Script for creating or deleting DynamoDB tables in local machine"
    )

    parser.add_argument("action", choices=[MigrationOption.create_tables, MigrationOption.delete_tables])

    args = parser.parse_args()
    if args.action == MigrationOption.create_tables:
        create_tables()
    elif args.action == MigrationOption.delete_tables:
        delete_tables()
    else:
        raise NotImplementedError(
            f"Action {args.action} was not implemented. Please specify correct migration option"
        )
