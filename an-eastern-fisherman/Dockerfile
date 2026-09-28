FROM python:3.12-slim

WORKDIR /home

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  HOST="0.0.0.0" \
  PORT="80"

# Install build dependencies for any packages that require compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
  libcurl4-openssl-dev \
  gcc \
  && rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY config/requirements.txt /tmp/requirements.txt

# Install Python dependencies first for better layer caching
RUN python --version \
  && pip --version \
  && pip install --no-cache-dir -r /tmp/requirements.txt \
  && rm -f /tmp/requirements.txt

# Copy challenge files
COPY challenge/ /home/
COPY assets.7z /home/assets.7z

# Expose the application port
EXPOSE 80

# Use supervisord to run the application
CMD ["python", "server.py"]