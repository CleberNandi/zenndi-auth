# metrics.py
from prometheus_client import Counter, Histogram

# ============================================================
# LOGIN
# ============================================================

LOGIN_SUCCESS = Counter(
    "zenndi_auth_login_success_total",
    "Logins bem-sucedidos",
    ["client"],  # app, web, parceiroX
)

LOGIN_FAILED = Counter(
    "zenndi_auth_login_failed_total",
    "Logins mal-sucedidos",
    ["reason"],  # invalid_password, user_not_found, blocked, rate_limited
)

# ============================================================
# VERIFICAÇÃO / CÓDIGOS
# ============================================================

CODE_SENT = Counter(
    "zenndi_auth_code_sent_total",
    "Códigos de verificação enviados",
    ["channel"],  # email / sms
)

VERIFY_ATTEMPT = Counter(
    "zenndi_auth_verify_attempt_total",
    "Tentativas de verificação de código",
    ["result"],  # success / failed
)

# ============================================================
# USUÁRIO CRIADO
# ============================================================

USER_CREATED = Counter(
    "zenndi_auth_user_created_total",
    "Usuários criados",
    ["result"],  # success / conflict / failed
)

# ============================================================
# DB METRICS
# ============================================================

DB_QUERY_COUNT = Counter(
    "zenndi_db_query_total",
    "Quantidade de queries executadas",
    ["operation"],  # select_user, insert_user etc
)

DB_QUERY_TIME = Histogram(
    "zenndi_db_query_duration_seconds",
    "Duração das queries no banco",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1],
)

# ============================================================
# HTTP REQUEST METRICS
# ============================================================

HTTP_REQUEST_TIME = Histogram(
    "zenndi_http_request_duration_seconds",
    "Tempo de execução das requisições HTTP",
    ["method", "route", "status"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2],
)

HTTP_REQUEST_COUNT = Counter(
    "zenndi_http_request_total",
    "Total de requisições HTTP",
    ["method", "route", "status"],
)

# ============================================================
# CORS METRICS
# ============================================================

CORS_ALLOWED = Counter(
    "zenndi_cors_allowed_total",
    "Requisições que passaram no CORS",
    ["origin"],
)

CORS_BLOCKED = Counter(
    "zenndi_cors_blocked_total",
    "Requisições bloqueadas por CORS",
    ["origin"],
)
