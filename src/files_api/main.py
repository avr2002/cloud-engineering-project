from datetime import datetime
from typing import (
    List,
    Optional,
)

from fastapi import (
    Depends,
    FastAPI,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from files_api.s3.delete_objects import delete_s3_object
from files_api.s3.read_objects import (
    fetch_s3_object,
    fetch_s3_objects_metadata,
    fetch_s3_objects_using_page_token,
    get_total_object_count,
    object_exists_in_s3,
)
from files_api.s3.write_objects import upload_s3_object

#####################
# --- Constants --- #
#####################

S3_BUCKET_NAME = "some-bucket"

APP = FastAPI()

####################################
# --- Request/response schemas --- #
####################################


# read (cRud)
class FileMetadata(BaseModel):
    """Model for file metadata."""
    file_path: str
    last_modified: datetime
    size_bytes: int


# create/update (Crud)
class PutFileResponse(BaseModel):
    """Response model for PUT /files/{file_path}."""

    file_path: str
    message: str


# read (cRud)
class GetFilesResponse(BaseModel):
    """Response model for GET /files/{file_path}."""

    files: List[FileMetadata]
    next_page_token: Optional[str]
    remaining_pages: Optional[int]


# read (cRud)
class GetFilesQueryParams(BaseModel):
    """Query parameters for GET /files."""

    page_size: int = 10
    directory: Optional[str] = None
    page_token: Optional[str] = None


# delete (cruD)
class DeleteFileResponse(BaseModel):
    """Response model for DELETE /files/{file_path}."""

    message: str


##################
# --- Routes --- #
##################


@APP.put("/files/{file_path:path}")
async def upload_file(file_path: str, file: UploadFile, response: Response) -> PutFileResponse:
    """Upload or update a file to an S3 bucket."""

    object_already_exists = object_exists_in_s3(bucket_name=S3_BUCKET_NAME, object_key=file_path)
    if object_already_exists:
        response_message = f"Existing file updated at path: {file_path}"
        response.status_code = status.HTTP_200_OK
    else:
        response_message = f"New file uploaded at path: {file_path}"
        response.status_code = status.HTTP_201_CREATED

    file_content: bytes = await file.read()
    upload_s3_object(
        bucket_name=S3_BUCKET_NAME,
        object_key=file_path,
        file_content=file_content,
        content_type=file.content_type,
    )
    return PutFileResponse(file_path=file_path, message=response_message)


@APP.get("/files")
async def list_files(
    response: Response,
    query_params: GetFilesQueryParams = Depends(),
) -> GetFilesResponse:
    """
    List files with pagination.
    :param directory: The directory to list files from.
    :param page_token: The token to retrieve the next page of results.
    :param page_size: The number of files to return per page.
    """

    if query_params.page_token:
        total_objects = get_total_object_count(
            S3_BUCKET_NAME,
            prefix=query_params.directory,
            page_token=query_params.page_token,
        )
        files, next_page_token = fetch_s3_objects_using_page_token(
            bucket_name=S3_BUCKET_NAME,
            continuation_token=query_params.page_token,
            max_keys=query_params.page_size,
        )
    else:
        total_objects = get_total_object_count(S3_BUCKET_NAME, prefix=query_params.directory)
        files, next_page_token = fetch_s3_objects_metadata(
            bucket_name=S3_BUCKET_NAME,
            prefix=query_params.directory,
            max_keys=query_params.page_size,
        )

    files_metadata = [
        FileMetadata(
            file_path=file["Key"],
            last_modified=file["LastModified"],
            size_bytes=file["Size"],
        )
        for file in files
    ]
    total_pages = (total_objects + query_params.page_size - 1) // query_params.page_size
    remaining_pages = total_pages - 1 if next_page_token else 0
    response.status_code = status.HTTP_200_OK
    return GetFilesResponse(
        files=files_metadata,
        next_page_token=next_page_token,
        remaining_pages=remaining_pages,
    )


@APP.head("/files/{file_path:path}")
async def get_file_metadata(file_path: str, response: Response) -> Response:
    """Retrieve file metadata.

    Note: by convention, HEAD requests MUST NOT return a body in the response.
    """
    object_already_exists = object_exists_in_s3(bucket_name=S3_BUCKET_NAME, object_key=file_path)
    if object_already_exists:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_404_NOT_FOUND

    if response.status_code == status.HTTP_200_OK:
        get_object_response = fetch_s3_object(bucket_name=S3_BUCKET_NAME, object_key=file_path)
        response.headers["Content-Type"] = get_object_response["ContentType"]
        response.headers["Content-Length"] = str(get_object_response["ContentLength"])
        response.headers["Last-Modified"] = get_object_response["LastModified"].strftime("%a, %d %b %Y %H:%M:%S GMT")

        return response

    return response


@APP.get("/files/{file_path:path}")
async def get_file(file_path: str, response: Response) -> StreamingResponse:
    """Retrieve a file."""
    object_already_exists = object_exists_in_s3(bucket_name=S3_BUCKET_NAME, object_key=file_path)
    if object_already_exists:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        return StreamingResponse(content="None", status_code=status.HTTP_404_NOT_FOUND)

    get_object_response = fetch_s3_object(bucket_name=S3_BUCKET_NAME, object_key=file_path)
    response.headers["Content-Type"] = get_object_response["ContentType"]
    response.headers["Content-Length"] = str(get_object_response["ContentLength"])
    return StreamingResponse(
        content=get_object_response["Body"],
        media_type=get_object_response["ContentType"],
        headers=response.headers,
    )


@APP.delete("/files/{file_path:path}")
async def delete_file(file_path: str, response: Response) -> Response:
    """Delete a file.

    NOTE: DELETE requests MUST NOT return a body in the response.
    """
    object_already_exists = object_exists_in_s3(bucket_name=S3_BUCKET_NAME, object_key=file_path)
    if not object_already_exists:
        response.status_code = status.HTTP_404_NOT_FOUND
        return response

    delete_s3_object(bucket_name=S3_BUCKET_NAME, object_key=file_path)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(APP, host="0.0.0.0", port=8000)
