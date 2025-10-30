FROM python:3.11-slim

# Install system dependencies for OpenCV and AI libraries
# Including build tools for compiling insightface
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    build-essential \
    g++ \
    cmake \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs uploads event_data

# Set memory-efficient environment variables
ENV PYTHONUNBUFFERED=1 \
    MALLOC_TRIM_THRESHOLD_=100000 \
    MALLOC_MMAP_THRESHOLD_=100000

# Run the bot
CMD ["python", "-u", "main.py"]
