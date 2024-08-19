"""Custom error handlers for the Fast API application."""

# import traceback

import pydantic
from fastapi import (
    Request,
    status,
)
from fastapi.responses import JSONResponse

from files_api.logger import logger
# from files_api import logger
# from loguru import logger


# Fast API Docs on Middleware: https://fastapi.tiangolo.com/tutorial/middleware/
async def handle_broad_exceptions(request: Request, call_next):
    """Handle any exception that goes unhandled by a more specific exception handler."""
    try:
        return await call_next(request)
    except Exception as exc:  # pylint: disable=broad-except
        # traceback.print_exc()
        logger.opt(exception=True).error("Unhandled Exception: {}", exc)
        # metrics.add_metric(name="UnhandledExceptions", unit="Count", value=1)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An unexpected error occurred.",
                "detail": "Internal Server Error",
            },
        )


# Fast API Docs on Error Handlers:
# https://fastapi.tiangolo.com/tutorial/handling-errors/?h=error#install-custom-exception-handlers
async def handle_pydantic_validation_error(request: Request, exc: pydantic.ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = exc.errors()
    logger.error("Validation Error")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": [
                {
                    "msg": error["msg"],
                    "input": error["input"],
                }
                for error in errors
            ]
        },
    )
