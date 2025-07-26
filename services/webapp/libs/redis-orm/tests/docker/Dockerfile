FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy package files for dependency installation  
COPY ../pyproject.toml ./
COPY ../core/ ./core/

# Install the package in development mode with all dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Install additional test dependencies
RUN pip install --no-cache-dir redis

# Copy test files  
COPY tests/tests_py/ ./tests_py/
COPY tests/models.py ./models.py

# Default command
CMD ["pytest", "-v", "tests/"] 