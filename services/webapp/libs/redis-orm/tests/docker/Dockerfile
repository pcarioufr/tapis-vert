FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies (no need to copy code since it's mounted at runtime)
RUN pip install --no-cache-dir redis pytest pytest-cov nanoid

# Install ddtrace for tracing support (optional dependency)
RUN pip install --no-cache-dir ddtrace || echo "ddtrace not available, continuing without tracing"

# Set Python path to include current directory so 'core' module can be imported
ENV PYTHONPATH=/app

# Disable Python cache file generation (.pyc files and __pycache__ directories)
ENV PYTHONDONTWRITEBYTECODE=1

# Default command
CMD ["pytest", "-v", "tests_py/"] 