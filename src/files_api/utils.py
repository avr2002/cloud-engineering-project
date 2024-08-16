import os
from typing import Callable

from fastapi import (
    Request,
    Response,
)
from fastapi.routing import APIRoute

from files_api.logger_config import logger
import threading

# Use thread-local storage to handle cold start per thread
_thread_local = threading.local()
_thread_local.cold_start = True

# # Global variable to track cold starts
# cold_start = True


async def inject_lambda_context(request: Request, call_next):
    """Middleware to add Lambda context to FastAPI request scope."""
    # global cold_start  # Declare that we're using the global variable
    # Capture cold start status from thread-local storage
    cold_start = _thread_local.cold_start

    try:
        # Get the Lambda context from the incoming request headers
        context = request.scope["aws.context"]
        # https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html
        lambda_context = {
            "cold_start": cold_start,
            "function_name": os.environ["AWS_LAMBDA_FUNCTION_NAME"],  # context.function_name,
            "function_memory_size": os.environ["AWS_LAMBDA_FUNCTION_MEMORY_SIZE"],  # context.memory_limit_in_mb,
            "function_arn": context.invoked_function_arn,
            "function_request_id": context.aws_request_id,
            "xray_trace_id": os.environ["_X_AMZN_TRACE_ID"].split(";")[0].strip("Root="),
        }

        # Get the correlation ID from the incoming request headers
        correlation_id = request.headers.get("X-Correlation-ID", None)
        if not correlation_id:
            # If empty, use request ID from AWS Context
            correlation_id = request.scope["aws.context"].aws_request_id
    except KeyError:
        lambda_context = {
            "cold_start": cold_start,
            "function_arn": "local-development",
            "function_memory_size": "local-development",
            "function_name": "local-development",
            "function_request_id": "local-development",
        }
        correlation_id = "local-development"

    with logger.contextualize(correlation_id=correlation_id, **lambda_context):
        response = await call_next(request)

    # # After handling the request, set cold_start to False for subsequent invocations
    # cold_start = False
    
     # Set cold_start to False for subsequent requests
    _thread_local.cold_start = False

    return response


class LoggerRouteHandler(APIRoute):
    """Custom router to add FastAPI context to logs."""

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            # Add fastapi context to logs
            context = {
                "path": request.url.path,
                "route": self.path,
                "method": request.method,
            }
            with logger.contextualize(fastapi=context):
                return await original_route_handler(request)

        return route_handler
