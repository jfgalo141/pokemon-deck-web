FROM python:3.11-slim

# Evitar prompts interactivos y asegurar logs en tiempo real
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalar LibreOffice (necesario para convertir las plantillas DOCX a PDF) y fuentes tipograficas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    fonts-liberation \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar dependencias e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el codigo del proyecto
COPY . .

# Puerto por defecto (plataformas como Render inyectaran $PORT en runtime)
ENV PORT=8000
EXPOSE 8000

CMD ["python", "app.py"]
