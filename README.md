# Zenndi Auth API

[![CI/CD](https://github.com/CleberNandi/zenndi-auth/actions/workflows/ci.yml/badge.svg)](https://github.com/CleberNandi/zenndi-auth/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker Image](https://img.shields.io/docker/pulls/clebernandi/zenndi-auth.svg)](https://hub.docker.com/r/clebernandi/zenndi-auth)

API de autenticação e gerenciamento de usuários para a plataforma Zenndi. Construída com FastAPI, PostgreSQL e Redis, seguindo as melhores práticas de desenvolvimento, segurança e CI/CD..

## ✨ Features

- **Autenticação JWT:** Sistema seguro de login com tokens de acesso e atualização.
- **Gerenciamento de Usuários:** CRUD completo para usuários.
- **Fluxo de Autenticação Moderno:** Opção de validação de e-mail antes da criação de senha (estilo Notion/Spotify).
- **Rate Limiting:** Proteção contra ataques de força bruta.
- **Observabilidade:** Integração com Sentry para monitoramento de erros e Prometheus/Grafana para métricas.
- **CI/CD Automatizado:** Build, testes e deploy automatizados com GitHub Actions.
- **Qualidade de Código:** Garantida por `Ruff`, `Pyright` e `Pytest`.

## 🛠️ Tech Stack

- **Backend:** FastAPI, Uvicorn, Pydantic
- **Banco de Dados:** PostgreSQL (com Alembic para migrations)
- **Cache/Rate Limiter:** Redis
- **Containerização:** Docker & Docker Compose
- **CI/CD:** GitHub Actions
- **Qualidade de Código:** Ruff (Linting & Formatting), Pyright (Type Checking)
- **Testes:** Pytest
- **Observabilidade:** Sentry, Prometheus, Grafana

## 📂 Estrutura de Pastas

```
zenndi_auth/
├── .github/
│   └── workflows/
│       └── ci.yml           # Workflow de Integração e Deploy Contínuo
├── alembic/                 # Configuração e versões de migrations do Alembic
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/   # Módulos de endpoints da API (ex: auth, users)
│   ├── core/                # Configurações centrais, lifespan, middlewares
│   ├── models/              # Modelos SQLAlchemy
│   ├── schemas/             # Esquemas Pydantic para validação de dados
│   └── services/            # Lógica de negócio
├── build/
│   └── deployments/         # Dockerfiles para diferentes ambientes
├── keys/                    # Chaves RSA para JWT (ignoradas pelo git)
├── monitoring/              # Configurações do Prometheus
├── tests/                   # Testes automatizados
├── .env.example             # Arquivo de exemplo para variáveis de ambiente
├── .gitignore
├── docker-compose.ci.yml    # Docker Compose para o ambiente de CI
├── docker-compose.yml       # Docker Compose para desenvolvimento local
├── Dockerfile               # Dockerfile para a imagem de produção
├── manage.py                # CLI interativa para gerenciamento do projeto
├── Makefile                 # Comandos de automação
└── README.md                # Esta documentação
```

## 🚀 Começando

Para rodar o projeto localmente, você precisará do Docker e Docker Compose instalados.

1.  **Clone o repositório:**

    ```bash
    git clone https://github.com/CleberNandi/zenndi-auth.git
    cd zenndi_auth
    ```

2.  **Configure as variáveis de ambiente:**
    Copie o arquivo de exemplo e preencha com suas configurações.

    ```bash
    cp .env.example .env
    ```

3.  **Gere as chaves RSA (para JWT):**

    ```bash
    mkdir -p keys
    openssl genrsa -out keys/private.pem 2048
    openssl rsa -in keys/private.pem -pubout -out keys/public.pem
    chmod 600 keys/private.pem
    ```

4.  **Use o Gerenciador de Projeto Interativo:**
    O script `manage.py` simplifica todas as operações comuns. Para subir o ambiente de desenvolvimento completo:

    ```bash
    python manage.py
    ```

    No menu, selecione a opção: `🚀 Subir ambiente de DEBUG (API + DB + Redis + Monitoramento)`.

    Isso irá construir as imagens, instalar as dependências e iniciar todos os serviços.

5.  **Aplique as migrations do banco de dados:**
    Ainda no menu do `manage.py`, selecione: `🚀 Aplicar migrations (Alembic)`.

6.  **Acesse a API:**
    A API estará disponível em `http://localhost:8000`. A documentação interativa (Swagger UI) pode ser acessada em `http://localhost:8000/docs`.

## 🧪 Rodando Testes

Você pode rodar todos os testes usando o gerenciador de projeto:

```bash
python manage.py
```

Selecione a opção: `🧪 Rodar todos os testes (pytest)`.

Para um relatório de cobertura: `📊 Rodar testes com relatório de cobertura`.

## 🚢 CI/CD

O pipeline de CI/CD é acionado em cada `push` ou `pull_request` para os branches `feature/**`, `dev`, `hml` e `main`.

- **Branches `feature/**`:** Roda os testes e, se passarem, cria um Pull Request automaticamente para o branch `dev`.
- **Branches `dev`, `hml`:** Roda os testes e, em caso de push direto, faz o build e push da imagem Docker `clebernandi/zenndi-auth:<branch-name>`.
- **Branch `main`:** Roda os testes e, em caso de push direto, faz o build e push das imagens Docker `clebernandi/zenndi-auth:latest` e `clebernandi/zenndi-auth:<run-number>`.

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.
