import pytest
from fastapi import status
from fastapi.testclient import TestClient

from files_api.main import APP

TEST_FILE_PATH = "some/nested/path/file.txt"
TEST_FILE_CONTENT = b"Hello, world!"
TEST_FILE_CONTENT_TYPE = "text/plain"


# Fixture for FastAPI test client
@pytest.fixture
def client(mocked_aws) -> TestClient:  # pylint: disable=unused-argument
    with TestClient(APP) as client:
        yield client


def test_upload_file(client: TestClient):
    response = client.put(
        f"/files/{TEST_FILE_PATH}",
        files={"file": (TEST_FILE_PATH, TEST_FILE_CONTENT, TEST_FILE_CONTENT_TYPE)},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {
        "file_path": TEST_FILE_PATH,
        "message": f"New file uploaded at path: {TEST_FILE_PATH}",
    }

    # update the file
    updated_content = b"Hello, world! Updated!"
    response = client.put(
        f"/files/{TEST_FILE_PATH}",
        files={"file": (TEST_FILE_PATH, updated_content, TEST_FILE_PATH)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "file_path": TEST_FILE_PATH,
        "message": f"Existing file updated at path: {TEST_FILE_PATH}",
    }


def test_list_files_with_pagination(client: TestClient):
    # Create a directory-like structure in the bucket
    file_paths = [
        "folder1/file1.txt",
        "folder1/file2.txt",
        "folder2/file3.txt",
        "folder2/subfolder/file4.txt",
        "file5.txt",
    ]

    for file_path in file_paths:
        client.put(
            f"/files/{file_path}",
            files={"file": (file_path, TEST_FILE_CONTENT, TEST_FILE_CONTENT_TYPE)},
        )

    # Query all files
    response = client.get("/files")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("files", [])) == 5
    assert response.json().get("next_page_token") is None
    assert response.json().get("remaining_pages") == 0

    # Query with prefix
    response = client.get("/files?directory=folder1")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("files", [])) == 2
    assert response.json().get("next_page_token") is None
    assert response.json().get("remaining_pages") == 0

    # Query with prefix
    response = client.get("/files?directory=folder")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("files", [])) == 4
    assert response.json().get("next_page_token") is None
    assert response.json().get("remaining_pages") == 0

    # Query with prefix as sub-directory
    response = client.get("/files?directory=folder2/subfolder")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("files", [])) == 1
    assert response.json().get("next_page_token") is None
    assert response.json().get("remaining_pages") == 0

    # Query with prefix and pagination
    response = client.get("/files?directory=folder&page_size=2")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("files", [])) == 2
    assert response.json().get("next_page_token") is not None
    assert response.json().get("remaining_pages") == 1

    # Query prefix, directory and pagination with page token
    next_page_token = response.json().get("next_page_token")
    response = client.get(f"/files?page_token={next_page_token}")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("files", [])) == 2
    assert response.json().get("next_page_token") is None
    assert response.json().get("remaining_pages") == 0

    # Query with file prefix
    next_page_token = response.json().get("next_page_token")
    response = client.get(f"/files?directory=file")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("files", [])) == 1
    assert response.json().get("files")[0].get("file_path") == "file5.txt"
    assert response.json().get("next_page_token") is None
    assert response.json().get("remaining_pages") == 0

    # @TODO: Query with invalid page token


def test_get_file_metadata(client: TestClient):
    # Create sample file
    client.put(
        url=f"/files/{TEST_FILE_PATH}",
        files={"file": ("folder1/file1.txt", TEST_FILE_CONTENT, TEST_FILE_CONTENT_TYPE)},
    )

    # Query metadata for existing file
    response = client.head(f"/files/{TEST_FILE_PATH}")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Content-Type"] == TEST_FILE_CONTENT_TYPE
    assert response.headers["Content-Length"] == str(len(TEST_FILE_CONTENT))

    # Query metadata for non-existing file
    response = client.head("/files/non/existing/file.txt")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Content-Type" not in response.headers
    assert "Content-Length" not in response.headers


def test_get_file(client: TestClient):
    # Create sample file
    client.put(
        url=f"/files/{TEST_FILE_PATH}",
        files={"file": ("folder1/file1.txt", TEST_FILE_CONTENT, TEST_FILE_CONTENT_TYPE)},
    )

    # Query a existing file
    response = client.get(f"/files/{TEST_FILE_PATH}")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Content-Type"] == TEST_FILE_CONTENT_TYPE
    assert response.headers["Content-Length"] == str(len(TEST_FILE_CONTENT))
    assert response.content == TEST_FILE_CONTENT

    # Query a non-existing file
    response = client.get("/files/non/existing/file.txt")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Content-Type" not in response.headers
    assert "Content-Length" not in response.headers


def test_delete_file(client: TestClient):
    # Create sample file
    client.put(
        url=f"/files/{TEST_FILE_PATH}",
        files={"file": ("folder1/file1.txt", TEST_FILE_CONTENT, TEST_FILE_CONTENT_TYPE)},
    )

    # Delete existing file
    response = client.delete(f"/files/{TEST_FILE_PATH}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Delete non-existing file
    response = client.delete(f"/files/{TEST_FILE_PATH}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
