import os
from uuid import uuid4

import boto3
from moto import mock_aws

from files_api.s3.write_objects import upload_s3_object

TEST_BUCKET_NAME = f"test-bucket-cloud-course-{str(uuid4())[:4]}"


# Set the environment variables to point away from AWS
def point_away_from_aws() -> None:
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@mock_aws
def test__upload_s3_object():
    # Set the environment variables to point away from AWS
    point_away_from_aws()

    # 1. Create an S3 bucket
    s3_client = boto3.client("s3")
    s3_client.create_bucket(Bucket=TEST_BUCKET_NAME)

    # 2. Upload a file to the bucket, with a particular content type
    object_key = "test.txt"
    file_content = b"Hello, world!"
    content_type = "text/plain"

    upload_s3_object(
        bucket_name=TEST_BUCKET_NAME,
        object_key=object_key,
        file_content=file_content,
        content_type=content_type,
        s3_client=s3_client,
    )

    # 3. Assert that the file was uploaded with the correct content type
    response = s3_client.get_object(Bucket=TEST_BUCKET_NAME, Key=object_key)
    assert response["ContentType"] == content_type
    assert response["Body"].read() == file_content

    # 4. Clean up by deleting the bucket
    response = s3_client.list_objects_v2(Bucket=TEST_BUCKET_NAME)
    for obj in response.get("Contents", []):
        s3_client.delete_object(Bucket=TEST_BUCKET_NAME, Key=obj["Key"])

    s3_client.delete_bucket(Bucket=TEST_BUCKET_NAME)
