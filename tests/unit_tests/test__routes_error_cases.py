from fastapi.testclient import TestClient
from fastapi import status


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
    