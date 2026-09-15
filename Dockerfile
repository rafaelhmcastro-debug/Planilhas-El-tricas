FROM python:3.11-slim

WORKDIR /app

# Copiar requirements e instalar dependências
COPY cabos-app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY cabos-app/ ./

# Expor porta
EXPOSE 8000

# Comando para iniciar
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
