FROM python:3.11-slim

WORKDIR /app

# copy/create bare minimum files needed to install dependencies
COPY pyproject.toml /app/
RUN mkdir -p /app/src/files_api/
RUN touch /app/src/files_api/__init__.py

# install dependencies from pyproject.toml
RUN pip install --upgrade pip
RUN pip install --editable "/app/[docker]"

# copy the rest of the source code
COPY ./src/ /app/src/
COPY ./tests/ /app/tests/

ENV PORT=8000

# create the S3 bucket if desired, then start the fastapi app
CMD (\
    if [ "$CREATE_BUCKET_ON_STARTUP" = "true" ]; then \
    python -c "import boto3; boto3.client('s3').create_bucket(Bucket='$S3_BUCKET_NAME')"; \
    fi; \
    ) && \
    gunicorn \
    --workers 4 \
    --worker-class "uvicorn.workers.UvicornWorker" \
    --bind "0.0.0.0:$PORT" \
    --reload \
    "files_api.main:create_app()"
