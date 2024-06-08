"""Test cases for `s3.read_objects`."""

from files_api.s3.read_objects import (
    fetch_s3_objects_metadata,
    fetch_s3_objects_using_page_token,
    object_exists_in_s3,
)
from mypy_boto3_s3 import S3Client
from tests.consts import TEST_BUCKET_NAME


def test_object_exists_in_s3(s3_client: S3Client):
    ...


def test_pagination(s3_client: S3Client):
    ...


def test_mixed_page_sizes(s3_client: S3Client):
    ...


def test_directory_queries(s3_client: S3Client):
    ...
