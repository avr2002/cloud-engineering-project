"""FastAPI application for managing files in an S3 bucket."""

from datetime import datetime
from typing import (
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)

DEFAULT_GET_FILES_PAGE_SIZE = 10
DEFAULT_GET_FILES_MIN_PAGE_SIZE = 1
DEFAULT_GET_FILES_MAX_PAGE_SIZE = 100
DEFAULT_GET_FILES_DIRECTORY = ""


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
class GetFilesQueryParams(BaseModel):
    """Query parameters for GET /files."""

    page_size: int = Field(
        default=DEFAULT_GET_FILES_PAGE_SIZE,
        ge=DEFAULT_GET_FILES_MIN_PAGE_SIZE,
        le=DEFAULT_GET_FILES_MAX_PAGE_SIZE,
    )
    directory: Optional[str] = DEFAULT_GET_FILES_DIRECTORY
    page_token: Optional[str] = None


# read (cRud)
class GetFilesResponse(BaseModel):
    """Response model for GET /files/{file_path}."""

    files: List[FileMetadata]
    next_page_token: Optional[str]
    remaining_pages: Optional[int]


# delete (cruD)
class DeleteFileResponse(BaseModel):
    """Response model for DELETE /files/{file_path}."""

    message: str
