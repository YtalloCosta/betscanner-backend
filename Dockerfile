FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use PORT env set by Railway
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
