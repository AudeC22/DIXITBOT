# DIXITBOT

Création d'un chat IA BOT dans le cadre d'un Projet Epitech Groupe 34

# Vue d'ensemble du projet groupe 34

# Objectif SMART DIXITBOT

Création en 7 jours par une équipe de 5 personnes d'un chatbot IA (DIXITBOT) dédié à l'analyse de publications scientifiques et génération de réponse . Le bot doit traiter les requêtes utilisateurs sur six domaines : IA/ML, Algo, Systèmes, Cybersécurité, Génie logiciel et Interaction de données .

# Contributeurs / équipe

- Laetitia Zabbar
- Imène Tabet
- Luz mariel Vasquez
- Aude Comte
- Amine Marzak

# 🤖 DIXITBOT — Agent conversationnel intelligent pour revue de littérature scientifique

Ce projet est un **agent conversationnel intelligent** spécialisé dans la revue de littérature scientifique en informatique. Il permet de poser des questions sur des sujets scientifiques et utilise une base de connaissances (KB) enrichie par scraping automatique depuis ArXiv et Semantic Scholar.

Il repose sur une architecture moderne :

- **Frontend** : Application web en HTML/CSS/JavaScript avec Vite
- **Backend** : API REST en Python avec FastAPI
- **IA locale** : Ollama avec modèle de langage open-source (par défaut llama3)
- **Intégrations** : Scraping automatique d'articles scientifiques (ArXiv, Semantic Scholar)
- **Base de données** : Stockage local des connaissances extraites

---

## 🧱 Architecture (vue d'ensemble)

- **Frontend** : Interface utilisateur web simple et responsive
- **Backend** : Python + FastAPI pour les API REST
- **IA locale** : Ollama pour exécution de modèles LLM en local
- **Scraping** : Intégrations pour récupérer des données depuis ArXiv et Semantic Scholar
- **Mémoire/KB** : Stockage et gestion d'une base de connaissances locale

## Flux de fonctionnement

1. L'utilisateur pose une question via l'interface web
2. Le backend consulte la base de connaissances locale
3. Si nécessaire, déclenchement du scraping pour enrichir la KB
4. Analyse de la question par le modèle IA avec contexte
5. Réponse structurée en français avec citations des sources

## 🧩 Modules principaux

### 1) Module MCP Scraping (arXiv)

**Objectif** : Scraper des publications scientifiques depuis arXiv pour alimenter l'agent IA en données récentes et fiables.

**Localisation** : `backend/app/integrations/MCP_scraping/`

**Fonctionnalités** :

- Scraping intelligent des pages arXiv (search/cs, pages abstracts, pages HTML)
- Extraction structurée des métadonnées scientifiques
- Exportation en JSON et HTML pour cache/debug
- Intégration MCP (Model Context Protocol) avec les outils du backend

**Données extraites** :

_Depuis la page Search (search/cs)_ :

- `arxiv_id` : identifiant arXiv unique
- `title` : titre de la publication
- `authors` : liste des auteurs
- `abstract` : résumé de l'article
- `submitted_date` : date de soumission
- `abs_url`, `pdf_url` : URLs d'accès
- `primary_category` : catégorie principale
- `all_categories` : catégories associées

_Depuis la page /abs_ :

- `doi` : Digital Object Identifier (si disponible)
- `versions` : historique des versions
- `last_updated_raw` : dernière mise à jour
- `abstract` : résumé enrichi (fallback)
- Lien vers la version `/html`

_Depuis la page /html_ :

- `method` : section Méthodologie/Approche
- `references` : bibliographie complète

**Fichier principal** : `backend/app/integrations/MCP_scraping/scrapping.py`

**Utilisation** :

- L'agent déclenche le scraper via MCP lorsqu'une requête nécessite une recherche arXiv
- Les résultats sont stockés en cache dans `data_lake/raw/`
- Les données enrichies alimentent la réponse de l'agent

---

### 2) Module Email (MailHog)

**Objectif** : Envoyer l'historique des conversations par email (démo, test, archivage).

**Localisation** : Module intégré dans les routes API

**Fonctionnalités** :

- Envoi d'emails SMTP via MailHog (serveur local)
- Formatage HTML + texte brut de l'historique de conversation
- Configuration SMTP centralisée
- Intégration API FastAPI

**Configuration** :

- **SMTP local** : `127.0.0.1:1025`
- **UI MailHog** : `http://127.0.0.1:8025`

**Format de la requête** :

