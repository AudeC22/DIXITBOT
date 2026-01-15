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
- **Tooling** : 
Module : scraping de données publiques (site cell.com)  
    _ Le JSON = ton résultat structuré final (ce que tu veux exploiter).
    _ Le HTML = une copie brute du GET (preuve + debug).
        Ça sert à :
        vérifier que le scraping a bien récupéré la bonne page
        comprendre pourquoi un champ manque (sélecteur faux, page différente, etc.)
        garder une trace reproductible (consigne prof souvent appréciée)

Module Email :  Installer MailHog sur Windows
Option 1 : Installation simple (recommandé)

Téléchargez MailHog pour Windows : Mailhog 1.0.1 : MailHog_windows_amd64.exe

Allez sur : https://github.com/mailhog/MailHog/releases
Téléchargez MailHog_windows_amd64.exe

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


