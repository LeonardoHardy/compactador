from fastapi import FastAPI, UploadFile, HTTPException, Query, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import APIKeyHeader
import os
import zipfile
import lzma
import shutil
from datetime import datetime, timedelta
from loguru import logger
import asyncio
from pathlib import Path
import traceback
from typing import Optional
from config import settings
from middleware import RateLimitMiddleware, SecurityHeadersMiddleware, FileValidationMiddleware
import secrets

# Lista global de API Keys (em produção, use um banco de dados)
API_KEYS = {os.getenv("API_KEY", "dev_key")}  # Usando a API_KEY do ambiente

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    root_path=os.getenv("ROOT_PATH", "")
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adiciona middlewares de segurança
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Configuração de diretórios
settings.UPLOAD_DIR.mkdir(exist_ok=True)
settings.COMPRESSED_DIR.mkdir(exist_ok=True)
settings.LOG_DIR.mkdir(exist_ok=True)

# Rota raiz que aceita GET e HEAD
@app.get("/")
@app.head("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "description": "API para compactação de arquivos",
        "endpoints": {
            "docs": "/docs",
            "upload": "/upload/",
            "download": "/download/{filename}"
        },
        "status": "online"
    }

# Configuração de logs
logger.add(
    settings.LOG_DIR / "error.log",
    rotation="100 MB",
    level="ERROR",
    backtrace=True,
    diagnose=True
)

logger.add(
    settings.LOG_DIR / "info.log",
    rotation="100 MB",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}"
)

# Semáforos para controle de concorrência
UPLOAD_SEMAPHORE = asyncio.Semaphore(settings.MAX_UPLOAD_CONCURRENCY)
COMPRESSION_SEMAPHORE = asyncio.Semaphore(settings.MAX_COMPRESSION_CONCURRENCY)

# Sistema de API Keys
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Depends(API_KEY_HEADER)):
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API Key não fornecida"
        )
    if api_key not in API_KEYS and api_key != settings.MASTER_KEY:
        raise HTTPException(
            status_code=401,
            detail="API Key inválida"
        )
    return api_key

@app.post("/api/keys/generate")
async def generate_api_key():
    try:
        new_key = secrets.token_urlsafe(32)
        API_KEYS.add(new_key)
        logger.info(f"Nova API Key gerada")
        return JSONResponse(content={"api_key": new_key})
    except Exception as e:
        logger.error(f"Erro ao gerar API Key: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao gerar API Key")

@app.post("/upload/")
async def upload_file(
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    compression_level: int = Query(default=9, ge=1, le=9),
    api_key: str = Depends(get_api_key)
):
    # Validação do arquivo
    if not FileValidationMiddleware.is_valid_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo não permitido"
        )
    
    file_path = None
    xz_path = None
    zip_path = None
    
    try:
        async with UPLOAD_SEMAPHORE:
            logger.info(f"Iniciando upload do arquivo: {file.filename}")
            
            # Gera um nome seguro para o arquivo
            safe_filename = FileValidationMiddleware.generate_safe_filename(file.filename)
            file_path = settings.UPLOAD_DIR / safe_filename
            
            # Validação e salvamento do arquivo
            file_size = 0
            try:
                with open(file_path, "wb") as buffer:
                    while chunk := await file.read(1024 * 1024):
                        file_size += len(chunk)
                        if file_size > settings.MAX_FILE_SIZE:
                            raise HTTPException(
                                status_code=413,
                                detail="Arquivo muito grande"
                            )
                        buffer.write(chunk)
            except Exception as e:
                logger.error(f"Erro ao salvar arquivo: {str(e)}\n{traceback.format_exc()}")
                raise HTTPException(status_code=500, detail="Erro ao salvar arquivo")
            
            # Compressão do arquivo
            async with COMPRESSION_SEMAPHORE:
                try:
                    compressed_filename = f"{safe_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    xz_path = settings.COMPRESSED_DIR / f"{compressed_filename}.xz"
                    zip_path = settings.COMPRESSED_DIR / f"{compressed_filename}.zip"
                    
                    # Tenta LZMA primeiro
                    with lzma.open(xz_path, "wb", preset=compression_level) as xz:
                        with open(file_path, "rb") as f:
                            shutil.copyfileobj(f, xz)
                    
                    if xz_path.stat().st_size < file_size:
                        final_path = xz_path
                        if zip_path.exists():
                            os.remove(zip_path)
                    else:
                        # Se LZMA não for eficiente, tenta ZIP
                        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=compression_level) as zipf:
                            zipf.write(file_path, safe_filename)
                        
                        if zip_path.stat().st_size < xz_path.stat().st_size:
                            os.remove(xz_path)
                            final_path = zip_path
                        else:
                            os.remove(zip_path)
                            final_path = xz_path
                    
                except Exception as e:
                    logger.error(f"Erro na compressão: {str(e)}\n{traceback.format_exc()}")
                    raise HTTPException(status_code=500, detail="Erro na compressão do arquivo")
            
            # Limpa o arquivo original em background
            background_tasks.add_task(cleanup_file, file_path)
            
            return {
                "filename": final_path.name,
                "original_size": file_size,
                "compressed_size": final_path.stat().st_size
            }
    
    except Exception as e:
        logger.error(f"Erro ao processar arquivo: {str(e)}\n{traceback.format_exc()}")
        await cleanup_files(file_path, xz_path, zip_path)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(
    filename: str,
    api_key: str = Depends(get_api_key)
):
    file_path = settings.COMPRESSED_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    # Verifica se o arquivo expirou
    file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
    if file_age > timedelta(hours=settings.FILE_EXPIRATION_HOURS):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Erro ao remover arquivo expirado: {str(e)}")
        raise HTTPException(status_code=404, detail="Arquivo expirado")
    
    def iterfile():
        with open(file_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                yield chunk
    
    content_type = "application/x-xz" if filename.endswith(".xz") else "application/zip"
    
    return StreamingResponse(
        iterfile(),
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Content-Type-Options": "nosniff"
        }
    )

async def cleanup_files(*files: Optional[Path]):
    for file in files:
        if file and file.exists():
            try:
                os.remove(file)
                logger.info(f"Arquivo removido: {file}")
            except Exception as e:
                logger.error(f"Erro ao remover arquivo {file}: {str(e)}")

def cleanup_file(file: Path):
    try:
        if file.exists():
            os.remove(file)
            logger.info(f"Arquivo original removido: {file}")
    except Exception as e:
        logger.error(f"Erro ao remover arquivo original {file}: {str(e)}")

@app.on_event("startup")
async def startup_event():
    logger.info("Iniciando servidor e configurando limpeza automática")
    asyncio.create_task(cleanup_old_files())

async def cleanup_old_files():
    while True:
        try:
            current_time = datetime.now()
            for dir_path in [settings.UPLOAD_DIR, settings.COMPRESSED_DIR]:
                for file_path in dir_path.glob("*"):
                    file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_age > timedelta(hours=settings.FILE_EXPIRATION_HOURS):
                        try:
                            os.remove(file_path)
                            logger.info(f"Arquivo antigo removido: {file_path}")
                        except Exception as e:
                            logger.error(f"Erro na limpeza do arquivo: {str(e)}")
        except Exception as e:
            logger.error(f"Erro na limpeza automática: {str(e)}")
        
        await asyncio.sleep(3600)  # Verifica a cada hora

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 