#!/usr/bin/env bash
PORT=8000
ENV_FILE=""

if ! command -v sam &> /dev/null
then
    echo "SAM CLI not found. Install from https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
    exit 1
fi
if ! command -v docker &> /dev/null
then
    echo "Warning: Docker not found. SAM local requires Docker to run Lambda functions. Install and start Docker Desktop."
fi

echo "Building SAM application..."
sam build || exit 1

echo "Starting SAM local API on port $PORT"
if [ -n "$ENV_FILE" ]; then
  sam local start-api --port $PORT --env-vars "$ENV_FILE"
else
  sam local start-api --port $PORT
fi
