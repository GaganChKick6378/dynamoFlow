# Dockerfile

# Use the official Langflow image as the base
FROM langflowai/langflow:latest

# Set the working directory inside the container
WORKDIR /app

# Set environment variables for Langflow and Langsmith
ENV LANGFLOW_HOST=0.0.0.0
ENV LANGFLOW_PORT=7860
ENV LANGCHAIN_TRACING_V2=true
ENV LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
ENV LANGCHAIN_API_KEY=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
ENV LANGCHAIN_PROJECT=langflow-monitoring
ENV LANGFLOW_CUSTOM_COMPONENTS_PATH=/app/custom_components
ENV PYTHONPATH=/app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python packages from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Create custom_components directory
RUN mkdir -p /app/custom_components

# Copy custom components
COPY ./custom_components /app/custom_components/

# Expose the port that Langflow will run on
EXPOSE 7860

# The command to start Langflow (already set in the base image, but can be explicit)
CMD ["langflow", "run", "--host", "0.0.0.0", "--port", "7860"]