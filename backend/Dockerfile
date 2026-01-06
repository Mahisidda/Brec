# backend/Dockerfile
FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

# Install system dependencies needed for scientific Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy code & data
COPY app ./app
COPY data ./data

# Verify files after they are copied
RUN echo "=== Listing /app/data ===" && ls -l /app/data

EXPOSE 8000

# Use gunicorn for production
# app.main:app tells Gunicorn to look in the app folder, find main.py, and use the app variable
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:8000", "app.main:app", "--timeout", "150", "--preload", "--log-level", "info"]
