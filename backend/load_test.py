import aiohttp
import asyncio
import os
from pathlib import Path
import time
from datetime import datetime

# Configurações do teste
NUM_CONCURRENT_USERS = 50  # Número de usuários simultâneos
TEST_DURATION = 300  # Duração do teste em segundos
BASE_URL = "http://localhost:8000"
TEST_FILE_SIZE_MB = 10  # Tamanho do arquivo de teste em MB

async def generate_test_file(size_mb):
    """Gera um arquivo de teste com o tamanho especificado"""
    file_path = Path("test_file.txt")
    with open(file_path, "wb") as f:
        f.write(os.urandom(size_mb * 1024 * 1024))
    return file_path

async def upload_and_download(session, file_path, user_id):
    """Simula um ciclo completo de upload e download para um usuário"""
    try:
        # Upload
        start_time = time.time()
        data = aiohttp.FormData()
        data.add_field('file',
                      open(file_path, 'rb'),
                      filename=f'test_file_{user_id}.txt')
        
        async with session.post(f"{BASE_URL}/upload/", data=data) as response:
            if response.status == 200:
                result = await response.json()
                upload_time = time.time() - start_time
                print(f"Usuário {user_id}: Upload completo em {upload_time:.2f}s")
                
                # Download
                start_time = time.time()
                filename = result['filename']
                async with session.get(f"{BASE_URL}/download/{filename}") as download_response:
                    if download_response.status == 200:
                        await download_response.read()
                        download_time = time.time() - start_time
                        print(f"Usuário {user_id}: Download completo em {download_time:.2f}s")
                        return True, upload_time, download_time
            
            return False, 0, 0
    except Exception as e:
        print(f"Erro para usuário {user_id}: {str(e)}")
        return False, 0, 0

async def user_simulation(file_path, user_id):
    """Simula o comportamento de um único usuário"""
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        successful_requests = 0
        total_upload_time = 0
        total_download_time = 0
        
        while time.time() - start_time < TEST_DURATION:
            success, upload_time, download_time = await upload_and_download(session, file_path, user_id)
            if success:
                successful_requests += 1
                total_upload_time += upload_time
                total_download_time += download_time
            await asyncio.sleep(1)  # Pequeno intervalo entre requisições
        
        return {
            'user_id': user_id,
            'successful_requests': successful_requests,
            'avg_upload_time': total_upload_time / successful_requests if successful_requests > 0 else 0,
            'avg_download_time': total_download_time / successful_requests if successful_requests > 0 else 0
        }

async def main():
    print(f"Iniciando teste de carga com {NUM_CONCURRENT_USERS} usuários simultâneos...")
    print(f"Duração do teste: {TEST_DURATION} segundos")
    print(f"Tamanho do arquivo de teste: {TEST_FILE_SIZE_MB}MB")
    
    # Gerar arquivo de teste
    file_path = await generate_test_file(TEST_FILE_SIZE_MB)
    
    # Iniciar simulações de usuários
    start_time = time.time()
    tasks = [user_simulation(file_path, i) for i in range(NUM_CONCURRENT_USERS)]
    results = await asyncio.gather(*tasks)
    
    # Calcular estatísticas
    total_requests = sum(r['successful_requests'] for r in results)
    total_time = time.time() - start_time
    avg_upload_time = sum(r['avg_upload_time'] for r in results) / len(results)
    avg_download_time = sum(r['avg_download_time'] for r in results) / len(results)
    
    print("\nResultados do teste de carga:")
    print(f"Total de requisições bem-sucedidas: {total_requests}")
    print(f"Requisições por segundo: {total_requests / total_time:.2f}")
    print(f"Tempo médio de upload: {avg_upload_time:.2f}s")
    print(f"Tempo médio de download: {avg_download_time:.2f}s")
    
    # Limpar arquivo de teste
    os.remove(file_path)

if __name__ == "__main__":
    asyncio.run(main()) 