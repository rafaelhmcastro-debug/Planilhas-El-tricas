FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cabos-app/ ./cabos-app/

EXPOSE 8000

CMD ["sh", "-c", "cd cabos-app && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
