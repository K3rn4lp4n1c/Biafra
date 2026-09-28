FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  HOST="0.0.0.0" \
  PORT="1337"

WORKDIR /home

# System packages needed by the app
RUN apt-get update && apt-get install -y --no-install-recommends \
  supervisor \
  ncat \
  && rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY config/supervisord.conf /etc/supervisord.conf
COPY config/requirements.txt /tmp/requirements.txt
COPY assets.7z /home/assets/assets.7z

# Install Python dependencies first for better layer caching
RUN python --version \
  && pip --version \
  && pip install --no-cache-dir -r /tmp/requirements.txt \
  && rm -f /tmp/requirements.txt

# Copy challenge files
COPY challenge/ /home/

# Expose the application port
EXPOSE 9999

# Use supervisord to run the application
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]