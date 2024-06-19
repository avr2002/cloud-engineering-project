from fastapi import status
from fastapi.testclient import TestClient


from files_api.schemas import DEFAULT_GET_FILES_MAX_PAGE_SIZE
from tests.consts import TEST_BUCKET_NAME
from tests.utils import delete_s3_bucket

NON_EXISTENT_FILE_PATH = "nonexistent_file.txt"


def test_get_nonexistent_file(client: TestClient):
    response = client.get(f"/files/{NON_EXISTENT_FILE_PATH}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": f"File not found: {NON_EXISTENT_FILE_PATH}"}


def test_get_nonexistent_file_metadata(client: TestClient):
    response = client.head(f"/files/{NON_EXISTENT_FILE_PATH}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.headers["Error"] == f"File not found: {NON_EXISTENT_FILE_PATH}"


def test_delete_nonexistent_file(client: TestClient):
    response = client.delete(f"/files/{NON_EXISTENT_FILE_PATH}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": f"File not found: {NON_EXISTENT_FILE_PATH}"}


def test_get_files_invalid_page_size(client: TestClient):
    # Test negative page size
    response = client.get("/files?page_size=-1")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test page size greater than the maximum allowed
    response = client.get(f"/files?page_size={DEFAULT_GET_FILES_MAX_PAGE_SIZE + 1}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_files_page_token_is_mutually_exclusive_with_page_size_and_directory(client: TestClient):
    response = client.get("/files?page_token=token&page_size=10&directory=dir")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "mutually exclusive" in str(response.json())

    response = client.get("/files?page_token=token&directory=dir")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "mutually exclusive" in str(response.json())

    response = client.get("/files?page_token=token&page_size=10")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "mutually exclusive" in str(response.json())


def test_unforeseen_500_error(client: TestClient):
    # Delete the S3 bucket and all objects inside name from the app state to force an unforeseen error
    delete_s3_bucket(TEST_BUCKET_NAME)

    # make a request to the API to a route that interacts with the S3 bucket
    response = client.get("/files")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
