# ARCHITECTURE — Agent IA Dixit

## Objectif

Ce document décrit l’architecture technique et fonctionnelle
de l’agent IA Dixit.

Il explique comment les différents composants interagissent
pour former un agent décisionnel capable de rechercher et
d’analyser des articles scientifiques, tout en respectant
des contraintes de puissance, d’éthique et de lisibilité.

## Vue d’ensemble

L’architecture repose sur une séparation claire des responsabilités :

- Le Frontend gère l’interface utilisateur
- Le Backend orchestre les décisions
- La Knowledge Base fournit les connaissances statiques
- Le serveur MCP encapsule les outils
- Les Tools exécutent des actions ciblées
- Le modèle LLM (via Ollama) raisonne et rédige les réponses

## Schéma logique global

Utilisateur
↓
Frontend (Chat UI)
↓
API REST — Backend (FastAPI, Orchestrateur)
├─→ Knowledge Base (KB)
│ (connaissances statiques, règles)
│
├─→ MCP Server
│ ↓
│ Tools (Scraping scientifique)
│ ↓
│ Données structurées
│
└─→ Ollama (LLM local)
↓
Réponse raisonnée
↓
Frontend

### Frontend (Interface utilisateur)

Responsabilités :

- Afficher l’interface de type chatbot
- Envoyer les requêtes utilisateur à l’API backend
- Afficher les réponses, états de chargement et erreurs

Contraintes :

- Aucune logique décisionnelle
- Aucune communication directe avec les outils ou le LLM

### Backend (API REST / Orchestrateur)

Responsabilités :

- Recevoir les requêtes utilisateur
- Classifier l’intention (sociale / métier)
- Consulter la Knowledge Base
- Décider s’il faut utiliser un outil
- Appeler le serveur MCP
- Appeler Ollama pour le raisonnement et la rédaction
- Gérer l’historique, les erreurs et les logs

### Knowledge Base (KB)

Rôle :

- Stocker les connaissances statiques
- Définir les règles métier
- Fournir des définitions, stratégies et templates de réponse

Exemples de contenu :

- Définitions (preprint, revue, survey)
- Sources fiables
- Règles tool / no-tool
- Formats de réponse

### MCP Server (Model Context Protocol)

Rôle :

- Fournir une interface standardisée vers les outils
- Séparer la décision de l’exécution
- Encapsuler les appels aux tools

Caractéristiques :

- Appelé uniquement par le backend
- Ne contient aucune logique décisionnelle

### Tools (Scraping scientifique)

Rôle :

- Exécuter des tâches ciblées :
  - recherche d’articles
  - extraction de métadonnées
- Retourner des données structurées

Contraintes :

- Sources publiques uniquement
- Pas de login ou paywall
- Appels limités pour préserver les ressources

### Modèle de langage (LLM via Ollama)

Rôle :

- Analyser la demande utilisateur
- Résumer et comparer des données
- Générer une réponse claire et structurée

Contraintes :

- Ne décide jamais d’utiliser un outil
- Ne communique jamais directement avec les tools

## Flux agentique détaillé

1. L’utilisateur envoie une requête via le frontend
2. Le backend reçoit la requête
3. L’intention est classifiée
4. La Knowledge Base est consultée
5. Le backend décide :
   - réponse directe
   - ou appel à un outil via MCP
6. Si tool :
   - récupération de données structurées
7. Les données sont transmises au LLM
8. Le LLM produit une réponse raisonnée
9. La réponse est renvoyée au frontend

## Correspondance avec la structure du projet

backend/

- main.py : point d’entrée API
- core/ : logique agentique et décisionnelle

mcp/

- server.py : serveur MCP
- tools.py : déclaration des outils
- schemas.py : formats d’échange

scraping/

- scraping.py : implémentation des scrapers

kb/

- kb_science.json : base de connaissances

docs/

- AGENT_SPEC.md
- DECISION_RULES.md
- TOOLS_CONTRACTS.md
- ARCHITECTURE.md

## Contraintes globales

- Architecture pensée pour un environnement local
- Ressources limitées (CPU, RAM)
- Limitation des appels aux outils
- Priorité à la clarté et à l’explicabilité

## Conclusion

Cette architecture permet de construire un agent IA robuste,
explicable et contrôlé. La séparation claire entre décision,
exécution et raisonnement garantit que Dixit est un véritable
agent IA, et non un simple chatbot conversationnel.
