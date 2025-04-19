from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
from datetime import datetime, timedelta
import hashlib
from config import settings
import os

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests = {}
        
    async def dispatch(self, request: Request, call_next: Callable):
        # Obtém o IP do cliente
        client_ip = request.client.host
        current_time = datetime.now()
        
        # Limpa registros antigos
        self.cleanup_old_records(current_time)
        
        # Verifica o rate limit
        if not self.is_request_allowed(client_ip, current_time):
            raise HTTPException(
                status_code=429,
                detail="Muitas requisições. Por favor, tente novamente em alguns minutos."
            )
        
        # Adiciona a requisição ao registro
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)
        
        response = await call_next(request)
        return response
    
    def cleanup_old_records(self, current_time: datetime):
        cutoff_time = current_time - timedelta(minutes=1)
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                req_time for req_time in self.requests[ip]
                if req_time > cutoff_time
            ]
            if not self.requests[ip]:
                del self.requests[ip]
    
    def is_request_allowed(self, client_ip: str, current_time: datetime) -> bool:
        if client_ip not in self.requests:
            return True
        
        # Conta requisições no último minuto
        minute_ago = current_time - timedelta(minutes=1)
        recent_requests = sum(1 for req_time in self.requests[client_ip] if req_time > minute_ago)
        
        return recent_requests < settings.RATE_LIMIT_PER_MINUTE

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Adiciona headers de segurança
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        
        return response

class FileValidationMiddleware:
    @staticmethod
    def is_valid_file(filename: str) -> bool:
        # Verifica extensão do arquivo
        ext = os.path.splitext(filename)[1].lower()
        return ext in settings.ALLOWED_EXTENSIONS
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        # Remove caracteres potencialmente perigosos
        filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
        return filename
    
    @staticmethod
    def generate_safe_filename(original_filename: str) -> str:
        # Gera um nome de arquivo seguro baseado no original
        name, ext = os.path.splitext(original_filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = FileValidationMiddleware.sanitize_filename(name)
        hash_part = hashlib.md5(original_filename.encode()).hexdigest()[:8]
        return f"{safe_name}_{timestamp}_{hash_part}{ext}" 