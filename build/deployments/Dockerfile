# ==============================================================================
# Estágio 1: Builder - Instala as dependências
# ==============================================================================

# Use uma ARG para tornar a imagem base configurável a partir do Makefile
ARG DOCKER_BASE_IMAGE=clebernandi/zenndi-auth-base:latest
FROM ${DOCKER_BASE_IMAGE} AS builder

WORKDIR /app

# Copia os arquivos de definição de dependências
COPY pyproject.toml ./

# Sincroniza as dependências de produção em um venv.
# 'uv sync' garante um ambiente limpo e exato, instalando apenas o que está
# definido no pyproject.toml, e é mais rápido que resolver e instalar em passos separados.
RUN /root/.cargo/bin/uv venv /opt/venv && /root/.cargo/bin/uv sync --no-cache --python /opt/venv/bin/python --no-dev pyproject.toml

# ==============================================================================
# Estágio 2: Final - Cria a imagem de produção enxuta
# ==============================================================================

FROM ${DOCKER_BASE_IMAGE} AS final

WORKDIR /app

# Cria um usuário não-root para rodar a aplicação
RUN useradd --create-home --shell /bin/bash appuser

# Copia o venv com as dependências do estágio builder
COPY --from=builder /opt/venv /opt/venv

# Copia o código da aplicação
COPY ./app ./app

# Ajusta as permissões para o usuário não-root
RUN chown -R appuser:appuser /app /opt/venv
USER appuser

# Define o número de workers, com um padrão de 4.
# Pode ser sobrescrito em tempo de execução com a variável de ambiente WORKERS.
ENV WORKERS=${WORKERS:-4}

# Define o comando para iniciar a aplicação com Gunicorn
# Usamos a forma "shell" do CMD para que a variável $WORKERS seja substituída.
CMD /opt/venv/bin/gunicorn -w "$WORKERS" -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000