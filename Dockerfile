FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY app ./app
COPY frontend ./frontend

# Não rodar como root dentro do container.
RUN useradd --create-home --uid 1000 validade && mkdir -p /app/dados && chown -R validade /app/dados
USER validade

EXPOSE 8000
CMD ["uvicorn", "app.main:criar_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
