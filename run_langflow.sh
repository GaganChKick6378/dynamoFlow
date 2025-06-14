#!/bin/bash

# Run Langflow with custom components mounted
docker run -p 7861:7860 \
  -v $(pwd)/custom_components:/app/custom_components \
  -v $(pwd)/requirements.txt:/app/requirements.txt \
  -e LANGFLOW_CUSTOM_COMPONENTS_PATH=/app/custom_components \
  -e PYTHONPATH=/app \
  -e OPENAI_API_KEY=${OPENAI_API_KEY} \
  -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
  -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
  -e AWS_DEFAULT_REGION=us-west-2 \
  langflowai/langflow:latest \
  bash -c "pip install -r /app/requirements.txt && langflow run --host 0.0.0.0 --port 7860" 