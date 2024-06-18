"""FastAPI application for managing files in an S3 bucket."""

from typing import Union

from fastapi import FastAPI

from files_api.routes import ROUTER
from files_api.settings import Settings


def create_app(settings: Union[Settings, None] = None) -> FastAPI:
    """Create a FastAPI application."""
    # s3_bucket_name = s3_bucket_name or os.environ["S3_BUCKET_NAME"]
    settings = settings or Settings()

    app = FastAPI()
    # app.state.s3_bucket_name = s3_bucket_name
    app.state.settings = settings
    app.include_router(ROUTER)
    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
