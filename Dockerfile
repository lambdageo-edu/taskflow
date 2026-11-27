FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# O banco fica em um volume, fora do contêiner.
RUN useradd --create-home appuser && mkdir /dados && chown appuser /dados
ENV TAREFAS_DB=/dados/tarefas.db
VOLUME /dados
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
