from __future__ import annotations

import json
import os
import sys

import loguru
from fastapi import Request
from loguru import logger


def serialize_extra_keys(record: loguru.Record) -> loguru.Record:
    extra = record["extra"]
    level = record["level"].name
    if extra:
        extra["level"] = level
        record["extra"] = json.dumps(extra)
    return record


def configure_logger() -> loguru.Logger:
    """Configure the logger for the FastAPI application."""
    logging_config = {
        "handlers": [
            {
                "sink": sys.stdout,
                "format": "{file}:{line}:{function} | {message} | {extra}",
                "filter": serialize_extra_keys,
                "diagnose": False,
                "backtrace": False,
            },
        ],
    }

    # Remove the default logger config and add custom configurations
    logger.remove()
    logger.configure(**logging_config)
    return logger


async def inject_lambda_context(request: Request, call_next):
    """Middleware to add Lambda context to FastAPI request scope."""

    try:
        # Get the Lambda context from the incoming request headers
        context = request.scope["aws.context"]
        # https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html
        lambda_context = {
            "function_name": os.environ["AWS_LAMBDA_FUNCTION_NAME"],  # context.function_name,
            "function_memory_size": os.environ["AWS_LAMBDA_FUNCTION_MEMORY_SIZE"],  # context.memory_limit_in_mb,
            "function_arn": context.invoked_function_arn,
            "function_request_id": context.aws_request_id,
            "xray_trace_id": os.environ["_X_AMZN_TRACE_ID"].split(";")[0].strip("Root="),
        }
    except KeyError:
        lambda_context = {
            "function_arn": "local-development",
            "function_memory_size": "local-development",
            "function_name": "local-development",
            "function_request_id": "local-development",
        }

    with logger.contextualize(**lambda_context):
        response = await call_next(request)

    return response

