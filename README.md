# Compactador de Arquivos

Aplicação web para compactação de arquivos usando FastAPI e React.

## Funcionalidades

- Upload de arquivos grandes via streaming
- Compactação em formato ZIP
- Interface responsiva e amigável
- Barra de progresso durante upload
- Download do arquivo compactado
- Limpeza automática de arquivos antigos

## Requisitos

- Python 3.8+
- Node.js 14+
- npm ou yarn

## Deploy

### Backend (Render.com)

1. Crie uma conta no [Render.com](https://render.com)
2. Clique em "New +" e selecione "Web Service"
3. Conecte seu repositório GitHub
4. Configure o serviço:
   - Nome: compactador-backend
   - Runtime: Python 3
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Clique em "Create Web Service"
6. Nas variáveis de ambiente, adicione:
   - `MASTER_KEY`: Sua chave mestra de produção
   - `FRONTEND_URL`: URL do seu frontend no Vercel

### Frontend (Vercel)

1. Crie uma conta no [Vercel](https://vercel.com)
2. Importe seu repositório GitHub
3. Configure o projeto:
   - Framework Preset: Create React App
   - Root Directory: frontend
4. Em "Environment Variables", adicione:
   - `REACT_APP_API_URL`: URL do seu backend no Render
   - `REACT_APP_API_KEY`: Sua chave de API de produção
5. Clique em "Deploy"

## Desenvolvimento Local

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm start
```

## Configuração

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## Configurações

- O tamanho máximo de arquivo pode ser ajustado em `backend/main.py` (MAX_FILE_SIZE)
- Os arquivos são automaticamente removidos após 24 horas
- Os logs são armazenados em `backend/logs/app.log`

## Segurança

Em produção:
1. Gere uma nova API Key através do endpoint `/api/keys/generate`
2. Atualize a variável `REACT_APP_API_KEY` no Vercel
3. Nunca compartilhe suas chaves de API

## Limitações

- Tamanho máximo de arquivo: 2GB (configurável)
- Formato de compactação: ZIP
- Tempo de retenção: 24 horas 