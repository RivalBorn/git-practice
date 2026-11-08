FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/recipes.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py init_db.py ./

RUN useradd --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /data \
    && chown -R app:app /app /data

USER app

EXPOSE 8000

CMD ["sh", "-c", "python init_db.py && exec gunicorn --bind 0.0.0.0:8000 app:app"]
