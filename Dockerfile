FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
# Combined update, install, and cleanup to reduce layer size
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-Only PyTorch first (Saves ~3GB)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Remove heavy files if they exist locally but shouldn't be in main image (just in case .dockerignore missed them)
RUN rm -rf .git proctor.zip proctor\ \(2\).zip

# Collect static files
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD gunicorn camera_demo_backend.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 120
