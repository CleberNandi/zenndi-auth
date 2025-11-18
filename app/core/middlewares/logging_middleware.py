import time

from fastapi import Request
import sentry_sdk
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.network_utils import get_client_ip

from app.core.request_id import (
    REQUEST_ID_HEADER,
    generate_request_id,
    get_request_id_from_header,
)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # --- Request ID ---
        request_id = get_request_id_from_header(request) or generate_request_id()
        log = logger.bind(request_id=request_id)
        sentry_sdk.set_tag("request_id", request_id)

        # --- IP ---
        client_ip = get_client_ip(request)

        # --- Request Log ---
        log.info(f"REQUEST {request.method} {request.url.path}")

        try:
            response = await call_next(request)
        except Exception:
            process_time = time.time() - start_time
            log.exception(
                f"Error processing {request.method} {request.url.path} - {process_time:.3f}s"
                f" IP: {client_ip}"
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"},
                headers={REQUEST_ID_HEADER: request_id},
            )
        else:
            # --- Security Headers ---
            security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            }
            response.headers.update(security_headers)

            process_time = time.time() - start_time

            # --- Response Log ---
            log.info(
                f"RESPONSE {request.method} {request.url.path} "
                f"status={response.status_code} duration={process_time:.4f}s "
                f"IP: {client_ip}"
            )

            # --- Request ID sempre ---
            response.headers[REQUEST_ID_HEADER] = request_id

            return response
