"""FastAPI application for managing files in an S3 bucket."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
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

ROUTER = APIRouter(tags=["Files"])


@ROUTER.put(
    "/v1/files/{file_path:path}",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "model": PutFileResponse,
            "description": "File uploaded successfully.",
            "content": PutFileResponse.model_json_schema()[str(status.HTTP_201_CREATED)]["content"],
        },
        status.HTTP_200_OK: {
            "model": PutFileResponse,
            "description": "File updated successfully.",
            "content": PutFileResponse.model_json_schema()[str(status.HTTP_200_OK)]["content"],
        },
    },
)
async def upload_file(
    request: Request,
    response: Response,
    file_path: Annotated[str, Path(description=PutFileResponse.model_fields["file_path"].description)],
    file_content: Annotated[UploadFile, File(description="The file to upload.")],
) -> PutFileResponse:
    """Upload or Update a File."""
    settings: Settings = request.app.state.settings
    s3_bucket_name = settings.s3_bucket_name
    object_already_exists = object_exists_in_s3(bucket_name=s3_bucket_name, object_key=file_path)
    if object_already_exists:
        response_message = f"Existing file updated at path: {file_path}"
        response.status_code = status.HTTP_200_OK
    else:
        response_message = f"New file uploaded at path: {file_path}"
        response.status_code = status.HTTP_201_CREATED

    file_bytes: bytes = await file_content.read()
    upload_s3_object(
        bucket_name=s3_bucket_name,
        object_key=file_path,
        file_content=file_bytes,
        content_type=file_content.content_type,
    )
    return PutFileResponse(file_path=file_path, message=response_message)


@ROUTER.get(
    "/v1/files",
    responses={
        status.HTTP_200_OK: {
            "model": GetFilesResponse,
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "examples": {
                        "With Pagination": GetFilesResponse.model_json_schema()["examples"][0],
                        "No Pages Left": GetFilesResponse.model_json_schema()["examples"][1],
                    },
                },
            },
        },
    },
)
async def list_files(
    request: Request, response: Response, query_params: Annotated[GetFilesQueryParams, Depends()]
) -> GetFilesResponse:
    """List Files with Pagination."""
    settings: Settings = request.app.state.settings
    s3_bucket_name = settings.s3_bucket_name
    if query_params.page_token:
        files, next_page_token = fetch_s3_objects_using_page_token(
            bucket_name=s3_bucket_name,
            continuation_token=query_params.page_token,
            max_keys=query_params.page_size,
        )
    else:
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
    response.status_code = status.HTTP_200_OK
    return GetFilesResponse(
        files=files_metadata,
        next_page_token=next_page_token if next_page_token else None,
    )


@ROUTER.head(
    "/v1/files/{file_path:path}",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "File not found for the given `file_path`.",
            "headers": {
                "X-Error": {
                    "description": "Error message indicating the file was not found.",
                    "example": "File not found: `path/to/file.txt`",
                    "schema": {"type": "string", "format": "text"},
                }
            },
            "content": None,
        },
        status.HTTP_200_OK: {
            "headers": {
                "Content-Type": {
                    "description": "The [MIME type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types) of the file.",
                    "example": "text/plain",
                    "schema": {"type": "string", "format": "text"},
                },
                "Content-Length": {
                    "description": "The size of the file in bytes.",
                    "example": 512,
                    "schema": {"type": "integer", "format": "integer"},
                },
                "Last-Modified": {
                    "description": "The last modified date of the file.",
                    "example": "Thu, 01 Jan 2022 00:00:00 GMT",
                    "schema": {"type": "string", "format": "date-time"},
                },
            },
        },
    },
)
async def get_file_metadata(file_path: str, request: Request, response: Response) -> Response:
    """
    Retrieve File Metadata.

    Note: by convention, HEAD requests MUST NOT return a body in the response.
    """
    settings: Settings = request.app.state.settings
    s3_bucket_name = settings.s3_bucket_name
    object_exists = object_exists_in_s3(bucket_name=s3_bucket_name, object_key=file_path)
    if not object_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            headers={"X-Error": f"File not found: {file_path}"},
        )

    get_object_response = fetch_s3_object(bucket_name=s3_bucket_name, object_key=file_path)
    response.headers["Content-Type"] = get_object_response["ContentType"]
    response.headers["Content-Length"] = str(get_object_response["ContentLength"])
    response.headers["Last-Modified"] = get_object_response["LastModified"].strftime("%a, %d %b %Y %H:%M:%S GMT")
    response.status_code = status.HTTP_200_OK

    return response


@ROUTER.get(
    "/v1/files/{file_path:path}",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "File not found for the given `file_path`.",
            "content": {
                "application/json": {
                    "example": {"detail": "File not found: path/to/file.txt"},
                },
            },
        },
        status.HTTP_200_OK: {
            "description": "Successful Response",
            "content": {
                "text/plain": {
                    "schema": {"type": "string", "format": "text"},
                    "example": "File Content.",
                },
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"},
                },
                "application/json": None,
            },
            "headers": {
                "Content-Type": {
                    "description": "The [MIME type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types) of the file.",
                    "example": "text/plain",
                    "schema": {"type": "string"},
                },
                "Content-Length": {
                    "description": "The size of the file in bytes.",
                    "example": 512,
                    "schema": {"type": "integer"},
                },
            },
        },
    },
)
async def get_file(
    request: Request, response: Response, file_path: Annotated[str, Path(description="The path to the file.")]
) -> StreamingResponse:
    """Retrieve a File."""
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


@ROUTER.delete(
    "/v1/files/{file_path:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "File deleted successfully."},
        status.HTTP_404_NOT_FOUND: {"description": "File not found."},
    },
)
async def delete_file(
    request: Request, response: Response, file_path: Annotated[str, Path(description="The path to the file.")]
) -> Response:
    """
    Delete a file.

    NOTE: DELETE requests MUST NOT return a body in the response.
    """
    settings: Settings = request.app.state.settings
    s3_bucket_name = settings.s3_bucket_name
    object_exists = object_exists_in_s3(bucket_name=s3_bucket_name, object_key=file_path)
    if not object_exists:
        response.status_code = status.HTTP_404_NOT_FOUND
        response.headers["X-Error"] = f"File not found: {file_path}"
        return response

    delete_s3_object(bucket_name=s3_bucket_name, object_key=file_path)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


# @ROUTER.put("/v1/files/openai/{file_path:path}")
# async def upload_file_from_openai(
#     request: Request,
#     file_path: Annotated[str, Path(description="The path to the file.")],
# ) -> PutFileResponse:
#     """Upload a File from OpenAI."""
#     settings: Settings = request.app.state.settings
#     s3_bucket_name = settings.s3_bucket_name

#     # generate ai content using openai
#     file_content = generate_ai_content()


#     upload_s3_object(
#         bucket_name=s3_bucket_name,
#         object_key=file_path,
#         file_content=file_bytes,
#         content_type=file_content.content_type,
#     )
#     return PutFileResponse(file_path=file_path, message=f"New file uploaded at path: {file_path}")
