FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/ ./common/
COPY services/ ./services/

# Se sobreescribe por cada servicio en docker-compose
CMD ["python", "-m", "services.classifier.main"]
