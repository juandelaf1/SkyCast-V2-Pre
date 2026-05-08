"""
Rate Limiter - ClimApp-Analytics-Pro
===========================
Protege la API contra abuso.
- Limita requests por IP
- Limita requests por endpoint
"""

import time
import logging
from typing import Dict, Tuple
from collections import defaultdict
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)


class RateLimiter:
    """Implementa rate limiting en memoria."""
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.limits = {
            "default": {"requests": 100, "window": 60},        # 100 req/min por defecto
            "api_clima": {"requests": 30, "window": 60},      # 30 req/min para clima
            "api_geo": {"requests": 10, "window": 60},        # 10 req/min para geo
        }
        self.block_duration = 60  # Bloquear por 60 segundos si excede
    
    def _get_client_ip(self) -> str:
        """Obtiene IP del cliente."""
        return request.headers.get('X-Forwarded-For', 
                request.headers.get('X-Real-IP',
                request.remote_addr))
    
    def is_allowed(self, endpoint: str = "default") -> Tuple[bool, Dict]:
        """Verifica si el request está permitido."""
        client_ip = self._get_client_ip()
        key = f"{endpoint}:{client_ip}"
        
        now = time.time()
        limit_config = self.limits.get(endpoint, self.limits["default"])
        max_requests = limit_config["requests"]
        window = limit_config["window"]
        
        # Limpiar requests antiguos
        self.requests[key] = [
            t for t in self.requests[key] 
            if now - t < window
        ]
        
        # Verificar límite
        if len(self.requests[key]) >= max_requests:
            # Bloquear IP
            self.requests[key] = [now]  # Resetear
            logger.warning(f"Rate limit excedido para {client_ip} en {endpoint}")
            return False, {
                "error": "Rate limit excedido",
                "limite": max_requests,
                "ventana": window,
                "intentar_en": window
            }
        
        # Permitir y registrar
        self.requests[key].append(now)
        return True, {}
    
    def reset(self, ip: str = None):
        """Reinicia límites para una IP."""
        if ip:
            for key in list(self.requests.keys()):
                if ip in key:
                    del self.requests[key]


# Instancia global
_rate_limiter = RateLimiter()


def rate_limit(endpoint: str = "default"):
    """Decorator para aplicar rate limiting."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            allowed, info = _rate_limiter.is_allowed(endpoint)
            if not allowed:
                return jsonify(info), 429
            return f(*args, **kwargs)
        return wrapped
    return decorator


def check_rate_limit(endpoint: str = "default"):
    """Verifica rate limit sin decorator."""
    return _rate_limiter.is_allowed(endpoint)


def get_rate_status() -> Dict:
    """Obtiene estado del rate limiter."""
    now = time.time()
    stats = {}
    for key, timestamps in _rate_limiter.requests.items():
        # Limpiar antiguos
        fresh = [t for t in timestamps if now - t < 60]
        if fresh:
            endpoint, ip = key.split(":")
            if endpoint not in stats:
                stats[endpoint] = {"ips": 0, "requests": 0}
            stats[endpoint]["ips"] += 1
            stats[endpoint]["requests"] += len(fresh)
    return stats