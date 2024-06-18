"""FastAPI application for managing files in an S3 bucket."""

from datetime import datetime
from typing import (
    List,
    Optional,
)

from pydantic import BaseModel


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
