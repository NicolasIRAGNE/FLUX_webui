# Base image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files into the container
COPY interface.py .
COPY requirements.txt .
COPY prompts.md .

# Set the environment variable
ENV GRADIO_SERVER_NAME="0.0.0.0"

# Run the Gradio application
CMD ["python", "interface.py"]
