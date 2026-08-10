# syntax=docker/dockerfile:1
FROM node:22-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS python-builder
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin quizbot
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENV=production
COPY --from=python-builder /opt/venv /opt/venv
COPY --chown=quizbot:quizbot . .
COPY --from=frontend-builder --chown=quizbot:quizbot /frontend/dist ./frontend/dist
RUN mkdir -p logs generated_cards assets && chown -R quizbot:quizbot /app
USER quizbot
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200"
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
