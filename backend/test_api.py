import requests
import json

# URL base da API
BASE_URL = "http://localhost:8000"

def test_api():
    # 1. Gerar API Key
    print("Gerando API Key...")
    response = requests.post(f"{BASE_URL}/api/keys/generate")
    if response.status_code == 200:
        api_key = response.json()["api_key"]
        print(f"API Key gerada: {api_key}")
    else:
        print(f"Erro ao gerar API Key: {response.status_code}")
        return

    # 2. Testar upload de arquivo
    print("\nTestando upload de arquivo...")
    headers = {"X-API-Key": api_key}
    
    with open("test.txt", "rb") as f:
        files = {"file": ("test.txt", f, "text/plain")}
        response = requests.post(f"{BASE_URL}/upload/", headers=headers, files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Upload bem sucedido!")
            print(f"Nome do arquivo compactado: {result['filename']}")
            print(f"Tamanho original: {result['original_size']} bytes")
            print(f"Tamanho compactado: {result['compressed_size']} bytes")
            
            # 3. Testar download do arquivo
            print("\nTestando download do arquivo...")
            response = requests.get(f"{BASE_URL}/download/{result['filename']}", headers=headers)
            
            if response.status_code == 200:
                with open(f"downloaded_{result['filename']}", "wb") as f:
                    f.write(response.content)
                print("Download bem sucedido!")
            else:
                print(f"Erro no download: {response.status_code}")
        else:
            print(f"Erro no upload: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    test_api() 