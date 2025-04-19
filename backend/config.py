from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path
import secrets

class Settings(BaseSettings):
    # Configurações básicas
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Compactador de Arquivos"
    
    # Configurações de segurança
    SECRET_KEY: str = os.getenv("SECRET_KEY", "sua-chave-secreta-padrao-deve-ser-alterada-em-producao")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 dias
    
    # URL do frontend
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Configurações CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        os.getenv("FRONTEND_URL", ""),  # URL do frontend em produção
        "http://localhost:8000"
    ]
    
    # Limites e restrições
    MAX_FILE_SIZE: int = 1024 * 1024 * 1024 * 2  # 2GB
    ALLOWED_EXTENSIONS: List[str] = [
        ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".jpg", ".jpeg", ".png", ".gif", ".zip", ".rar"
    ]
    MAX_UPLOAD_CONCURRENCY: int = 5
    MAX_COMPRESSION_CONCURRENCY: int = 3
    
    # Diretórios
    BASE_DIR: Path = Path(__file__).resolve().parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    COMPRESSED_DIR: Path = BASE_DIR / "compressed"
    LOG_DIR: Path = BASE_DIR / "logs"
    
    # Configurações de Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Tempo de expiração para arquivos (em horas)
    FILE_EXPIRATION_HOURS: int = 24
    
    # Chave mestra para administração (gerada automaticamente)
    MASTER_KEY: str = secrets.token_urlsafe(32)
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings() 