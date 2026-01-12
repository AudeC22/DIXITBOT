# DIXITBOT
Création d'un chat IA BOT dans le cadre d'un Projet Epitech Groupe 34 

# 🤖 DIXITBOT — Agent conversationnel intelligent

Ce projet est un **agent conversationnel intelligent** développé dans le cadre du projet IA BOT.
Il repose sur une architecture en **4 couches** :
- Frontend (web app)
- Backend Python (API REST)
- Serveur MCP (tooling)
- Modèle IA local (Ollama)

---

## 🧱 Architecture (vue d’ensemble)

- **Frontend** : HTML / CSS / JavaScript  
- **Backend** : Python + FastAPI  
- **IA locale** : Ollama + modèle `qwen2.5:1.5b`  
- **Tooling** : scraping de données publiques (site cell.com)  
- **Communication** : API REST  

## Flux agentique

1. L’utilisateur envoie une requête via l’interface web
2. Le backend analyse l’intention
3. La mémoire et la knowledge base sont consultées
4. Si l’information est insuffisante, un tool MCP est déclenché
5. Le tool effectue un scraping ciblé
6. Les données sont analysées par le modèle IA local (Ollama)
7. Une réponse contextualisée est retournée à l’utilisateur

## ⚙️ Installation (environnement local)

### 1️⃣ Prérequis

- Windows 10 ou 11  
- Python 3.10 ou plus  
- Git  
- Connexion Internet (pour le scraping et le téléchargement du modèle)

---

### 2️⃣ Installer Ollama (obligatoire)

Ollama est utilisé pour exécuter un **modèle de langage open-source en local**.

👉 Télécharger et installer Ollama pour Windows :  
https://ollama.com/download/windows

Après installation, redémarrer VS Code ou le terminal, puis vérifier :

```bash
ollama --version


