FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --shell /usr/sbin/nologin app
COPY . .
RUN chmod +x /app/entrypoint.sh && chown -R app:app /app
USER app

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
