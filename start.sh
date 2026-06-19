#!/bin/bash
set -e

echo "=== ArbiTrack - Configurando ambiente ==="

cd backend

if [ ! -f .env ]; then
  cp .env.example .env
  echo "📋 Arquivo .env criado. Edite backend/.env e adicione sua ODDS_API_KEY para modo ao vivo."
  echo "   Sem API key, o app roda em modo demonstração com dados simulados."
fi

echo "📦 Instalando dependências..."
pip install -q -r requirements.txt

echo "🚀 Iniciando servidor em http://localhost:8000"
python main.py
