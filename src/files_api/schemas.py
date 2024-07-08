"""FastAPI application for managing files in an S3 bucket."""

from datetime import datetime
from enum import Enum
from typing import (
    List,
    Optional,
)

from fastapi import status
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)
from typing_extensions import Self

DEFAULT_GET_FILES_PAGE_SIZE = 10
DEFAULT_GET_FILES_MIN_PAGE_SIZE = 1
DEFAULT_GET_FILES_MAX_PAGE_SIZE = 100
DEFAULT_GET_FILES_DIRECTORY = ""


# from pydantic.alias_generators import to_camel
# class BaseSchema(BaseModel):
#     model_config = ConfigDict(
#         alias_generator=to_camel,
#         populate_by_name=True,
#     )


# read (cRud)
class FileMetadata(BaseModel):
    """`Metadata` of a file."""

    file_path: str = Field(
        description="The path to the file.",
        json_schema_extra={"example": "path/to/file.txt"},
    )
    last_modified: datetime = Field(
        description="The last modified timestamp of the file.",
        json_schema_extra={"example": "2021-09-01T12:00:00"},
    )
    size_bytes: int = Field(
        description="The size of the file in bytes.",
        json_schema_extra={"example": 512},
    )


# create/update (Crud)
class PutFileResponse(BaseModel):
    """Response model for `PUT /v1/files/:file_path`."""

    file_path: str = Field(
        description="The path to the file.",
        json_schema_extra={"example": "path/to/file.txt"},
    )
    message: str = Field(
        description="The message indicating the status of the operation.",
        json_schema_extra={"example": "New file uploaded at path: path/to/file.txt"},
    )

    model_config = ConfigDict(
        json_schema_extra={
            f"{status.HTTP_201_CREATED}": {
                "content": {
                    "application/json": {
                        "example": {
                            "file_path": "path/to/file.txt",
                            "message": "New file uploaded at path: path/to/file.txt",
                        },
                    },
                },
            },
            f"{status.HTTP_200_OK}": {
                "content": {
                    "application/json": {
                        "example": {
                            "file_path": "path/to/file.txt",
                            "message": "Existing file updated at path: path/to/file.txt",
                        }
                    },
                },
            },
        }
    )


# read (cRud)
class GetFilesQueryParams(BaseModel):
    """Query parameters for `GET /v1/files`."""

    page_size: int = Field(
        default=DEFAULT_GET_FILES_PAGE_SIZE,
        ge=DEFAULT_GET_FILES_MIN_PAGE_SIZE,
        le=DEFAULT_GET_FILES_MAX_PAGE_SIZE,
        description="The number of files to return in a single page.",
        json_schema_extra={"example": 10},
    )
    directory: Optional[str] = Field(
        default=DEFAULT_GET_FILES_DIRECTORY,
        description="The directory to list files from.",
        json_schema_extra={"example": "path/to/directory"},
    )
    page_token: Optional[str] = Field(
        default=None,
        description="The token to retrieve the next page of files.",
        json_schema_extra={"example": "next_page_token_value"},
    )

    @model_validator(mode="after")
    def check_page_token(self) -> Self:
        """Ensure that page_token is mutually exclusive with page_size and directory."""
        if self.page_token:
            get_files_query_params: dict = self.model_dump(exclude_defaults=True)
            directory_set: bool = "directory" in get_files_query_params.keys()
            if directory_set:
                raise ValueError("page_token is mutually exclusive with directory")
        return self


# read (cRud)
class GetFilesResponse(BaseModel):
    """Response model for `GET /v1/files/:file_path`."""

    files: List[FileMetadata]
    next_page_token: Optional[str]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "value": {
                        "files": [
                            {
                                "file_path": "path/to/file1.txt",
                                "last_modified": "2021-09-01T12:00:00",
                                "size_bytes": 512,
                            },
                            {
                                "file_path": "path/to/file2.txt",
                                "last_modified": "2021-09-02T12:00:00",
                                "size_bytes": 256,
                            },
                        ],
                        "next_page_token": "next_page_token_value",
                    }
                },
                {
                    "value": {
                        "files": [
                            {
                                "file_path": "path/to/file1.txt",
                                "last_modified": "2021-09-01T12:00:00",
                                "size_bytes": 512,
                            },
                            {
                                "file_path": "path/to/file2.txt",
                                "last_modified": "2021-09-02T12:00:00",
                                "size_bytes": 256,
                            },
                        ],
                        "next_page_token": "null",
                    }
                },
            ]
        }
    )


# delete (cruD)
class DeleteFileResponse(BaseModel):
    """Response model for `DELETE /v1/files/:file_path`."""

    message: str


class GeneratedFileType(str, Enum):
    """The type of file generated by OpenAI."""

    TEXT = "Text"
    IMAGE = "Image"
    AUDIO = "Text-to-Speech"


# create/update (Crud)
class PostFileResponse(BaseModel):
    """Response model for `POST /v1/files/generated/:file_path`."""

    file_path: str = Field(
        description="The path to the file.",
        json_schema_extra={"example": "path/to/file.txt"},
    )
    message: str = Field(
        description="The message indicating the status of the operation.",
        json_schema_extra={"example": "New file generated and uploaded at path: path/to/file.txt"},
    )
