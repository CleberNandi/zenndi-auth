Guia Rápido: Testando Workflows do GitHub Actions Localmente com act
Este guia explica como instalar e usar a ferramenta act para executar e depurar seus workflows do GitHub Actions no seu próprio computador, sem a necessidade de fazer push para o repositório a cada alteração.

O que é o act?
act é uma ferramenta de linha de comando que lê seus arquivos de workflow do GitHub (.github/workflows/\*.yml) e executa os jobs localmente usando Docker. Isso permite que você teste suas automações de CI/CD de forma rápida e eficiente.

1. Instalação
   A forma mais fácil de instalar o act depende do seu sistema operacional.

Link Oficial para Instalação (todas as plataformas): https://github.com/nektos/act#installation
Abaixo estão os comandos mais comuns:

macOS
Use o Homebrew:

```bash
brew install act
```

Linux
Use o script de instalação oficial:

```sh
# 1. Baixa e executa o script de instalação. Ele instalará o 'act' em uma pasta ./bin
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# 2. Move o executável para um diretório global para que o comando funcione em qualquer lugar
sudo mv ./bin/act /usr/local/bin/
rmdir ./bin
```

Windows
Use o Chocolatey ou Scoop:

```bash
choco install act
scoop install act
```

2. Como Usar o act no Projeto zenndi-auth
   Após a instalação, navegue até a raiz do seu projeto (/home/nandi/Workspace/Projetos/zenndi/zenndi_auth) e execute os comandos abaixo.

a. Listando os Jobs Disponíveis
Para ver quais jobs o act reconhece no seu workflow, use o comando -l (list).

```bash
act -l
```

A saída será parecida com esta, mostrando os jobs do seu arquivo ci.yml:

```bash
ID             Job Name         Workflow Name                      Workflow File  Events
test           test             CI/CD - Build, Test, and Deploy    ci.yml         push, pull_request, workflow_dispatch
create-pr      create-pr        CI/CD - Build, Test, and Deploy    ci.yml         push, pull_request, workflow_dispatch
build-and-push build-and-push   CI/CD - Build, Test, and Deploy    ci.yml         push, pull_request, workflow_dispatch
```

b. Executando um Job Específico
É mais eficiente rodar apenas o job que você quer testar. Use a flag -j <job_id>.

Exemplo: Rodando apenas o job de testes (test)

```bash
act -j test
```

O act irá:

Baixar uma imagem Docker para simular o ambiente do GitHub Actions.
Executar cada um dos steps definidos no job test.
Mostrar toda a saída de logs diretamente no seu terminal.
c. Simulando Eventos do GitHub
Você pode simular diferentes gatilhos (on:) para testar a lógica condicional (if: ...) do seu workflow.

Exemplo 1: Testando a criação de PR para uma `feature`
Simule um push para um branch de feature definindo a variável de ambiente `GITHUB_REF`. Isso executará os jobs `test` e, se bem-sucedido, o `create-pr`.

```bash
GITHUB_REF=refs/heads/feature/minha-nova-funcionalidade act push
```

Exemplo 2: Testando o deploy para main Simule um push para o branch main. Isso executará os jobs test e, se bem-sucedido, o build-and-push.

```bash
GITHUB_REF=refs/heads/main act push

```

Exemplo 3: Testando um Pull Request Simule um evento de pull request para o branch dev.

```bash
GITHUB_REF=refs/heads/dev act push
```

3. Lidando com Secrets
   Seu workflow depende de secrets (como tokens de acesso). O act irá solicitá-los interativamente na primeira vez que você rodar um comando.

Para evitar digitar as secrets toda vez, você pode criar um arquivo chamado .secrets na raiz do seu projeto.

CUIDADO: Adicione o arquivo .secrets ao seu .gitignore para NUNCA comitá-lo!

1. Crie o arquivo .secrets:

```bash
touch .secrets
```

2. Adicione suas secrets ao arquivo, uma por linha:

```bash
# .secrets
# Adicione este arquivo ao .gitignore!

# Secrets para o Docker Hub
DOCKERHUB_USERNAME=seu_usuario_docker
DOCKERHUB_TOKEN=seu_token_do_docker_hub

# Personal Access Token do GitHub para criar PRs
# https://github.com/settings/tokens
PAT=ghp_SeuTokenDoGitHubAqui

# Secrets do banco de dados (opcional, pois o CI usa valores padrão)
POSTGRES_USER=testuser
POSTGRES_PASSWORD=testpass
POSTGRES_DB=testdb
```

Agora, quando você rodar o act, ele lerá as secrets deste arquivo automaticamente
