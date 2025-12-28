# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        tesseract-ocr \
        libtesseract-dev \
        libleptonica-dev \
        pkg-config \
        curl \
        gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies globally
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify gunicorn is installed
RUN which gunicorn || (echo "gunicorn not found" && exit 1)

# Copy project
COPY . .

# Create logs directory
RUN mkdir -p logs

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port (Railway will set PORT environment variable)
EXPOSE $PORT

# Run the application
CMD ["gunicorn", "--config", "gunicorn.conf.py", "run:app"]
