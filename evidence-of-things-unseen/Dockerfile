FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  HOST="0.0.0.0" \
  PORT=80

WORKDIR /home

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  libgl1 \
  libglib2.0-0 \
  libsm6 \
  libxext6 \
  libxrender1 \
  libxcb1

# Install Python dependencies first for better layer caching
COPY config/requirements.txt /tmp/requirements.txt
RUN python --version \
  && pip --version \
  && pip install --no-cache-dir -r /tmp/requirements.txt \
  && rm -f /tmp/requirements.txt

# Copy challenge files
COPY challenge/ /home/
COPY assets.7z /home/assets/assets.7z

# Expose the application port
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fsS http://127.0.0.1/health || exit 1

CMD ["python", "server.py"]