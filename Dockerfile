FROM python:3.11-slim

# Evitar archivos .pyc y habilitar salida de logs sin buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar curl para el healthcheck y limpiar caché de apt
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python aprovechando la caché de capas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar únicamente el código fuente
COPY src/ ./src/

# Puerto estándar de Streamlit
EXPOSE 8501

# Verificación de salud del contenedor
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Comando de inicio
ENTRYPOINT ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]