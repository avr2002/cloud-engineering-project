FROM python:3.11-slim-bookworm

WORKDIR /app

# copy/create bare minimum files needed to install dependencies
COPY pyproject.toml /app/
RUN mkdir -p /app/src/files_api/
RUN touch /app/src/files_api/__init__.py

# install dependencies from pyproject.toml
RUN pip install --upgrade pip
RUN pip install uvicorn
RUN pip install --editable "/app/"

# copy the rest of the source code
COPY ./src/ /app/src/
# COPY ./tests/ /app/tests/

# create the s3 bucket if desired(if false then using real S3 bucket), then start the fastapi app
CMD (\
    if [ "$CREATE_BUCKET_ON_STARTUP" = "true" ]; then \
    python -c "import boto3; boto3.client('s3').create_bucket(Bucket='${S3_BUCKET_NAME}')"; \
    fi \
    ) \
    && uvicorn files_api.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
