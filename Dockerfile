FROM python:3.9-slim

# System dependencies for moviepy, ffmpeg, and other tools
RUN apt-get update && \
    apt-get install -y ffmpeg libsm6 libxext6 git && \
    rm -rf /var/lib/apt/lists/*

# Create output directory and set permissions
RUN mkdir -p /tmp/generated_videos && chown appuser:appuser /tmp/generated_videos

# Set working directory to the worker code
WORKDIR /app/protovideo-worker

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Add a non-root user for security
RUN useradd -m appuser

USER appuser

RUN python -c "from chatterbox.tts import ChatterboxTTS; model = ChatterboxTTS.from_pretrained(device='cpu'); wav = model.generate('test audio'); print('Test audio generated')"

# Default command: run FastAPI app with uvicorn
CMD ["python", "main_worker.py"]