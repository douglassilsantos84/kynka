FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system kynka \
    && useradd --system --gid kynka --create-home kynka

COPY pyproject.toml requirements-api.txt ./
COPY src ./src
COPY run_api.py ./

RUN pip install --no-cache-dir -r requirements-api.txt \
    && pip install --no-cache-dir -e . \
    && mkdir -p /app/data \
    && chown -R kynka:kynka /app

USER kynka

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/platform/health', timeout=3).read()"

CMD ["uvicorn","kynka.presentation.api.app:app","--host","0.0.0.0","--port","8000","--proxy-headers"]
