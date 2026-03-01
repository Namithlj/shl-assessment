FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# copy requirements first for better caching
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch || true && \
    pip install --no-cache-dir -r /app/requirements.txt

# copy frontend separately so it lives at /app/frontend in the image
COPY frontend /app/frontend
# copy the rest of the project
COPY . /app

# expose port used by Flask / Gunicorn
EXPOSE 8181

# Use Gunicorn for production; bind to numeric port 8181 (matches render.yaml)
CMD ["gunicorn", "api.server:app", "--bind", "0.0.0.0:8181", "--workers", "2"]
