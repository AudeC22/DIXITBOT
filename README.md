# DIXITBOT

DIXITBOT est un agent conversationnel orienté revue de littérature scientifique. Le backend traite les questions utilisateur, enrichit la réponse à partir d'une base de connaissances locale et de sources arXiv, puis renvoie une synthèse structurée.

## Vue d'ensemble

- Backend FastAPI
- Frontend Vite
- Modèle local Ollama
- Scraping arXiv et indexation locale
- API de question/réponse sur /api/ask

## Architecture

- Frontend : interface web simple en HTML/CSS/JavaScript
- Backend : API REST Python avec FastAPI
- IA locale : Ollama avec le modèle qwen3:1.7b
- Intégrations : récupération de métadonnées arXiv et enrichissement de la réponse
- Stockage : base de connaissances locale dans data_lake

## Prérequis

- Python 3.11+
- Node.js
- Git
- Ollama installé

## Installation

Depuis la racine du projet :

```bash
pip install -r requirements.txt
```

Installation du frontend :

```bash
cd frontend
npm install
cd ..
```

Téléchargement du modèle Ollama :

```bash
ollama pull qwen3:1.7b
```

## Lancement sous Windows

### 1. Vérification d'Ollama

```bash
ollama list
```

Le modèle qwen3:1.7b doit apparaître.

Si Ollama est déjà lancé, l'instruction suivante ne doit pas être utilisée :

```bash
ollama serve
```

### 2. Lancer le backend

Depuis la racine du projet :

```bash
cd backend
python -m app.main
```

Le backend est disponible sur :

```text
http://127.0.0.1:51234
```

La documentation Swagger est disponible sur :

```text
http://127.0.0.1:51234/docs
```

### 3. Lancer le frontend

Dans un nouveau terminal :

```bash
cd frontend
npm run dev
```

Le frontend est disponible sur :

```text
http://localhost:5173
```

## Utilisation de l'API

Endpoint principal :

```text
POST /api/ask
```

Exemple de requête :

```json
{
  "question": "Transformer models for medical imaging"
}
```

La réponse contient généralement :

- un texte de synthèse
- les sources issues de la base de connaissances
- les sources issues d'arXiv lorsque des résultats sont disponibles

## Tests rapides

1. Lancer le backend.
2. Ouvrir la documentation Swagger sur http://127.0.0.1:51234/docs.
3. Tester l'endpoint POST /api/ask avec une requête précise.
4. Vérifier un statut HTTP 200 et une réponse structurée.

## Limites connues

### Modèle LLM

Le comportement dépend du modèle local Ollama et des données disponibles. Des limites possibles incluent :

- hallucinations
- perte de cohérence sur des échanges très longs
- réponses approximatives si le contexte est insuffisant

### arXiv

Les requêtes arXiv peuvent temporairement échouer avec un code HTTP 429. Les causes fréquentes sont :

- un volume trop important de requêtes
- une requête trop générale
- une limitation temporaire liée à l'adresse IP

Les requêtes plus spécifiques produisent généralement de meilleurs résultats.

## Structure du projet

```text
DIXITBOT/
├── README.md
├── requirements.txt
├── backend/
│   └── app/
│       ├── api/
│       ├── core/
│       ├── integrations/
│       └── services/
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── package.json
└── data_lake/
```

## Notes techniques

- Le frontend envoie les questions vers /api/ask.
- Le backend peut utiliser la base de connaissances locale ainsi que des métadonnées arXiv.
- Le scraping utilise l'API ArXiv Atom, pas un navigateur HTML.
- Le scraping extrait des métadonnées et des abstracts et stocke le résultat en JSON.
- Les requêtes ne sont pas normalisées au-delà d'un petit nettoyage de ponctuation.
- Il n'existe pas de post-traitement de citation ni de recherche sémantique dans le code actuel.
- Une route d'email est exposée sur `/api/send-email`.
- L'envoi d'email utilise `smtplib` vers un SMTP local (`127.0.0.1:1025` par défaut).
- Le contenu envoyé est généré en HTML et une copie JSON de l'historique est sauvegardée dans `data_lake/raw/conversation_history/`.

---

Projet IA BOT — Epitech Groupe 34
