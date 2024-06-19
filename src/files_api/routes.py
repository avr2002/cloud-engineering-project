"""FastAPI application for managing files in an S3 bucket."""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from files_api.s3.delete_objects import delete_s3_object
from files_api.s3.read_objects import (
    fetch_s3_object,
    fetch_s3_objects_metadata,
    fetch_s3_objects_using_page_token,
    # get_total_object_count,
    object_exists_in_s3,
)
from files_api.s3.write_objects import upload_s3_object
from files_api.schemas import (
    FileMetadata,
    GetFilesQueryParams,
    GetFilesResponse,
    PutFileResponse,
)
from files_api.settings import Settings

ROUTER = APIRouter()


@ROUTER.put("/files/{file_path:path}")
async def upload_file(
    request: Request,
    file_path: str,
    file: UploadFile,
    response: Response,
) -> PutFileResponse:
    """Upload or update a file to an S3 bucket."""
    settings: Settings = request.app.state.settings
    s3_bucket_name = settings.s3_bucket_name
    object_already_exists = object_exists_in_s3(bucket_name=s3_bucket_name, object_key=file_path)
    if object_already_exists:
        response_message = f"Existing file updated at path: {file_path}"
        response.status_code = status.HTTP_200_OK
    else:
        response_message = f"New file uploaded at path: {file_path}"
        response.status_code = status.HTTP_201_CREATED

    file_content: bytes = await file.read()
    upload_s3_object(
        bucket_name=s3_bucket_name,
        object_key=file_path,
        file_content=file_content,
        content_type=file.content_type,
    )
    return PutFileResponse(file_path=file_path, message=response_message)


@ROUTER.get("/files")
async def list_files(
    request: Request,
    response: Response,
    query_params: GetFilesQueryParams = Depends(),
) -> GetFilesResponse:
    """List files with pagination."""
    settings: Settings = request.app.state.settings
    s3_bucket_name = settings.s3_bucket_name
    if query_params.page_token:
        # total_objects = get_total_object_count(
        #     s3_bucket_name,
        #     prefix=query_params.directory,
        #     page_token=query_params.page_token,
        # )
        files, next_page_token = fetch_s3_objects_using_page_token(
            bucket_name=s3_bucket_name,
            continuation_token=query_params.page_token,
            max_keys=query_params.page_size,
        )
    else:
        # total_objects = get_total_object_count(s3_bucket_name, prefix=query_params.directory)
        files, next_page_token = fetch_s3_objects_metadata(
            bucket_name=s3_bucket_name,
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
    # total_pages = (total_objects + query_params.page_size - 1) // query_params.page_size
    # remaining_pages = total_pages - 1 if next_page_token else 0
    response.status_code = status.HTTP_200_OK
    return GetFilesResponse(
        files=files_metadata,
        next_page_token=next_page_token if next_page_token else None,
        # remaining_pages=remaining_pages,
    )


@ROUTER.head("/files/{file_path:path}")
async def get_file_metadata(
    request: Request,
    file_path: str,
    response: Response,
) -> Response:
    """
    Retrieve file metadata.

    Note: by convention, HEAD requests MUST NOT return a body in the response.
    """
    settings: Settings = request.app.state.settings
    s3_bucket_name = settings.s3_bucket_name
    object_exists = object_exists_in_s3(bucket_name=s3_bucket_name, object_key=file_path)
    if not object_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            # detail=f"File not found: {file_path}",
            headers={"Error": f"File not found: {file_path}"},
        )

    get_object_response = fetch_s3_object(bucket_name=s3_bucket_name, object_key=file_path)
    response.headers["Content-Type"] = get_object_response["ContentType"]
    response.headers["Content-Length"] = str(get_object_response["ContentLength"])
    response.headers["Last-Modified"] = get_object_response["LastModified"].strftime("%a, %d %b %Y %H:%M:%S GMT")
    response.status_code = status.HTTP_200_OK

    return response


@ROUTER.get("/files/{file_path:path}")
async def get_file(
    request: Request,
    response: Response,
    file_path: str,
) -> StreamingResponse:
    """Retrieve a file."""
    # 1. Business Logic: Erros that user can fix.
    # Error case: Object does not exist in S3 bucket.
    # Error case: Invalid input

    # 2. Internal Server Error: Errors that user cannot fix.
    # Error case: Not authenticates/authorized to make calls to AWS
    # Error case: The bucket does not exist
    settings: Settings = request.app.state.settings
    s3_bucket_name = settings.s3_bucket_name
    object_exists = object_exists_in_s3(bucket_name=s3_bucket_name, object_key=file_path)
    if not object_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {file_path}")

    get_object_response = fetch_s3_object(bucket_name=s3_bucket_name, object_key=file_path)
    response.headers["Content-Type"] = get_object_response["ContentType"]
    response.headers["Content-Length"] = str(get_object_response["ContentLength"])
    response.status_code = status.HTTP_200_OK
    return StreamingResponse(
        content=get_object_response["Body"],
        media_type=get_object_response["ContentType"],
        headers=response.headers,
    )


@ROUTER.delete("/files/{file_path:path}")
async def delete_file(
    request: Request,
    file_path: str,
    response: Response,
) -> Response:
    """
    Delete a file.

    NOTE: DELETE requests MUST NOT return a body in the response.
    """
    settings: Settings = request.app.state.settings
    s3_bucket_name = settings.s3_bucket_name
    object_exists = object_exists_in_s3(bucket_name=s3_bucket_name, object_key=file_path)
    if not object_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {file_path}")

    delete_s3_object(bucket_name=s3_bucket_name, object_key=file_path)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
