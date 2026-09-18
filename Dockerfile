FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml requirements-api.txt ./
COPY src ./src
COPY run_api.py ./
RUN pip install --no-cache-dir -r requirements-api.txt && pip install --no-cache-dir -e .
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["uvicorn","kynka.presentation.api.app:app","--host","0.0.0.0","--port","8000"]
