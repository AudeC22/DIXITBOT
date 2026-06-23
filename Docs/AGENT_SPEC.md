# AGENT SPECIFICATION — Agent de Recherche Scientifique

## Nom du projet

Dixit – Agent IA de Recherche Scientifique

## Version

v1.0

## Responsable architecture

Amine (Lead Agent / Architecture)

## Mission de l’agent

L’agent a pour mission d’aider les utilisateurs à rechercher, filtrer, résumer et comparer des articles scientifiques accessibles publiquement sur Internet, à partir de sources fiables et ouvertes.

L’agent raisonne avant d’agir, consulte sa base de connaissances, et utilise des outils externes uniquement lorsque cela est nécessaire.

## Ce que l’agent sait faire

- Comprendre une requête de recherche scientifique en langage naturel
- Proposer des mots-clés et stratégies de recherche
- Identifier des articles scientifiques pertinents
- Extraire des métadonnées publiques (titre, auteurs, année, résumé, lien)
- Résumer un article scientifique
- Comparer plusieurs articles (objectif, méthode, limites)
- Expliquer ses choix et ses limites

## Ce que l’agent ne fait pas

- Contourner des paywalls ou des systèmes d’authentification
- Accéder à des bases de données privées ou payantes
- Collecter ou traiter des données personnelles sensibles
- Garantir l’exhaustivité totale des publications existantes
- Fournir un avis scientifique expert ou médical

## Sources autorisées (publiques)

- arXiv (prépublications)
- Semantic Scholar (index académique)
- PubMed (biomédical)
- OpenAlex (métadonnées scientifiques)
- DOAJ (revues open access)
- Sites institutionnels ou universitaires publics

## Types d’intentions utilisateur

### Intentions sociales

Exemples : "bonjour", "merci", "tu peux m'aider ?"
Traitement : réponse directe sans appel à un outil externe

### Intentions métier (recherche scientifique)

Exemples : "trouve des articles sur le RAG", "résume cet article", "compare ces deux papiers"
Traitement : KB → décision tool/no-tool → synthèse

## Règles fondamentales de l’agent

- La Knowledge Base est toujours consultée en priorité
- Un outil externe est utilisé uniquement si une information manque
- Le modèle de langage n’est jamais utilisé pour décider, uniquement pour raisonner et rédiger
- Les outils retournent des données structurées, jamais du contenu brut

## Contraintes techniques

- Maximum 3 appels d’outils par requête utilisateur
- Maximum 5 résultats affichés par recherche
- Maximum 1 à 2 requêtes simultanées
- Priorité donnée à la qualité plutôt qu’à la quantité

## Positionnement du projet

L’interface utilisateur prend la forme d’un chatbot, mais l’intelligence repose sur une architecture d’agent IA.
L’agent analyse, décide, puis agit de manière contrôlée avant de produire une réponse raisonnée.
