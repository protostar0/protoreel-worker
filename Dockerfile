FROM python:3.9-slim

# Install system deps
RUN apt-get update && \
    apt-get install -y ffmpeg libsm6 libxext6 git && \
    rm -rf /var/lib/apt/lists/*

# Add non-root user

# Set working dir
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY . .

# Change user

# Run the worker
ENTRYPOINT ["python", "main_worker.py"]
