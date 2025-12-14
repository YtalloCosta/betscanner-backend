FROM mcr.microsoft.com/playwright/python:v1.41.2-jammy

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Instalar browsers Playwright (Railway PERMITE este comando nesta imagem)
RUN playwright install chromium

# Copiar o projeto
COPY . .

# Railway fornece $PORT automaticamente
ENV PORT=8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
