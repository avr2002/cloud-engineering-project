from __future__ import annotations

import json
import os
import sys
import traceback

import loguru
from fastapi import Request
from loguru import logger


def configure_logger() -> loguru.Logger:
    """Configure the logger for the FastAPI application."""
    logging_config = {
        "handlers": [
            {
                "sink": sys.stdout,
                "format": "<level>{level}</level> | <cyan>{file}:{line}:{function}</cyan> | <white>{message}</white> | <dim><white>{extra}</white></dim> {stacktrace}",
                "filter": postprocess_log_record,
                "diagnose": False,
                "backtrace": False,
                "colorize": True,
            },
        ],
    }

    # Remove the default logger config and add custom configurations
    logger.remove()
    logger.configure(**logging_config)
    return logger


def postprocess_log_record(record: loguru.Record) -> loguru.Record:
    """
    Inject transformed metadata into each log record before they are passed to the formatter.

    For instance,

    1. Serialize the "extra" field to JSON so that renders nicely in CloudWatch logs.
    2. For error logs, add a traceback with \r instead of \n so that CloudWatch does not
       split the traceback into multiple log events.
    """
    extra = record["extra"]
    level = record["level"].name

    # serialize "extra" field to JSON
    if extra:
        extra["level"] = level
        record["extra"] = json.dumps(extra, default=str)  # type: ignore

    # add stacktrace to log record
    record["stacktrace"] = ""  # type: ignore
    if record["exception"]:
        exc = record["exception"]
        stacktrace = get_formatted_stacktrace(exc, replace_newline_character_with_carriage_return=True)
        record["stacktrace"] = stacktrace  # type: ignore

    return record


def get_formatted_stacktrace(
    loguru_record_exception: loguru.RecordException, replace_newline_character_with_carriage_return: bool
) -> str:
    """Get the formatted stacktrace for the current exception."""
    exc_type, exc_value, exc_traceback = loguru_record_exception
    stacktrace: list[str] = traceback.format_exception(exc_type, exc_value, exc_traceback)
    stacktrace: str = "".join(stacktrace)  # type: ignore
    if replace_newline_character_with_carriage_return:
        stacktrace = stacktrace.replace("\n", "\r")  # type: ignore
    return stacktrace  # type: ignore


async def inject_lambda_context__middleware(request: Request, call_next):
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

    with logger.contextualize(aws_lambda=lambda_context):
        response = await call_next(request)

    return response
