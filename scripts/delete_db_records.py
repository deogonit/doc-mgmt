import argparse

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError
from logger import get_logger


class EnvironmentVariables:
    local = "local"
    dev = "dev"
    stage = "stage"
    uat = "uat"
    prod = "prod"


ABSENT_FIELDS = ("created_at", "expiration_time")
TABLES_AND_PRIMARY_KEY = (
    ("Documents", "id"),
    ("Envelopes", "envelope_id"),
    ("EnvelopeCallbacks", "envelope_id"),
)
ENDPOINT_URL = "http://localhost:4566"
AWS_REGION = "us-east-1"


client = boto3.client(  # noqa: S106
    "dynamodb",
    endpoint_url=ENDPOINT_URL,
    region_name=AWS_REGION,
    config=Config(signature_version=UNSIGNED),
)
logger = get_logger()
filter_expression = " or ".join([f"attribute_not_exists({field})" for field in ABSENT_FIELDS])


def get_records(table_name: str):
    records = []
    scan_kwargs = {
        "TableName": table_name,
        "FilterExpression": filter_expression
    }
    done = False
    start_key = None
    while not done:
        if start_key:
            scan_kwargs["ExclusiveStartKey"] = start_key

        try:
            response = client.scan(**scan_kwargs)
        except ClientError as err:
            error_response = err.response["Error"]["Code"]
            error_message = err.response["Error"]["Message"]
            logger.error(f"Couldn't scan for {table_name}. Here's why: {error_response}: {error_message}")
            raise

        records.extend(response.get("Items", []))
        start_key = response.get("LastEvaluatedKey", None)
        done = start_key is None

    return records


def delete_records(table_name: str, primary_key: str, records_ids: list[str]):
    delete_params = {
        "TableName": table_name,
        "ConditionExpression": filter_expression,
        "Key": {}
    }

    for record_id in records_ids:
        delete_params.update({
            "Key": {
                primary_key: {
                    "S": record_id
                }
            }
        })

        logger.info(f"Deleting id {record_id} from {table_name} table")
        try:
            client.delete_item(**delete_params)
        except ClientError as err:
            error_response = err.response["Error"]["Code"]
            error_message = err.response["Error"]["Message"]
            logger.error(f"Couldn't delete. Here's why: {error_response}: {error_message}")
            raise


def main(env: str) -> None:
    prefix_env = "" if env == EnvironmentVariables.local else env

    for table_name, table_primary_key in TABLES_AND_PRIMARY_KEY:
        enhanced_table_name = f"{prefix_env}{table_name}"
        records = get_records(enhanced_table_name)
        if not records:
            logger.info(f"Records from {table_name} has not founded")
            continue

        records_ids = [record[table_primary_key]["S"] for record in records]
        delete_records(table_name, table_primary_key, records_ids)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="DynamoDB deleting records",
        description="Script for deleting records in DynamoDB tables"
    )

    parser.add_argument(
        "--env",
        choices=[
            EnvironmentVariables.local,
            EnvironmentVariables.dev,
            EnvironmentVariables.stage,
            EnvironmentVariables.uat,
            EnvironmentVariables.prod,
        ],
        default=EnvironmentVariables.local,
        const=EnvironmentVariables.local,
        nargs="?"
    )

    args = parser.parse_args()
    env = args.env

    main(env)
