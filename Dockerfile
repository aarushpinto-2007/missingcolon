FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /tmp/shieldstream/uploads \
             /tmp/shieldstream/vault \
             /tmp/shieldstream/secure_keys \
             /tmp/shieldstream/final_stream

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "120", "--workers", "2", "api.app:app"]
