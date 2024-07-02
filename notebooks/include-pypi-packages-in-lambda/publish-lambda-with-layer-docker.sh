# Publish the lambda code to AWS Lambda using the AWS CLI
# aws --cli-auto-prompt # Enable auto prompt for the AWS CLI

set -ex


# Clean up the artifacts, lambda-env directory and lambda.zip file if they exist
rm -rf lambda-env || true
rm lambda-layer.zip || true
rm lambda.zip || true


# Install dependencies in a docker container: https://gallery.ecr.aws/

# Get the current user ID and group ID
USER_ID=$(id -u)
GROUP_ID=$(id -g)

docker logout || true
docker pull public.ecr.aws/lambda/python:3.12-arm64
docker run --rm \
    --user $USER_ID:$GROUP_ID \
    --volume $(pwd):/out \
    --entrypoint /bin/bash \
    public.ecr.aws/lambda/python:3.12-arm64 \
    -c ' \
    pip install \
        -r /out/requirements.txt \
        --target /out/lambda-env/python \
    '


# Bundle the dependencies into a zip file to create a lambda layer
cd lambda-env
zip -r ../lambda-layer.zip ./

# Go back to the root directory, and clean up the lambda.zip file if it exists, 
# and create a new one with the lambda code
cd ../src
zip -r ../lambda.zip ./
cd ..

# cp lambda_function.py lambda-env/

# Export the AWS_PROFILE and AWS_REGION environment variables
export AWS_PROFILE=cloud-course
export AWS_REGION=ap-south-1

# Publish the lambda code to AWS Lambda
aws lambda update-function-code \
    --function-name lambda-demo \
    --zip-file fileb://./lambda.zip \
    --output json | cat


# Publish the lambda layer to AWS Lambda, and store the LayerVersionArn in a variable
LAYER_VERSION_ARN=$(aws lambda publish-layer-version \
    --layer-name cloud-course-python-deps \
    --compatible-runtimes python3.12 \
    --zip-file fileb://./lambda-layer.zip \
    --compatible-architectures arm64 \
    --query 'LayerVersionArn' \
    --output text | cat)

# Sample LayerVersionArn: "arn:aws:lambda:ap-south-1:730335491176:layer:cloud-course-python-deps:1"

# Update the lambda function configuration to include the latest published layer
aws lambda update-function-configuration \
    --function-name lambda-demo \
    --layers $LAYER_VERSION_ARN \
    --output json | cat