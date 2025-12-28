# Use an official lightweight Python image.
# 3.10-slim is a good balance of size and compatibility.
FROM python:3.10-slim

# Prevent Python from writing pyc files to disc and buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies required for:
# - opencv/computer vision tools (libgl1, libglib2.0-0)
# - PDF processing (poppler-utils)
# - OCR (tesseract-ocr)
# - Audio/Video (ffmpeg)
# - Building some python packages (build-essential, gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create necessary directories for runtime
RUN mkdir -p uploads static/audio

# Expose the port the app runs on (Render sets $PORT, default Flask is 5000)
# We will use gunicorn to bind to the environment's PORT
CMD gunicorn main:app --bind 0.0.0.0:$PORT