```json
{
  "recipient_email": "user@example.com",
  "conversation_history": [
    {
      "role": "user",
      "content": "Bonjour",
      "timestamp": "2026-01-15T13:15:00"
    },
    {
      "role": "assistant",
      "content": "Salut",
      "timestamp": "2026-01-15T13:15:05"
    }
  ],
  "subject": "Historique conversation DIXITBOT"
}
```

**Stockage** : Les historiques sont conservés en JSON dans `data_lake/raw/conversation_history/`

---

```
DIXITBOT/
├── README.md                 # Ce fichier
├── requirements.txt          # Dépendances Python
├── backend/                  # Code backend Python
│   └── app/
│       ├── __init__.py
│       ├── main.py           # Point d'entrée FastAPI
│       ├── api/
│       │   └── routes/       # Routes API (ask, health, kb, scrape)
│       ├── core/             # Noyau IA
│       │   ├── ollama_client.py  # Client HTTP pour Ollama
│       │   ├── prompts.py        # Prompts système et utilisateur
│       │   └── memory.py         # Gestion de la mémoire/KB
│       ├── integrations/     # Intégrations externes
│       │   └── MCP_scraping/ # Scraping ArXiv et Semantic Scholar
│       └── services/         # Services métier
├── data_lake/               # Stockage des données
│   ├── kb.json              # Base de connaissances JSON
│   ├── KB/                  # Dossier connaissances
│   ├── processed/           # Données traitées
│   └── raw/                 # Données brutes scrapées
├── frontend/                # Interface web
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── package.json
├── processing/              # Scripts de traitement
└── DOC/                     # Documentation
```

## Technologies utilisées

- FastAPI
- Ollama (avec modèle llama3)
- MailHog (pour les emails)
- HTML/CSS/JS (frontend)
- MCP-like tools (scraping)
- Python 3.10+

## 📚 Dépendances Python (modules utilisés)

### 🌐 Frameworks Web & API

| Module     | Version | Utilité                            |
| ---------- | ------- | ---------------------------------- |
| `fastapi`  | ≥0.100  | Framework API REST pour le backend |
| `uvicorn`  | ≥0.23   | Serveur ASGI pour FastAPI          |
| `pydantic` | ≥2.0    | Validation schémas + types stricts |

### 🔗 Requêtes HTTP & Communication

| Module     | Version | Utilité                               |
| ---------- | ------- | ------------------------------------- |
| `requests` | ≥2.31   | Requêtes HTTP (scraping arXiv)        |
| `aiohttp`  | ≥3.9    | Requêtes HTTP asynchrones (optionnel) |
| `httpx`    | ≥0.24   | Client HTTP moderne (optionnel)       |

### 🏗️ Parsing HTML & Web Scraping

| Module           | Version | Utilité                                 |
| ---------------- | ------- | --------------------------------------- |
| `beautifulsoup4` | ≥4.12   | Parsing HTML (extraction données arXiv) |
| `lxml`           | ≥4.9    | Parser HTML performant (backend BS4)    |
| `html5lib`       | ≥1.1    | Parser HTML robuste (fallback)          |

### 💾 Stockage & Sérialisation

| Module    | Version    | Utilité                              |
| --------- | ---------- | ------------------------------------ |
| `json`    | ✅ builtin | Sérialisation JSON (cache, exports)  |
| `pickle`  | ✅ builtin | Sérialisation Python (cache mémoire) |
| `sqlite3` | ✅ builtin | Base données locale (historique)     |

### 📧 Gestion Emails

| Module        | Version    | Utilité                        |
| ------------- | ---------- | ------------------------------ |
| `smtplib`     | ✅ builtin | Envoi SMTP (emails MailHog)    |
| `email.mime`  | ✅ builtin | Construction emails HTML/texte |
| `email.utils` | ✅ builtin | Formatage headers SMTP         |

### 🤖 IA & Ollama

| Module   | Version | Utilité                             |
| -------- | ------- | ----------------------------------- |
| `ollama` | ≥0.1    | Client Python Ollama (requêtes LLM) |

### 📊 Utilitaires & Outils

| Module     | Version    | Utilité                                 |
| ---------- | ---------- | --------------------------------------- |
| `os`       | ✅ builtin | Chemins fichiers / env variables        |
| `sys`      | ✅ builtin | Configuration système                   |
| `re`       | ✅ builtin | Regex (parsing catégories arXiv)        |
| `time`     | ✅ builtin | Pauses politenesses (scraping)          |
| `datetime` | ✅ builtin | Timestamps fichiers / conversations     |
| `random`   | ✅ builtin | Jitter timeouts (anti-pattern arXiv)    |
| `pathlib`  | ✅ builtin | Gestion chemins (cross-platform)        |
| `typing`   | ✅ builtin | Type hints (Dict, List, Optional, etc.) |
| `logging`  | ✅ builtin | Logs debug / erreurs                    |

