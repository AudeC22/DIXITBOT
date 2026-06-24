# DECISION RULES — Agent de Recherche Scientifique

## Objectif

Ce document décrit les règles de décision de l’agent IA Dixit.
Il précise dans quels cas l’agent répond directement à partir de la
Knowledge Base (KB) et dans quels cas il déclenche un outil externe
(scraping via MCP).

Ces règles permettent de garantir :

- une utilisation raisonnée des ressources
- une réponse pertinente et explicable
- une architecture d’agent (et non un simple chatbot)

## Règle actuelle

L'agent scrape arXiv si la Knowledge Base renvoie moins de 2 résultats
au-dessus du seuil de pertinence `kb_min_score`.

Implémentation : `backend/app/services/decision_service.py::should_scrape_arxiv()`.

## Paramètre configurable

- `min_relevant_count` (par défaut : `2`) — nombre minimal de résultats KB
  jugés suffisants pour répondre sans déclencher de scraping.

## Justification

- Éviter un scraping arXiv systématique et inutile lorsque la KB locale
  suffit déjà à répondre.
- Préserver la bande passante arXiv (service public, à usage raisonné).
- Respecter les pratiques éthiques de scraping documentées dans le projet
  (cf. `Docs/AGENT_SPEC.md`, contraintes techniques sur le nombre d'appels
  d'outils par requête).

## Limites connues

- Aucun scoring sémantique de pertinence : la décision repose uniquement
  sur un comptage du nombre de résultats KB retournés, pas sur la qualité
  ou la pertinence réelle de ces résultats.
- Un faux négatif est possible : si la KB renvoie 2 résultats peu
  pertinents, l'agent ne scrapera pas arXiv malgré une réponse de faible
  qualité.

## Évolution future

Voir `Docs/AGENT_SPEC.md` pour la roadmap (règles de décision plus fines,
scoring sémantique, etc.).
