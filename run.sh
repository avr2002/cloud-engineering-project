#!/bin/bash

set -e

#####################
# --- Constants --- #
#####################

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MINIMUM_TEST_COVERAGE_PERCENT=0


##########################
# --- Task Functions --- #
##########################

# install core and development Python dependencies into the currently activated venv
function install {
    python -m pip install --upgrade pip
    python -m pip install --editable "$THIS_DIR/[dev]"
}


function install-generated-sdk {
    # install the generated SDK in newly created venv
    python -m pip install --upgrade pip
    python -m pip install --editable "$THIS_DIR/files-api-sdk/" \
        --config-settings editable_mode=strict
}


function generate-client-library {
    # Get the current user ID and group ID to run the docker command with so that 
    # the generated SDK folder doesn't have root permissions, instead user level permission
    USER_ID=$(id -u)
    GROUP_ID=$(id -g)

    docker run --rm \
    --user $USER_ID:$GROUP_ID \
    -v $PWD:/local openapitools/openapi-generator-cli generate \
    --generator-name python-pydantic-v1 \
    --input-spec /local/openapi.json \
    --output /local/files-api-sdk \
    --package-name files_api_sdk
}


function run {
    AWS_PROFILE=cloud-course\
    S3_BUCKET_NAME=python-aws-cloud-course-bucket\
    uvicorn 'files_api.main:create_app' --reload
}
function run-local {
    if [ -f .env ]; then
        export $(cat .env | xargs)
    fi
    
    uvicorn 'files_api.main:create_app' --reload
}

# start the FastAPI app, pointed at a mocked aws endpoint
function run-mock {
    set +e

    # Start moto.server in the background on localhost:5000
    python -m moto.server -p 5000 &
    MOTO_PID=$!

    # point the AWS CLI and boto3 to the mocked AWS server using mocked credentials
    export AWS_ENDPOINT_URL="http://localhost:5000"
    export AWS_SECRET_ACCESS_KEY="mock"
    export AWS_ACCESS_KEY_ID="mock"
    export S3_BUCKET_NAME="some-bucket"

    # create a bucket called "some-bucket" using the mocked aws server
    aws s3 mb "s3://$S3_BUCKET_NAME"

    # Start the Docker Compose to mock the OpenAI API
    docker compose --file ./mock-openai-docker-compose.yaml up --detach

    # Trap EXIT signal to kill the moto.server process when uvicorn stops
    trap 'kill $MOTO_PID; docker compose --file ./mock-openai-docker-compose.yaml down' EXIT

    # Set AWS endpoint URL and start FastAPI app with uvicorn in the foreground
    uvicorn src.files_api.main:create_app --reload

    # Wait for the moto.server process to finish (this is optional if you want to keep it running)
    wait $MOTO_PID
}

# run linting, formatting, and other static code quality tools
function lint {
    pre-commit run --all-files
}

# same as `lint` but with any special considerations for CI
function lint:ci {
    # We skip no-commit-to-branch since that blocks commits to `main`.
    # All merged PRs are commits to `main` so this must be disabled.
    SKIP=no-commit-to-branch pre-commit run --all-files
}

# execute tests that are not marked as `slow`
function test:quick {
    run-tests -m "not slow" ${@:-"$THIS_DIR/tests/"}
}

# execute tests against the installed package; assumes the wheel is already installed
function test:ci {
    INSTALLED_PKG_DIR="$(python -c 'import files_api; print(files_api.__path__[0])')"
    # in CI, we must calculate the coverage for the installed package, not the src/ folder
    COVERAGE_DIR="$INSTALLED_PKG_DIR" run-tests
}

# (example) ./run.sh test tests/test_states_info.py::test__slow_add
function run-tests {
    PYTEST_EXIT_STATUS=0

    # clean the test-reports dir
    rm -rf "$THIS_DIR/test-reports" || mkdir "$THIS_DIR/test-reports"

    # execute the tests, calculate coverage, and generate coverage reports in the test-reports dir
    python -m pytest ${@:-"$THIS_DIR/tests/"} \
        --cov "${COVERAGE_DIR:-$THIS_DIR/src}" \
        --cov-report html \
        --cov-report term \
        --cov-report xml \
        --junit-xml "$THIS_DIR/test-reports/report.xml" \
        --cov-fail-under "$MINIMUM_TEST_COVERAGE_PERCENT" || ((PYTEST_EXIT_STATUS+=$?))
    mv coverage.xml "$THIS_DIR/test-reports/" || true
    mv htmlcov "$THIS_DIR/test-reports/" || true
    mv .coverage "$THIS_DIR/test-reports/" || true
    return $PYTEST_EXIT_STATUS
}

function test:wheel-locally {
    source deactivate || true
    rm -rf test-env || true
    python -m venv test-env
    source test-env/bin/activate
    clean || true
    pip install build
    build
    WHEEL_FPATH=$(ls ./dist/*.whl)
    pip install "${WHEEL_FPATH}[test]" || true
    test:ci || true
    source deactivate || true
    rm -rf test-env || true
    clean || true
}

# serve the html test coverage report on localhost:8000
function serve-coverage-report {
    python -m http.server --directory "$THIS_DIR/test-reports/htmlcov/" 8000
}

# build a wheel and sdist from the Python source code
function build {
    python -m build --sdist --wheel "$THIS_DIR/"
}

function release:test {
    lint
    clean
    build
    publish:test
}

function release:prod {
    release:test
    publish:prod
}

function publish:test {
    try-load-dotenv || true
    twine upload dist/* \
        --repository testpypi \
        --username=__token__ \
        --password="$TEST_PYPI_TOKEN"
}

function publish:prod {
    try-load-dotenv || true
    twine upload dist/* \
        --repository pypi \
        --username=__token__ \
        --password="$PROD_PYPI_TOKEN"
}

# remove all files generated by tests, builds, or operating this codebase
function clean {
    rm -rf dist build coverage.xml test-reports
    find . \
      -type d \
      \( \
        -name "*cache*" \
        -o -name "*.dist-info" \
        -o -name "*.egg-info" \
        -o -name "*htmlcov" \
      \) \
      -not -path "*env*/*" \
      -exec rm -r {} + || true

    find . \
      -type f \
      -name "*.pyc" \
      -not -path "*env/*" \
      -exec rm {} +
}

# export the contents of .env as environment variables
function try-load-dotenv {
    if [ ! -f "$THIS_DIR/.env" ]; then
        echo "no .env file found"
        return 1
    fi

    while read -r line; do
        export "$line"
    done < <(grep -v '^#' "$THIS_DIR/.env" | grep -v '^$')
}

# print all functions in this file
function help {
    echo "$0 <task> <args>"
    echo "Tasks:"
    compgen -A function | cat -n
}

TIMEFORMAT="Task completed in %3lR"
time ${@:-help}
