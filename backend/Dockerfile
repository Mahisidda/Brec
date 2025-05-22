# backend/Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system deps (if any) and Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code & data
COPY app ./app
COPY data ./data

EXPOSE 8000

# Use gunicorn for production
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app.main:app"]
