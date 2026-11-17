FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Collect static files and set up permissions
RUN python manage.py collectstatic --noinput

EXPOSE 7860

CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_demo_data && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT}"]
