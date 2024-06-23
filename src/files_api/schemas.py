"""FastAPI application for managing files in an S3 bucket."""

from datetime import datetime
from typing import (
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)
from typing_extensions import Self

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
    """Response model for PUT /v1/files/{file_path}."""

    file_path: str
    message: str


# read (cRud)
class GetFilesQueryParams(BaseModel):
    """Query parameters for GET /v1/files."""

    page_size: int = Field(
        default=DEFAULT_GET_FILES_PAGE_SIZE,
        ge=DEFAULT_GET_FILES_MIN_PAGE_SIZE,
        le=DEFAULT_GET_FILES_MAX_PAGE_SIZE,
    )
    directory: Optional[str] = DEFAULT_GET_FILES_DIRECTORY
    page_token: Optional[str] = None

    @model_validator(mode="after")
    def check_page_token(self) -> Self:
        """Ensure that page_token is mutually exclusive with page_size and directory."""
        if self.page_token:
            get_files_query_params: dict = self.model_dump(exclude_defaults=True)
            page_size_set: bool = "page_size" in get_files_query_params.keys()
            directory_set: bool = "directory" in get_files_query_params.keys()
            if page_size_set or directory_set:
                raise ValueError("page_token is mutually exclusive with page_size and directory")
        return self


# read (cRud)
class GetFilesResponse(BaseModel):
    """Response model for GET /v1/files/{file_path}."""

    files: List[FileMetadata]
    next_page_token: Optional[str]


# delete (cruD)
class DeleteFileResponse(BaseModel):
    """Response model for DELETE /v1/files/{file_path}."""

    message: str
