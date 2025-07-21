FROM python:3.9-slim

# System dependencies for moviepy, ffmpeg, and other tools
RUN apt-get update && \
    apt-get install -y ffmpeg libsm6 libxext6 git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Add a non-root user for security
RUN useradd -m appuser

# Create output directory and set permissions
RUN mkdir -p /tmp/generated_videos && chown appuser:appuser /tmp/generated_videos

USER appuser

# Expose FastAPI port
EXPOSE 8080

# Default command: run FastAPI app with uvicorn
CMD ["uvicorn", "main_worker:app", "--host", "0.0.0.0", "--port", "8080"] 
