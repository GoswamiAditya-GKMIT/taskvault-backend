from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connections
from django.core.cache import cache
from celery import current_app
import logging

logger = logging.getLogger(__name__)

class HealthCheckAPIView(APIView):
    """
    Comprehensive health check API verifying:
    - Django Server
    - Database (PostgreSQL)
    - Cache (Redis)
    - Celery Workers
    """
    permission_classes = []  # Publicly accessible for monitoring tools

    def get(self, request):
        # 0. Check for Fast Mode or Cached Health
        is_fast = request.query_params.get("fast", "false").lower() == "true"
        
        # Short-term cache to prevent thundering herd during load tests
        cache_key = "health_check_result"
        if not is_fast:
            cached_result = cache.get(cache_key)
            if cached_result:
                return Response(cached_result, status=status.HTTP_200_OK)

        health_status = {
            "status": "healthy",
            "services": {
                "django": "ok",
                "database": "unknown",
                "redis": "unknown",
                "celery": "unknown"
            }
        }
        
        if is_fast:
             health_status["services"]["mode"] = "fast"
             return Response(health_status, status=status.HTTP_200_OK)

        overall_healthy = True

        # 1. Database Check
        try:
            for conn in connections.all():
                conn.cursor().execute("SELECT 1")
            health_status["services"]["database"] = "ok"
        except Exception as e:
            logger.error(f"Health Check Database Error: {e}")
            health_status["services"]["database"] = f"error: {str(e)}"
            overall_healthy = False

        # 2. Redis Check
        try:
            cache.set("health_check_ping", "pong", timeout=5)
            if cache.get("health_check_ping") == "pong":
                health_status["services"]["redis"] = "ok"
            else:
                health_status["services"]["redis"] = "error: ping/pong failed"
                overall_healthy = False
        except Exception as e:
            logger.error(f"Health Check Redis Error: {e}")
            health_status["services"]["redis"] = f"error: {str(e)}"
            overall_healthy = False

        # 3. Celery Check
        try:
            # Optimization: Reduced timeout for broadcast check
            inspector = current_app.control.inspect(timeout=0.2)
            stats = inspector.stats()
            if stats:
                health_status["services"]["celery"] = "ok"
            else:
                health_status["services"]["celery"] = f"warning: no workers detected"
        except Exception as e:
            logger.error(f"Health Check Celery Error: {e}")
            health_status["services"]["celery"] = f"error: {str(e)}"

        if not overall_healthy:
            health_status["status"] = "unhealthy"
            return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Cache the result for 10 seconds
        cache.set(cache_key, health_status, timeout=10)
        return Response(health_status, status=status.HTTP_200_OK)
