# Publish the lambda code to AWS Lambda using the AWS CLI
# aws --cli-auto-prompt # Enable auto prompt for the AWS CLI

# Clean up the artifacts, lambda-env directory and lambda.zip file if they exist
rm -rf lambda-env || true
rm lambda.zip || true


# Install the required packages to the lambda-env directory
pip install --target ./lambda-env requests fastapi

# Bundle the dependencies and the lambda code into a zip file
cp lambda_function.py lambda-env/
cd lambda-env
zip -r ../lambda.zip ./

# Export the AWS_PROFILE and AWS_REGION environment variables
export AWS_PROFILE=cloud-course
export AWS_REGION=ap-south-1

# Publish the lambda code to AWS Lambda
aws lambda update-function-code \
--function-name lambda-demo \
--zip-file fileb://../lambda.zip
