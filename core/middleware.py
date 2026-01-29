import time
import uuid
import logging
import traceback
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("taskvault.request")

class LoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log incoming requests and outgoing responses.
    Includes Correlation ID, execution time, and identity tracking.
    """
    SENSITIVE_KEYS = {"password", "token", "otp", "authorization", "cookie", "email", "username", "card_number", "cvv", "expiry_date"}

    def process_request(self, request):
        request.start_time = time.time()
        # 1. Generate/Extract Correlation ID
        request.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # 2. Extract Identity (if already authenticated by previous middleware)
        request.user_id = getattr(request.user, "id", "Anonymous")
        request.tenant_id = getattr(getattr(request.user, "organization", None), "id", "N/A")

    def process_response(self, request, response):
        # 3. Calculate Duration
        duration_ms = int((time.time() - getattr(request, "start_time", time.time())) * 1000)
        
        # 4. Determine Log Level
        status_code = response.status_code
        level = logging.INFO
        if 400 <= status_code < 500:
            level = logging.WARNING
        elif status_code >= 500:
            level = logging.ERROR

        # 5. Mask Sensitive Data in Headers
        headers = dict(request.headers)
        for key in headers:
            if key.lower() in self.SENSITIVE_KEYS:
                headers[key] = "[MASKED]"

        # 6. Log Structured Message
        log_data = {
            "request_id": getattr(request, "request_id", "N/A"),
            "tenant_id": getattr(request, "tenant_id", "N/A"),
            "user_id": getattr(request, "user_id", "Anonymous"),
            "execution_time_ms": duration_ms,
        }

        msg = f"{request.method} {request.path} - {status_code} ({duration_ms}ms)"
        logger.log(level, msg, extra=log_data)

        # 7. Propagate Correlation ID back to client
        response["X-Request-ID"] = getattr(request, "request_id", "N/A")
        
        return response

    def process_exception(self, request, exception):
        """
        Log unhandled exceptions as CRITICAL.
        """
        duration_ms = int((time.time() - getattr(request, "start_time", time.time())) * 1000)
        log_data = {
            "request_id": getattr(request, "request_id", "N/A"),
            "tenant_id": getattr(request, "tenant_id", "N/A"),
            "user_id": getattr(request, "user_id", "Anonymous"),
            "execution_time_ms": duration_ms,
        }
        
        msg = f"CRITICAL Exception on {request.method} {request.path}: {str(exception)}"
        logger.critical(msg, extra=log_data, exc_info=True)
        return None
