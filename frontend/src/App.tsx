import React, { useState, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API_KEY = process.env.REACT_APP_API_KEY || 'dev_key';

function App() {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [downloadLink, setDownloadLink] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState('');

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadProgress(0);
    setDownloadLink('');
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_URL}/upload/`, formData, {
        headers: {
          'X-API-Key': API_KEY
        },
        onUploadProgress: (progressEvent: any) => {
          const progress = progressEvent.total
            ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
            : 0;
          setUploadProgress(progress);
        },
      });

      setDownloadLink(response.data.filename);
    } catch (error: any) {
      if (error.response) {
        // Erro do servidor
        if (error.response.status === 401) {
          setError('Erro de autenticação. Por favor, verifique sua API Key.');
        } else if (error.response.status === 413) {
          setError('O arquivo é muito grande.');
        } else {
          setError(`Erro do servidor: ${error.response.data.detail || 'Erro desconhecido'}`);
        }
      } else if (error.request) {
        // Erro de conexão
        setError('Erro de conexão com o servidor.');
      } else {
        setError('Ocorreu um erro ao processar o arquivo.');
      }
      console.error('Erro:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownload = async () => {
    if (!downloadLink) return;
    
    try {
      const response = await axios.get(`${API_URL}/download/${downloadLink}`, {
        headers: {
          'X-API-Key': API_KEY
        },
        responseType: 'blob'
      });
      
      // Criar URL do blob e iniciar download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', downloadLink);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      if (error.response?.status === 401) {
        setError('Erro de autenticação ao baixar o arquivo.');
      } else {
        setError('Erro ao baixar o arquivo.');
      }
      console.error('Erro no download:', error);
    }
  };

  return (
    <div className="container">
      <h1>Compactador de Arquivos</h1>
      
      <div className="upload-box">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileUpload}
          style={{ display: 'none' }}
        />
        
        <button
          className="upload-button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
        >
          Selecionar Arquivo
        </button>

        {isUploading && (
          <div className="progress-container">
            <p>Enviando arquivo... {uploadProgress}%</p>
            <div className="progress-bar">
              <div 
                className="progress-fill"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {downloadLink && (
          <button
            onClick={handleDownload}
            className="download-button"
          >
            Baixar Arquivo Compactado
          </button>
        )}
      </div>
    </div>
  );
}

export default App;
