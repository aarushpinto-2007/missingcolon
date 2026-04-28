FROM python:3.11-slim

# Install FFmpeg (needed for video processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project
COPY . .

# Create required directories
RUN mkdir -p /tmp/shieldstream/uploads \
             /tmp/shieldstream/vault \
             /tmp/shieldstream/secure_keys \
             /tmp/shieldstream/final_stream

# Azure uses dynamic port → MUST use $PORT
ENV PORT=8000

# Expose port (not strictly required but good practice)
EXPOSE 8000

# Start app using dynamic port (IMPORTANT)
CMD ["sh", "-c", "gunicorn --bind=0.0.0.0:$PORT --timeout=120 --workers=2 api.app:app"]
