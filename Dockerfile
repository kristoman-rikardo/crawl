# Bruk Playwright sitt offisielle Python-image
FROM mcr.microsoft.com/playwright/python:latest

WORKDIR /app

# Kopier inn requirements og installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer Chrome/Chromium explicitly
RUN playwright install chromium

# Kopier resten av koden
COPY . .

# Kjør uvicorn når containeren starter
CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=10000"]
