"""FastAPI application for managing files in an S3 bucket."""

from textwrap import dedent
from typing import Union

import pydantic
from fastapi import FastAPI
from fastapi.routing import APIRoute

from files_api.errors import (
    handle_broad_exceptions,
    handle_pydantic_validation_error,
)
from files_api.routes import ROUTER
from files_api.settings import Settings


def custom_generate_unique_id(route: APIRoute):
    return f"{route.tags[0]}-{route.name}"


def create_app(settings: Union[Settings, None] = None) -> FastAPI:
    """Create a FastAPI application."""
    # s3_bucket_name = s3_bucket_name or os.environ["S3_BUCKET_NAME"]
    settings = settings or Settings()

    app = FastAPI(
        title="Files API",
        summary="Store and Retrieve Files.",
        version="v1",  # a fancier version would read the semver from pkg metadata
        description=dedent(
            """\
        <a href="https://github.com/avr2002" target="_blank">\
            <img src="https://img.shields.io/badge/Maintained%20by-Amit%20Vikram%20Raj-F4BBFF?style=for-the-badge">\
        </a>

        | Helpful Links | Notes |
        | --- | --- |
        | [MLOps Club](https://mlops-club.org) | ![MLOps Club](https://img.shields.io/badge/Memember%20of-MLOps%20Club-05998B?style=for-the-badge) |
        | [Project Repo](https://github.com/avr2002/cloud-engineering-project) | `avr2002/cloud-engineering-project` |
        """
        ),
        contact={"name": "Amit", "url": "https://www.linkedin.com/in/avr27/", "email": "avr13405@gmail.com"},
        license_info={"name": "Apache 2.0", "identifier": "MIT"},
        docs_url="/",  # its easier to find the docs when they live on the base url
        redoc_url="/redoc",
        generate_unique_id_function=custom_generate_unique_id,
    )
    # app.state.s3_bucket_name = s3_bucket_name
    app.state.settings = settings
    app.include_router(ROUTER)
    app.add_exception_handler(
        exc_class_or_status_code=pydantic.ValidationError,
        handler=handle_pydantic_validation_error,
    )
    app.middleware("http")(handle_broad_exceptions)
    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
