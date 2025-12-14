FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# Diretório da aplicação
WORKDIR /app

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala browsers Playwright
RUN playwright install --with-deps chromium

# Copia o restante do projeto
COPY . .

# Comando de execução
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
