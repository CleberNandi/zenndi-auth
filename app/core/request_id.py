import uuid
from typing import Optional
from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-ID"


def generate_request_id() -> str:
    return str(uuid.uuid4())


def get_request_id_from_header(request: Request) -> Optional[str]:
    request_id = request.headers.get(REQUEST_ID_HEADER)
    return request_id.strip() if request_id else None
