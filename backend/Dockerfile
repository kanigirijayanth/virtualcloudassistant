# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app
COPY app/requirements.txt .

# Upgrade pip and setuptools, install requirements
RUN pip install --no-cache-dir pip==25.1.1 setuptools==78.1.1 && \
    pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.12-slim

# Create non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Upgrade pip and setuptools, then copy Python packages from builder
RUN pip install --no-cache-dir pip==25.1.1 setuptools==78.1.1
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ .

# Install curl and ffmpeg
RUN apt-get update && apt-get install -y curl ffmpeg && rm -rf /var/lib/apt/lists/*

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

# Update command to run main.py directly
CMD ["python", "main.py"]
