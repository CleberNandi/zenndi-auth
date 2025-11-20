# ==============================================================================
# Estágio 1: Builder - Instala as dependências de forma otimizada
# ==============================================================================
# A ARG permite que a imagem base seja configurada pelo Makefile, mas definimos um padrão seguro.
ARG DOCKER_BASE_IMAGE=clebernandi/zenndi-auth-base:latest
FROM ${DOCKER_BASE_IMAGE} AS builder

# Define o diretório de trabalho
WORKDIR /app

# Apenas os arquivos de dependências para aproveitar cache
# O build só re-executará este passo se um desses arquivos mudar.
COPY pyproject.toml settings.toml README.md requirements.lock ./

# Instala as dependências em um diretório separado que será copiado para o estágio final.
# Usamos 'uv' para instalar a partir do arquivo de lock, garantindo builds rápidos e reprodutíveis.
# --system: Instala no ambiente Python global do container (sem venv).
# --no-cache: Não armazena o cache do uv, mantendo a camada (layer) menor.
RUN uv pip install --system --no-cache -r requirements.lock

# ==============================================================================
# Estágio 2: Final - Cria a imagem de produção enxuta e segura
# ==============================================================================
FROM ${DOCKER_BASE_IMAGE} AS final

# Define o diretório de trabalho
WORKDIR /app

# Cria um usuário e grupo não-root chamado 'appuser'
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser -d /app appuser

# Copia as dependências pré-instaladas do estágio 'builder'.
# Isso é muito mais rápido do que instalar tudo de novo.
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Copia os executáveis (como gunicorn, uvicorn) instalados pelas dependências.
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia o código da aplicação
COPY . .

# Garante que o entrypoint seja executável
RUN chmod +x /app/entrypoint.sh

# Muda a propriedade dos arquivos para o nosso usuário não-root
RUN chown -R appuser:appuser /app

# Muda para o usuário não-root
USER appuser

# Expõe a porta que a aplicação irá rodar
EXPOSE 8000

# Define o número de workers, com um padrão de 4.
# Pode ser sobrescrito em tempo de execução com a variável de ambiente WORKERS.
ENV WORKERS=4

# Define o entrypoint que será executado quando o container iniciar.
# Usamos o formato "exec" para que o entrypoint.sh seja o PID 1.
ENTRYPOINT ["/app/entrypoint.sh"]