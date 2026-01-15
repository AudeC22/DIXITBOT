# Vue d’ensemble du projet groupe 34

# Objectif SMART DIXITBOT
Création en 7 jours par une équipe de 5 personnes d'un chatbot IA (DIXITBOT) dédié à l'analyse de publications scientifiques et génération de réponse . Le bot doit traiter les requêtes utilisateurs sur six domaines : IA/ML, Algo, Systèmes, Cybersécurité, Génie logiciel et Interaction de données .


# Contributeurs / équipe
Laetitia Zabbar
Imène Tabet
Luz mariel Vasquez
Aude Comte
Amine Marzak

# 🤖 DIXITBOT — Agent conversationnel intelligent

📦 Structure du projet
Ce projet est un **agent conversationnel intelligent** développé dans le cadre du projet IA BOT qui génère des réponses via Ollama (Qwen3).
Il repose sur une architecture en **4 couches** :
- Frontend (web app (HTML/CSS/JS))
- Backend Python → API FastAPI(API REST) + outils MCP + scraping + email
- data_lake/ → Cache, raw HTML, exports
- module_Email/ → Tool email
- Modèle IA local (Ollama)
- requirements.txt → Dépendances Python

---

## 🧱 Architecture (vue d’ensemble)

- **Frontend** : HTML / CSS / JavaScript  
- **Backend** : Python + FastAPI  
- **IA locale** : Ollama + modèle ` `  
- **Tooling** : outils déclenchés par l’agent (ex: scraping arXiv) + module email
- **Communication** : API REST (Swagger dispo)

## 📁 Arborescence du projet

```txt
DIXITBOT/
├─ backend/
│  ├─ app/
│  │  ├─ core/
│  │  │  ├─ memory.py            # Gestion mémoire conversation (in-memory / store)
│  │  │  ├─ ollama_client.py     # Client HTTP vers Ollama (localhost:11434)
│  │  │  └─ prompts.py           # Prompts système (anti-hallu + format réponse)
│  │  ├─ integrations/
│  │  │  ├─ mcp/
│  │  │  │  ├─ schemas.py        # Schémas Pydantic côté MCP
│  │  │  │  ├─ server.py         # Serveur / routing MCP
│  │  │  │  └─ tools.py          # Déclaration outils exposés (scraping etc.)
│  │  │  └─ scraping/
│  │  │     └─ scrapping.py      # Implémentation scraper arXiv (HTML + /abs + /html)
│  │  └─ main.py                 # Entrée FastAPI (endpoints)
│  ├─ data_lake/                 # Cache & outputs (raw/cache, exports)
│  └─ ...
├─ frontend/                     # UI (appel API /ask, /send-email)
├─ README.md                     # Documentation projet
└─ requirements.txt              # Dépendances Python

## Flux agentique

1. L’utilisateur envoie une requête via l’interface web (frontend)
2. Le backend analyse l’intention
3. La mémoire et la knowledge base sont consultées
4. Si l’information est insuffisante, un tool (équivalent à MCP) est déclenché
5. Le tool effectue un scraping ciblé (de arXiv)
6. Les données sont analysées par le modèle IA local (Ollama)
7. Une réponse contextualisée est retournée au frontend à l’utilisateur

## Technologies utilisées
_ FastAPI
_ Ollama
_ MailHog
_ HTML/CSS/JS
_ MCP-like tools
_ Python 3.13

Licence : Aucune licence necessaire

🧩 Modules principaux
1) Module Scraping (arXiv)

Scraping de pages publiques arXiv : search/cs (page research computer science)+ /abs (page “Abstract”)+ (si dispo) /html
Sorties :
_ JSON structuré (résultats enrichis)
_ HTML bundle (debug local / preuve)
Fichier principal : backend/app/integrations/scraping/scrapping.py

Les champs qui sont extraits : 
Depuis la page Search (search/cs)
_ arxiv_id
_ title
_ authors
_ abstract
_ submitted_date
_ abs_url, pdf_url
_ primary_category
_ all_categories

Depuis /abs
_ doi (si présent)
_ versions, last_updated_raw
_ abstract (fallback si vide côté search)
_ lien /html (si disponible)

Depuis /html
_ method (section Method/Methods/Methodology/Approach)
_ references (bibliographie)

3) Module Email (MailHog en local)

Objectif : envoyer par email l’historique d’une conversation (pour démo + test).

SMTP local : 127.0.0.1:1025

UI MailHog : http://127.0.0.1:8025

Outil email (format texte + HTML + envoi SMTP) : module_Email/email_tool.py
Config SMTP : module_Email/config.json
Endpoint : POST /send-email dans backend/app/main.py

ℹ️ Le module email utilise le conversation_history fourni (par le ?).
L’historique est dans raw/conversation_history/ en format JSON

Installation (environnement local)
Prérequis
Windows 10 / 11 ou macOS (Sequoia 15.7.3)

Python 3.13.7

Git

Connexion Internet (scraping + téléchargement du modèle IA)

Création de l’environnement virtuel et installation des dépendances
bash
# Depuis la racine du projet
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# Installation des dépendances Python
pip install -r requirements.txt
Installation d’Ollama (obligatoire)
Ollama permet d’exécuter un modèle de langage open‑source en local.

Téléchargement : https://ollama.com/download/windows

Après installation, redémarrer le terminal puis vérifier :

bash
ollama --version
ollama pull qwen3:1.7b
Installation de MailHog (module Email)
MailHog sert de boîte mail locale pour tester l’envoi d’emails.

Téléchargement : https://github.com/AudeC22/DIXITBOT.git  
(Fichier recommandé : MailHog_windows_amd64.exe)

Lancement :

bash
# Exemple si MailHog est dans C:\MailHog\
C:\MailHog\MailHog_windows_amd64.exe
Interface web MailHog :
http://127.0.0.1:8025

Ports utilisés :

SMTP : 1025

UI : 8025

Lancement du projet
1. Lancer MailHog (terminal 1)
bash
C:\MailHog\MailHog_windows_amd64.exe
2. Lancer le backend (FastAPI) — terminal 2
bash
# Depuis la racine du projet
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
Swagger UI :
http://127.0.0.1:8000/docs

3. Lancer le frontend
Arborescence :

Code
frontend/
   index.html
   script.js
   style.css
Méthodes possibles :

Ouvrir directement frontend/index.html

Ou utiliser un serveur local (ex. Live Server dans VS Code)

Ou lancer un serveur simple :

bash
cd frontend
python -m http.server 5500
Frontend accessible sur :
http://127.0.0.1:5500 (127.0.0.1 in Bing)

Ports utilisés (récapitulatif)
Backend FastAPI : http://127.0.0.1:8000

MailHog SMTP : 127.0.0.1:1025

MailHog UI : http://127.0.0.1:8025

Ollama API : http://127.0.0.1:11434

Tests rapides
Test de l’envoi d’email via Swagger
Ouvrir : http://127.0.0.1:8000/docs

Endpoint : POST /send-email

Exemple de corps JSON :

json
{
  "recipient_email": "test@example.com",
  "conversation_history": [
    { "role": "user", "content": "Bonjour", "timestamp": "2026-01-15T13:15:00" },
    { "role": "assistant", "content": "Salut Aude", "timestamp": "2026-01-15T13:15:05" }
  ],
  "subject": "Conversation DIXITBOT"
}
Vérifier l’email dans MailHog :
http://127.0.0.1:8025