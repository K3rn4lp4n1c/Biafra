FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  HOST="0.0.0.0" \
  PORT=80

WORKDIR /home

# System packages needed by the app
RUN apt-get update && apt-get install -y --no-install-recommends \
  libimage-exiftool-perl \
  curl \
  gosu \
  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching
COPY config/requirements.txt /tmp/requirements.txt
COPY --chmod=755 entrypoint.sh /entrypoint.sh
RUN python --version \
  && pip --version \
  && pip install --no-cache-dir -r /tmp/requirements.txt \
  && rm -f /tmp/requirements.txt

# Copy challenge files
COPY challenge/ /home/
RUN echo "CTF{REDACTED}" > /home/flag 

# Lock down application
RUN chown -R root:root /home \
  && find /home -type d -exec chmod 755 {} \; \
  && find /home -type f -exec chmod 444 {} \; \
  && chmod 755 /home \
  && chmod 777 /home/flag

# Expose the application port
EXPOSE 80

# Non-root runtime user
RUN useradd --create-home --shell /usr/sbin/nologin ctf

HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD curl -fsS http://127.0.0.1/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]

CMD ["python", "app.py"]