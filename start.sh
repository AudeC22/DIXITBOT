#!/bin/bash
# start.sh — Lance les 3 services nécessaires à DIXIT BOT en une seule commande
# (Ollama, Backend FastAPI, Frontend Vite)
# Usage : ./start.sh   (depuis la racine du projet)

# Se place toujours à la racine du projet, peu importe d'où le script est appelé
cd "$(dirname "$0")"

# Fonction appelée à la fermeture (Ctrl+C) : arrête proprement tous les services lancés
cleanup() {
    echo ""
    echo "Arrêt des services..."
    kill $OLLAMA_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# 1. Lancer Ollama en arrière-plan (si pas déjà lancé)
if ! lsof -i :11434 >/dev/null 2>&1; then
    echo "Démarrage d'Ollama..."
    ollama serve &
    OLLAMA_PID=$!
    sleep 2
else
    echo "Ollama tourne déjà sur le port 11434."
fi

# 2. Lancer le backend FastAPI en arrière-plan (utilise le venv s'il existe)
echo "Démarrage du backend..."
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
fi
python -m app.main &
BACKEND_PID=$!
cd ..

# 3. Lancer le frontend Vite en arrière-plan
echo "Démarrage du frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Tous les services sont lancés."
echo "Frontend : http://localhost:5173"
echo "Backend  : http://localhost:51234"
echo "Appuie sur Ctrl+C pour tout arrêter."

# Attend que les processus tournent, garde le script actif
wait
