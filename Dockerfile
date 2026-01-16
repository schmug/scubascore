# Use Python 3.11 slim image for smaller footprint
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories for runtime
RUN mkdir -p autoload autoload/processed

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose the application port
EXPOSE 5000

# Set environment variables
ENV FLASK_ENV=production \
    PYTHONUNBUFFERED=1

# Initialize database on container start if it doesn't exist
# Then run gunicorn with 4 workers
CMD python -c "import os; from app import init_db; init_db() if not os.path.exists('scubascore.db') else None" && \
    gunicorn --bind 0.0.0.0:5000 \
             --workers 4 \
             --timeout 120 \
             --access-logfile - \
             --error-logfile - \
             app:app
