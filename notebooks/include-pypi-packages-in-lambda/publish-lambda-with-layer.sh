# Publish the lambda code to AWS Lambda using the AWS CLI
# aws --cli-auto-prompt # Enable auto prompt for the AWS CLI

# Clean up the artifacts, lambda-env directory and lambda.zip file if they exist
rm -rf lambda-env || true
rm lambda-layer.zip || true
rm lambda.zip || true


# Install the required packages to the lambda-env directory
# https://docs.aws.amazon.com/lambda/latest/dg/python-layers.html#python-layer-paths

# create a directory called python in the lambda-env directory for the dependencies to be installed in.
mkdir -p lambda-env/python
pip install --target ./lambda-env/python -r requirements.txt

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
    --compatible-architectures x86_64 \
    --query 'LayerVersionArn' \
    --output text | cat)

# Sample LayerVersionArn: "arn:aws:lambda:ap-south-1:730335491176:layer:cloud-course-python-deps:1"

# Update the lambda function configuration to include the latest published layer
aws lambda update-function-configuration \
    --function-name lambda-demo \
    --layers $LAYER_VERSION_ARN \
    --output json | cat
