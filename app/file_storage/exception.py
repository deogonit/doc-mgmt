import json
from pathlib import Path

from botocore.exceptions import ClientError
from fastapi import status

from app.base.exception import BaseHTTPException


class NoSuchBucketException(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The specified bucket does not exist"
    field_name = "bucketName"

    def __init__(self, bucket_name: str):
        super().__init__(field_value=bucket_name)


class DynamicS3Exception(BaseHTTPException):
    status_code = status.HTTP_418_IM_A_TEAPOT
    message = "Dynamic S3 exception with status code and message which are forwarded from s3"
    field_name = "bucketName/filePath"

    def __init__(
        self,
        s3_exception: ClientError,
        bucket: str,
        key: str | Path | None = None,
    ):
        full_path = f"{bucket}/{key}" if key else bucket

        s3_status_code = s3_exception.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        s3_error_dict = s3_exception.response.get("Error")

        super().__init__(
            status_code=int(s3_status_code) if s3_status_code else None,
            message=json.dumps(s3_error_dict) if s3_error_dict else None,
            field_value=full_path,
        )
