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

from botocore.response import StreamingBody
from files_api.s3.delete_objects import delete_s3_object
from files_api.s3.read_objects import (
    fetch_s3_object,
    fetch_s3_objects_metadata,
    fetch_s3_objects_using_page_token,
    object_exists_in_s3,
    get_total_object_count,
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
    file_path: str
    last_modified: datetime
    size_bytes: int


class PutFileResponse(BaseModel):
    """Response model for PUT /files/{file_path}."""

    file_path: str
    message: str


class GetFileResponse(BaseModel):
    """Response model for GET /files/{file_path}."""

    files: List[FileMetadata]
    next_page_token: Optional[str]
    remaining_pages: Optional[int]


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
    directory: Optional[str] = None,
    page_token: Optional[str] = None,
    page_size: Optional[int] = 10,
) -> GetFileResponse:
    """
    List files with pagination.
    :param directory: The directory to list files from.
    :param page_token: The token to retrieve the next page of results.
    :param page_size: The number of files to return per page.
    """
    total_objects: int = get_total_object_count(S3_BUCKET_NAME, prefix=directory)
    total_pages: int = (total_objects + page_size - 1) // page_size
    
    if page_token:
        files, next_page_token = fetch_s3_objects_using_page_token(
            bucket_name=S3_BUCKET_NAME,
            continuation_token=page_token,
            max_keys=page_size,
            # prefix=directory,
        )
        files_metadata = [
            FileMetadata(
                file_path=file["Key"],
                last_modified=file["LastModified"],
                size_bytes=file["Size"],
            )
            for file in files
        ]
        remaining_pages = total_pages - 1 if next_page_token else 0
        response.status_code = status.HTTP_200_OK
        return GetFileResponse(
            files=files_metadata,
            next_page_token=next_page_token,
            remaining_pages=remaining_pages,
        )
        
    files, next_page_token = fetch_s3_objects_metadata(
        bucket_name=S3_BUCKET_NAME,
        prefix=directory,
        max_keys=page_size,
    )
    files_metadata = [
        FileMetadata(
            file_path=file["Key"],
            last_modified=file["LastModified"],
            size_bytes=file["Size"],
        )
        for file in files
    ]
    remaining_pages = total_pages - 1 if next_page_token else 0
    response.status_code = status.HTTP_200_OK
    return GetFileResponse(
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
        get_object_response  = fetch_s3_object(bucket_name=S3_BUCKET_NAME, object_key=file_path)
        response.headers['Content-Type'] = get_object_response ['ContentType']
        response.headers['Content-Length'] = str(get_object_response ['ContentLength'])
        response.headers['Last-Modified'] = get_object_response ['LastModified'].strftime("%a, %d %b %Y %H:%M:%S GMT")
        
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
    response.headers['Content-Type'] = get_object_response ['ContentType']
    response.headers['Content-Length'] = str(get_object_response ['ContentLength'])
    return StreamingResponse(
        content=get_object_response['Body'],
        media_type=get_object_response ['ContentType'],
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
