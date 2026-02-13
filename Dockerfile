FROM python:3.11-slim

WORKDIR /app

# Install ONLY necessary OpenCV dependencies - Fix for Debian Trixie
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD gunicorn camera_demo_backend.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 120
