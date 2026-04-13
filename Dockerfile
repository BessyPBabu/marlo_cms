FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt && \
    python -c "import django; print('Django OK:', django.__version__)"

COPY . .

RUN python -c "import django; print('Django still OK:', django.__version__)" && \
    python manage.py collectstatic --no-input

EXPOSE 8000