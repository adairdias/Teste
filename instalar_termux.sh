#!/usr/bin/env bash
# Script de instalação para Termux (Android)

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     Instalando Extrator Telegram     ║"
echo "╚══════════════════════════════════════╝"
echo ""

echo "[1/3] Atualizando pacotes..."
pkg update -y && pkg upgrade -y

echo ""
echo "[2/3] Instalando Python..."
pkg install python -y

echo ""
echo "[3/3] Instalando bibliotecas Python..."
pip install flask telethon

echo ""
echo "╔══════════════════════════════════════╗"
echo "║      Instalação concluída!           ║"
echo "╠══════════════════════════════════════╣"
echo "║                                      ║"
echo "║  Para iniciar o app:                 ║"
echo "║    python app.py                     ║"
echo "║                                      ║"
echo "║  Depois abra o Chrome e acesse:      ║"
echo "║    http://localhost:5000             ║"
echo "║                                      ║"
echo "╚══════════════════════════════════════╝"
echo ""
