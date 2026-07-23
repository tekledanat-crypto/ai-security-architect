"""Security middleware: secure headers + lightweight rate limiting.

Rate limiting here is a simple in-memory token bucket per client — adequate for a
single-instance dev/demo deployment. In Azure, Front Door / APIM provide the
authoritative edge rate limiting (see frameworks: OWASP API4, LLM10). Secure
headers align with OWASP Web A05 (security misconfiguration).
"""
from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 120):
        super().__init__(app)
        self.capacity = requests_per_minute
        self.window = 60.0
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        client = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window
        hits = [t for t in self._hits[client] if t > window_start]
        if len(hits) >= self.capacity:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again shortly."},
                headers={"Retry-After": "10"},
            )
        hits.append(now)
        self._hits[client] = hits
        return await call_next(request)
