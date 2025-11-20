#!/bin/sh
# entrypoint.sh

# Sai imediatamente se um comando falhar.
set -e

# Se o primeiro argumento for um comando existente (como "sh", "bash", "python"),
# executa esse comando. Isso permite sobrescrever o entrypoint para depuração.
if [ -x "$(command -v "$1")" ]; then
  exec "$@"
else
  # Caso contrário, executa o gunicorn como padrão.
  # O 'exec' substitui o processo do shell, tornando o gunicorn o PID 1.
  exec gunicorn -w "$WORKERS" -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
fi