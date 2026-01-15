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

Ce projet est un **agent conversationnel intelligent** développé dans le cadre du projet IA BOT qui génère des réponses via Ollama (Qwen3).
Il repose sur une architecture en **4 couches** :
- Frontend (web app)
- Backend Python (API REST)
- Serveur MCP (tooling)
- Modèle IA local (Ollama)

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

## ⚙️ Installation (environnement local)

### 1️⃣ Prérequis

- Systeme exploitation Windows 10, 11, IOS sequoia 15.7.3 
- Python 3.13.7
- Git Hub 
- Connexion Internet (pour le scraping et le téléchargement du modèle)

---
### 2️⃣ Création d’un environnement virtuel (venv)
Un venv isole les dépendances Python du projet (évite de polluer Python global).

Commandes recommandées (Windows PowerShell) :

# Depuis la racine du projet
py -m venv .venv
.\.venv\Scripts\Activate.ps1

---
3️⃣ Installer les dépendances Python
pip install -r requirements.txt

---

### 3️⃣ Installer Ollama (obligatoire)


Ollama est utilisé pour exécuter un **modèle de langage open-source en local**.

👉 Télécharger et installer Ollama pour Windows :  
https://ollama.com/download/windows

Après installation, redémarrer VS Code ou le terminal, puis vérifier :

```bash
ollama --version
ollama version is 0.14.1
ollama pull qwen3 1.7B

5️⃣ Installer MailHog (pour module Email)

MailHog sert de “boîte mail de test” locale.

✅ Version recommandée : MailHog 1.0.1
Fichier Windows : MailHog_windows_amd64.exe (pour Windows 64-bit)

👉 Téléchargement : https://github.com/AudeC22/DIXITBOT.git

Lancement (exemple) :

# Exemple si le fichier est dans C:\MailHog\
C:\MailHog\MailHog_windows_amd64.exe


Puis ouvrir l’UI :

http://127.0.0.1:8025

ℹ️ Ports MailHog :

1025 = SMTP (réception des emails de test)

8025 = UI web (boîte de réception)

▶️ Lancer le projet
1) Lancer MailHog (terminal 1)
C:\MailHog\MailHog_windows_amd64.exe

2) Lancer l’API FastAPI (terminal 2)

Depuis la racine :

.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000


Swagger UI :

http://127.0.0.1:8000/docs

ℹ️ Le port 8000 n’est pas une “version FastAPI” : c’est juste le port réseau utilisé par Uvicorn.

3) Lancer le frontend

❓ TODO : comment se lance le frontend ?

fichier HTML direct ?

serveur local (Live Server VSCode) ?

npm / vite / autre ?

🔌 Ports utilisés (récapitulatif)

FastAPI (Uvicorn) : http://127.0.0.1:8000

MailHog SMTP : 127.0.0.1:1025

MailHog UI : http://127.0.0.1:8025

Ollama API : http://127.0.0.1:11434

🧪 Tests rapides
Test Email via Swagger

Aller sur : http://127.0.0.1:8000/docs

Endpoint : POST /send-email

Exemple body :

{
  "recipient_email": "test@example.com",
  "conversation_history": [
    { "role": "user", "content": "Bonjour", "timestamp": "2026-01-15T13:15:00" },
    { "role": "assistant", "content": "Salut Aude 👋", "timestamp": "2026-01-15T13:15:05" }
  ],
  "subject": "Conversation DIXITBOT"
}


Voir l’email dans MailHog : http://127.0.0.1:8025

🛠️ Problèmes courants (Windows)
1) “Python n’est pas reconnu”

Utiliser :

py --version
py -m uvicorn app.main:app --reload --port 8000

2) “Port déjà utilisé”

Changer le port :

python -m uvicorn app.main:app --reload --port 8001

