"""Functions for reading objects from an S3 bucket--the "R" in CRUD."""

from typing import (
    Optional,
    Union,
)

import boto3
from botocore.exceptions import ClientError

try:
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_s3.type_defs import (
        GetObjectOutputTypeDef,
        HeadObjectOutputTypeDef,
        ListObjectsV2OutputTypeDef,
        ObjectTypeDef,
    )
except ImportError:
    ...

DEFAULT_MAX_KEYS = 1_000


def object_exists_in_s3(
    bucket_name: str,
    object_key: str,
    s3_client: Optional["S3Client"] = None,
) -> bool:
    """
    Check if an object exists in the S3 bucket using head_object.

    :param bucket_name: Name of the S3 bucket.
    :param object_key: Key of the object to check.
    :param s3_client: Optional S3 client to use. If not provided, a new client will be created.

    :return: True if the object exists, False otherwise.
    """
    try:
        s3_client = s3_client or boto3.client("s3")
        response: "HeadObjectOutputTypeDef" = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        if response:
            return True
    except ClientError as err:
        error_code = err.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            return False
        raise


def fetch_s3_object(
    bucket_name: str,
    object_key: str,
    s3_client: Optional["S3Client"] = None,
) -> "GetObjectOutputTypeDef":
    """
    Fetch metadata of an object in the S3 bucket.

    :param bucket_name: Name of the S3 bucket.
    :param object_key: Key of the object to fetch.
    :param s3_client: Optional S3 client to use. If not provided, a new client will be created.

    :return: Metadata of the object if it exists, otherwise None.
    """
    s3_client = s3_client or boto3.client("s3")
    response: "GetObjectOutputTypeDef" = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    return response


def fetch_s3_objects_using_page_token(
    bucket_name: str,
    continuation_token: str,
    max_keys: int | None = None,
    s3_client: Optional["S3Client"] = None,
) -> tuple[list["ObjectTypeDef"], Union[str, None]]:
    """
    Fetch list of object keys and their metadata using a continuation token.

    :param bucket_name: Name of the S3 bucket to list objects from.
    :param continuation_token: Token for fetching the next page of results where the last page left off.
    :param max_keys: Maximum number of keys to return within this page.
    :param s3_client: Optional S3 client to use. If not provided, a new client will be created.

    :return: Tuple of a list of objects and the next continuation token.
        1. Possibly empty list of objects in the current page.
        2. Next continuation token if there are more pages, otherwise None.
    """
    s3_client = s3_client or boto3.client("s3")

    response: "ListObjectsV2OutputTypeDef" = s3_client.list_objects_v2(
        Bucket=bucket_name,
        ContinuationToken=continuation_token,
        MaxKeys=max_keys or DEFAULT_MAX_KEYS,
    )
    files: list["ObjectTypeDef"] = response.get("Contents", [])
    next_continuation_token: str | None = response.get("NextContinuationToken", None)

    return files, next_continuation_token


def fetch_s3_objects_metadata(
    bucket_name: str,
    prefix: Optional[str] = None,
    max_keys: Optional[int] = DEFAULT_MAX_KEYS,
    s3_client: Optional["S3Client"] = None,
) -> tuple[list["ObjectTypeDef"], Union[str, None]]:
    """
    Fetch list of object keys and their metadata.

    :param bucket_name: Name of the S3 bucket to list objects from.
    :param prefix: Prefix to filter objects by.
    :param max_keys: Maximum number of keys to return within this page.
    :param s3_client: Optional S3 client to use. If not provided, a new client will be created.

    :return: Tuple of a list of objects and the next continuation token.
        1. Possibly empty list of objects in the current page.
        2. Next continuation token if there are more pages, otherwise None.
    """
    s3_client = s3_client or boto3.client("s3")
    response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Prefix=prefix or "",
        MaxKeys=max_keys or DEFAULT_MAX_KEYS,
    )
    files: list["ObjectTypeDef"] = response.get("Contents", [])
    next_continuation_token: str | None = response.get("NextContinuationToken", None)

    return files, next_continuation_token


def get_total_object_count(
    bucke_name: str,
    prefix: Optional[str] = None,
    page_token: Optional[str] = None,
    s3_client: Optional["S3Client"] = None,
) -> int:
    s3_client = s3_client or boto3.client("s3")
    paginator = s3_client.get_paginator("list_objects_v2")
    operation_parameters = {"Bucket": bucke_name, "Prefix": prefix or ""}
    if page_token:
        operation_parameters["PaginationConfig"] = {"StartingToken": page_token}

    page_iterator = paginator.paginate(**operation_parameters)
    total_objects = 0
    for page in page_iterator:
        total_objects += len(page.get("Contents", []))

    return total_objects
