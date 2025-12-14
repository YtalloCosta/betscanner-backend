FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# Define diretório da aplicação
WORKDIR /app

# Copia requirements e instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Garante instalação dos browsers Playwright (mesmo já existindo na imagem)
RUN playwright install chromium
RUN playwright install-deps

# Copia o restante dos arquivos
COPY . .

# Necessário para Playwright rodar no Railway
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Inicia API
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
