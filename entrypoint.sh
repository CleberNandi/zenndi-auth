#!/bin/sh
# entrypoint.sh

# Sai imediatamente se um comando falhar.
set -e

# O comando 'exec' substitui o processo do shell pelo processo do gunicorn.
# Isso faz com que o gunicorn se torne o PID 1, permitindo que ele lide com sinais do SO corretamente.
# O shell expande a variável $WORKERS antes que o 'exec' seja chamado.
exec /opt/venv/bin/gunicorn -w "$WORKERS" -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000