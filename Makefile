# ========================
# Variáveis gerais
# ========================
# Nome do projeto
PROJECT_NAME=zenndi_auth

# Docker  images base
DOCKER_FILE_BASE=./build/deployments/Dockerfile.base
DOCKER_FILE_BASE_DEV=./build/deployments/Dockerfile.dev
DOCKER_IMAGE_BASE=clebernandi/zenndi-auth-base
DOCKER_IMAGE_DEV=clebernandi/zenndi-auth-dev

# Docker image app
DOCKER_FILE_APP=./build/deployments/Dockerfile
DOCKER_IMAGE_APP=clebernandi/zenndi-auth-app

# Pegar hash id do commit
GIT_HASH=$(shell git rev-parse --short HEAD)

# ========================
# Variáveis do banco
# ========================
DB_NAME ?= carteirazen_db
DB_USER ?= postgres
DB_PASS ?= postgres
DB_HOST ?= localhost
DB_PORT ?= 5432

# ========================
# Docker Criando imagens
# ========================
.PHONY: docker-create-image-base docker-create-image-base-dev docker-create-image-app docker-create-image-full docker-create-image-app-dev
docker-create-image-base: 
	@echo "🏗️  [01] - Construindo imagem base como '$(DOCKER_IMAGE_BASE)'..."
	docker build --no-cache -f $(DOCKER_FILE_BASE) -t $(DOCKER_IMAGE_BASE):latest .
	@echo "🚀 [02] - Enviando '$(DOCKER_IMAGE_BASE)' para o registro..."
	docker push $(DOCKER_IMAGE_BASE)

docker-create-image-dev: 
	@echo "🏗️  [01] - Construindo imagem base como '$(DOCKER_IMAGE_DEV)'..."
	docker build --no-cache -f $(DOCKER_FILE_BASE_DEV) -t $(DOCKER_IMAGE_DEV):latest .
	@echo "🚀 [02] - Enviando '$(DOCKER_IMAGE_DEV)' para o registro..."
	docker push $(DOCKER_IMAGE_DEV)

docker-create-image-app:
	@echo "🔒  [01 de 04] - Gerando requirements.lock a partir do pyproject.toml..."
	uv pip compile pyproject.toml --extra dev -o requirements.lock
	@echo "🏗️  [02 de 04] - Construindo imagem do app como '$(DOCKER_IMAGE_APP)'..."
	docker build --no-cache -f $(DOCKER_FILE_APP) --build-arg DOCKER_IMAGE_BASE=$(DOCKER_IMAGE_BASE) -t $(DOCKER_IMAGE_APP):$(GIT_HASH) -t $(DOCKER_IMAGE_APP):latest .
	@echo "🚀 [03 de 04] - Envqiando tag $(GIT_HASH) para o registro..."
	docker push $(DOCKER_IMAGE_APP):$(GIT_HASH)
	@echo "🚀 [04 de 04] - Enviando tag latest para o registro..."
	docker push $(DOCKER_IMAGE_APP):latest

# ========================
# Docker Subindo containers
# ========================
.PHONY: docker-up-prod docker-up-build
docker-up-prod:
	@echo "🚀 Subindo ambiente PROD"
	ENV_MODE=prod docker compose -f docker-compose.prod.yml up --build

docker-up-build:
	docker compose -f docker-compose.yml up --build

# ========================
# Limpeza
# ========================
.PHONY: clean docker-clean docker-clean-all docker-images-clean

clean:
	find . -type d -name "__pycache__" -exec rm -r {} + || true
	find . -type f -name "*.pyc" -delete || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache

docker-clean:	
	docker system prune -af

docker-images-clean:	
	docker image prune -f

docker-clean-all:
	docker compose down -v --rmi all --remove-orphans
	docker system prune -af

# ========================
# Ajuda
# ========================
.PHONY: help

help:
	@echo "📝 Comandos disponíveis:"
	@echo "🚢  make docker-create-image-base		Gera e faz envio da imagem docker base"
	@echo "🚢  make docker-create-image-app     	Gera e faz envio da imagem do app"
	@echo "🚢  make docker-create-image-app-dev   Gera e faz envio da imagem do app"
	@echo "🚢  make docker-create-image-full		Gera e faz envio das imagens base e app sequenciais"
	@echo "🚀  make docker-up-prod         			Subindo container de produção"
	@echo "🚀  make docker-up-build        			Buildando container"
	@echo "🧹  make clean         					Limpando cache python"
	@echo "🧹  make docker-clean         			Limpando imagens orfans"
	@echo "🧹  make docker-images-clean       		Limpando imagens somente orfans "
	@echo "🧹  make docker-clean-all         		Parando containers e eliminando todas as imagens "