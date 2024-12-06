#!/bin/bash

# Set the configuration file content
CONFIG_CONTENT=$(cat <<EOF
{
  "agent": {
    "metrics_collection_interval": 10,
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
  },
  "metrics": {
    "namespace": "MyNamespace",
    "append_dimensions": {
      "InstanceId": "i-12345678"
    },
    "metrics_collected": {
      "statsd": {
        "service_address": ":8125"
      }
    }
  }
}
EOF
)

# Create the configuration file
CONFIG_FILE="config.json"
echo "$CONFIG_CONTENT" > $CONFIG_FILE

# Print the configuration file path
echo "Configuration file created at: $(pwd)/$CONFIG_FILE"

# Function to check if a container is running and stop/remove it if necessary
cleanup_container() {
    CONTAINER_NAME=$1
    if [ $(docker ps -q -f name=$CONTAINER_NAME) ]; then
        echo "Stopping the existing CloudWatch agent container..."
        docker stop $CONTAINER_NAME
        echo "Removing the existing CloudWatch agent container..."
        docker rm $CONTAINER_NAME
    elif [ $(docker ps -a -q -f name=$CONTAINER_NAME) ]; then
        echo "Removing the stopped CloudWatch agent container..."
        docker rm $CONTAINER_NAME
    fi
}

# Cleanup any existing container with the name cloudwatch-agent-unique
cleanup_container "cloudwatch-agent-unique"

# Run the CloudWatch agent container
echo "Starting the CloudWatch agent container..."
docker run -v "$(pwd)/$CONFIG_FILE":/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
           -p 25888:25888/udp \
           -p 8125:8125/udp \
           --name cloudwatch-agent-unique \
           amazon/cloudwatch-agent:latest \
           /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
           -a fetch-config \
           -m onPremise \
           -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
           -s

# Check the status of the container
if [ $(docker ps -q -f name=cloudwatch-agent-unique) ]; then
    echo "CloudWatch agent container is running successfully."
else
    echo "Failed to start the CloudWatch agent container."
    echo "CloudWatch agent logs:"
    docker logs cloudwatch-agent-unique
fi
