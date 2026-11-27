FROM python:3.14-slim

WORKDIR /app

# Correções de segurança do sistema que a imagem base ainda não traz.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# O pip só serve para instalar: removê-lo tira da imagem as bibliotecas que ele embute.
RUN pip install --no-cache-dir -r requirements.txt && pip uninstall -y pip

COPY app/ ./app/

# O banco fica em um volume, fora do contêiner.
RUN useradd --create-home appuser && mkdir /dados && chown appuser /dados
ENV TAREFAS_DB=/dados/tarefas.db
VOLUME /dados
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
