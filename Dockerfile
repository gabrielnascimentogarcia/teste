# Usa uma imagem Python slim oficial
FROM python:3.9-slim

# Define variáveis de ambiente para evitar arquivos .pyc e buffering de log
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências de sistema necessárias para o Tkinter (GUI)
# x11-apps e python3-tk são cruciais aqui.
RUN apt-get update && apt-get install -y \
    python3-tk \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos do projeto para o container
COPY mic1_hardware.py .
COPY assembler.py .
COPY gui_app.py .
COPY main.py .

# Cria um usuário não-root para segurança (opcional, mas recomendado)
RUN useradd -m appuser
USER appuser

# Comando padrão para rodar a aplicação
# Nota: Para ver a GUI, você deve rodar o docker passando o display do host.
# Exemplo Linux: docker run -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix mic1-sim
CMD ["python", "main.py"]