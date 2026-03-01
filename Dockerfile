FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# copy runtime requirements first for better caching
COPY requirements.prod.txt /app/requirements.prod.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/requirements.prod.txt

# copy frontend separately so it lives at /app/frontend in the image
COPY frontend /app/frontend
# copy the rest of the project
COPY . /app

# expose port used by Flask / Gunicorn
EXPOSE 8181

# Use Gunicorn for production; bind to Render's $PORT if set
CMD ["sh", "-c", "gunicorn api.server:app --bind 0.0.0.0:${PORT:-8181} --workers ${WEB_CONCURRENCY:-1}"]
