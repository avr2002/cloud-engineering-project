# Logging

## Log Format

The docs [here](https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.add) cover

- Log record attributes, e.g. `time`, `level`, `name`, `function`, `line`, `message`, `extra`
- Time formatting, e.g. `YYYY-MM-DD HH:mm:ss.SSS`
- Color formatting, e.g. `<green>`, `<level>`, `<cyan>`, `<dim>`

### Example

```markdown
<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <bold><white>{message}</white></bold> | <dim>{extra}</dim>
```

## Code snippets for logging in FastAPI

### Request/Response info

```python
def log_request_info(request: Request):
    """Log the request info."""
    request_info = {
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params.items()),
        "path_params": dict(request.path_params.items()),
        "headers": dict(request.headers.items()),  # note: logging headers can leak secrets
        "base_url": str(request.base_url),
        "url": str(request.url),
        "client": str(request.client),
        "server": str(request.scope.get("server", "unknown")),
        "cookies": dict(request.cookies.items()), # note: logging cookies can leak secrets
    }
    logger.debug("Request received", http_request=request_info)


def log_response_info(response: Response):
    """Log the response info."""
    response_info = {
        "status_code": response.status_code,
        "headers": dict(response.headers.items()),
    }
    logger.debug("Response sent", http_response=response_info)
```

### Route Handler

> ⚠️ Warning: route handlers are advanced. If set up incorrectly, they can mess up the FastAPI framework ([docs](https://fastapi.tiangolo.com/how-to/custom-request-and-route/)).

```python
from typing import Callable

from fastapi import (
    Request,
    Response,
)
from fastapi.routing import APIRoute

class RouteHandler(APIRoute):
    """Custom router to add FastAPI context to logs."""

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            response: Response = await original_route_handler(request)
            return response

        return route_handler
```

Hook it up like this:

```python
# routes.py

...

FILES_ROUTER.route_class = RouteHandler
GENERATED_FILES_ROUTER.route_class = RouteHandler
```

OR

```python
# main.py

def create_app() -> FastAPI:
    ...
    app.router.route_class = RouteHandler
    return app
```

Note the route handler will not be executed when requesting the FastAPI docs page.

### Keeping tracebacks in one log event/statement

CloudWatch splits log events on `\n` newline characters. This is a problem for stack traces, because tracebacks
always show each function in the call stack on a new line.

To fix this, we'll have to reformat the traceback to replace the newline characters with a "carriage return" character.
It will still appear as multiple lines in the cloudwatch or in the terminal... but CloudWatch will treat it as a single log event.

```python
# logger.py
import traceback

def configure_logger():
    logger.remove()
    logger.add(
        sink=sys.stdout,
        diagnose=False,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <bold><white>{message}</white></bold> | <dim>{extra}</dim> {stacktrace}",
        filter=process_log_record,
    )


def process_log_record(record: "loguru.Record") -> "loguru.Record":
    r"""
    Inject transformed metadata into each log record before they are passed to the formatter.

    For instance,

    1. Serialize the "extra" field to JSON so that renders nicely in CloudWatch logs.
    2. For error logs, add a traceback with \r instead of \n so that CloudWatch does not
       split the traceback into multiple log events.
    """
    extra = record["extra"]

    # serialize "extra" field to JSON
    if extra:
        record["extra"] = json.dumps(extra, default=str)

    # add stacktrace to log record
    record["stacktrace"] = ""
    if record["exception"]:
        err = record["exception"]
        stacktrace = get_formatted_stacktrace(err, replace_newline_character_with_carriage_return=True)
        record["stacktrace"] = stacktrace

    return record

def get_formatted_stacktrace(loguru_record_exception, replace_newline_character_with_carriage_return: bool) -> str:
    """Get the formatted stacktrace for the current exception."""
    exc_type, exc_value, exc_traceback = loguru_record_exception
    stacktrace_: list[str] = traceback.format_exception(exc_type, exc_value, exc_traceback)
    stacktrace: str = "".join(stacktrace_)
    if replace_newline_character_with_carriage_return:
        stacktrace = stacktrace.replace("\n", "\r")
    return stacktrace
```

### Lambda Context (and naive request ID)

Adding lambda context to our logs can be incredibly useful for two reasons:

#### 1. Help locate the logs based on the function or runtime that produced them

In production, we might have many servers running our service code. Or our code could be running in AWS Lambda.

A failure might occur due to issues with a server, not due to our code. (or the interaction the server has with our code).

For example, if one server is out of memory, or at CPU capacity, requests may be more likely to fail when running on that server.
The failures might have nothing to do with our code.

In cases like this, it is useful to be able to look up logs based on the server they came from. In this case, we are
using AWS lambda rather than docker containers or EC2 instances. So, we will add the lambda context to our logs, e.g.
the function name, ARN, memory size.

#### 2. Add a request ID!

Adding a request ID would help us find all the logs emitted by a single request. This is game changing! 

We will use the "lambda request ID" as the request ID when the function is running in lambda. Otherwise, we will generate
a random request ID.

We will also return the request ID in the response headers, so if the client gets an error, they can use it to look up
the related logs (or send the ID to the dev team responsible for the service).

```python
# logger.py

import os
from uuid import uuid4


async def inject_lambda_context__middleware(request: Request, call_next):
    """Middleware to add Lambda context to FastAPI request scope."""
    try:
        # Get the Lambda context from the incoming request headers
        context = request.scope["aws.context"]
        # https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html
        lambda_context = {
            "function_name": os.environ["AWS_LAMBDA_FUNCTION_NAME"],  # context.function_name,
            "function_arn": context.invoked_function_arn,
            "function_memory_size": os.environ["AWS_LAMBDA_FUNCTION_MEMORY_SIZE"],  # context.memory_limit_in_mb,
            "function_request_id": context.aws_request_id,
        }
    except KeyError:
        # when running locally, set mocked values as context
        lambda_context = {
            "function_name": "n/a",
            "function_arn": "n/a",
            "function_memory_size": "n/a",
            "function_request_id": str(uuid4()),
        }

    with logger.contextualize(aws_lambda=lambda_context):
        response = await call_next(request)

    response.headers["X-Request-ID"] = lambda_context["function_request_id"]
    return response

```

### Lambda cold start

```python
# Global variable to track cold starts
# pylint: disable=invalid-name
cold_start = True


def log_lambda_cold_start():
    """Log the cold start of the Lambda function."""
    # pylint: disable=global-statement
    global cold_start
    message = "Cold Start" if cold_start else "Warm Start"
    logger.info(message, cold_start=cold_start)
    cold_start = False
```