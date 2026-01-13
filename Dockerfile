FROM python:3.11-slim

# Install Tesseract + lingua italiana
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ita \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["bash", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