### 🧪 Tests & Qualité (optionnel)

| Module           | Version | Utilité                   |
| ---------------- | ------- | ------------------------- |
| `pytest`         | ≥7.4    | Framework tests unitaires |
| `pytest-asyncio` | ≥0.21   | Tests async/await         |

---

### 1️⃣ Prérequis

- Windows 10 ou 11
- Python 3.10 ou plus
- Node.js 16+ (pour le frontend)
- Git
- Connexion Internet

### 2️⃣ Installer Ollama

Ollama permet d'exécuter des modèles de langage en local.

👉 Télécharger et installer Ollama pour Windows :  
https://ollama.com/download/windows

Après installation, vérifier :

```bash
ollama --version
```

Puis télécharger le modèle par défaut (llama3) :

```bash
ollama pull llama3
```

### 3️⃣ Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 4️⃣ Installer les dépendances frontend

```bash
cd frontend
npm install
```

### 5️⃣ Installer MailHog (module Email)

MailHog sert de boîte mail locale pour tester l'envoi d'emails.

**Téléchargement** : https://github.com/mailhog/MailHog/releases
(Fichier recommandé : `MailHog_windows_amd64.exe`)

**Lancement** :

```bash
# Exemple si MailHog est dans C:\MailHog\
C:\MailHog\MailHog_windows_amd64.exe
```

**Interface web MailHog** : http://127.0.0.1:8025

**Ports utilisés** :

- SMTP : `1025`
- UI : `8025`

## 🚀 Lancement

### 1️⃣ Lancer MailHog

Dans un terminal :

```bash
C:\MailHog\MailHog_windows_amd64.exe
```

### 2️⃣ Lancer Ollama

Dans un autre terminal :

```bash
ollama serve
```

Le serveur Ollama démarre sur http://127.0.0.1:11434

### 3️⃣ Lancer le backend

Dans un troisième terminal, depuis la racine du projet :

```bash
cd backend
python -m app.main
```

L'API FastAPI sera disponible sur http://127.0.0.1:8000

### 4️⃣ Lancer le frontend

Dans un quatrième terminal :

```bash
cd frontend
npm run dev
```

L'interface web sera accessible sur http://localhost:5173 (ou le port indiqué par Vite)

## 📍 Ports utilisés (récapitulatif)

| Service         | URL/Port                   |
| --------------- | -------------------------- |
| Backend FastAPI | http://127.0.0.1:8000      |
| Swagger UI      | http://127.0.0.1:8000/docs |
| Frontend        | http://localhost:5173      |
| MailHog SMTP    | 127.0.0.1:1025             |
| MailHog UI      | http://127.0.0.1:8025      |
| Ollama API      | http://127.0.0.1:11434     |

## ✅ Tests rapides

### Test de l'envoi d'email via Swagger

1. Ouvrir : http://127.0.0.1:8000/docs
2. Localiser l'endpoint : `POST /send-email`
3. Cliquer sur "Try it out"
4. Remplir le corps JSON :

```json
{
  "recipient_email": "test@example.com",
  "conversation_history": [
    {
      "role": "user",
      "content": "Bonjour, quels sont les derniers progrès en IA/ML ?",
      "timestamp": "2026-01-15T13:15:00"
    },
    {
      "role": "assistant",
      "content": "Les derniers progrès concernent les transformers et les modèles de diffusion...",
      "timestamp": "2026-01-15T13:15:05"
    }
  ],
  "subject": "Historique de ma conversation avec DIXITBOT"
}
```

5. Vérifier l'email dans MailHog : http://127.0.0.1:8025

---

## 💡 Utilisation

- **data_lake/raw/** : Contient les données scrapées brutes (HTML/JSON d'ArXiv)
- **data_lake/processed/** : Données traitées et nettoyées
- **data_lake/kb.json** : Base de connaissances consolidée

## 🔧 Configuration

- Modèle Ollama : Configurable via variable d'environnement `OLLAMA_MODEL` (défaut: llama3)
- Port Ollama : `OLLAMA_BASE_URL` (défaut: http://127.0.0.1:11434)
- Timeout et rate limiting : Ajustables dans `ollama_client.py`

## 📝 Notes de développement

- Le projet utilise une architecture modulaire pour faciliter l'extension
- Les prompts sont en français pour des réponses localisées
- Le scraping respecte les conditions d'utilisation des sites sources
- Toutes les dépendances sont listées dans requirements.txt

---

Développé pour le projet IA BOT - Epitech Groupe 34
