FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências do sistema para Tkinter e encaminhamento X11
RUN apt-get update && apt-get install -y \
    python3-tk \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY mic1_hardware.py .
COPY assembler.py .
COPY gui_app.py .
COPY main.py .

# Cria um usuário não-root para segurança
RUN useradd -m appuser
USER appuser

# Comando padrão para rodar o simulador
# Requer encaminhamento X11 configurado no host
CMD ["python", "main.py"]