# TOOLS CONTRACTS — Module MCP (Dixit)

## Vue d'ensemble

Dans ce projet, un "tool" est un module Python qui exécute une action ciblée
(typiquement : aller chercher des données structurées auprès d'une source
externe) et qui retourne toujours une réponse au format uniforme décrit
ci-dessous, jamais du contenu brut.

Conformément à la décision d'équipe (slide 09 du projet), "MCP" désigne ici
**un module d'outils structuré interne au backend**, pas le Model Context
Protocol d'Anthropic. Aucune dépendance `fastmcp`, aucun transport
stdio/JSON-RPC : un module Python classique (`backend/app/integrations/mcp/`)
avec des contrats d'entrée/sortie stricts, appelé directement par le backend
(`ask.py` via `mcp.run_tool(...)`).

La slide 09 décrit 3 niveaux de profondeur pour les tools de scraping
scientifique :
- **Niveau 1 (métadonnées)** : ID, Titre, Auteurs, Résumé, Date, Catégories, URLs
- **Niveau 2 (contexte)** : DOI, Historique des versions, Mises à jour
- **Niveau 3 (contenu profond)** : Méthodologie, Références

## Format générique

Tous les tools retournent une `ToolResponse` :

```
ToolResponse {
    tool: str            # nom du tool appelé, ex: "arxiv_metadata"
    ok: bool             # succès ou échec de l'exécution
    items: List[...]     # résultats structurés (vide si ok=False)
    scraped_at: str       # timestamp ISO 8601 UTC de l'exécution
    errors: List[str]    # messages d'erreur si ok=False (vide sinon)
}
```

Le dispatch se fait via `run_tool(name: str, params: Dict[str, Any]) -> ToolResponse`
(`backend/app/integrations/mcp/registry.py`), qui valide les `params` contre le
schéma Pydantic du tool demandé avant d'exécuter la fonction concrète.

## Tool implémenté : `arxiv_metadata` (Niveau 1)

Wrappe `backend/app/services/scrape_service.scrape_arxiv()`.

**Params (`ArxivMetadataParams`)** :
```
query: str
theme: Optional[str] = None
max_results: int = 8
sort: str = "relevance"
```

**Items (`ArxivMetadataItem`)** :
```
arxiv_id: str
title: str
authors: List[str]
abstract: str
submitted_date: str
categories: List[str] = []
abs_url: str
pdf_url: str
```

### Limitation connue : `categories` toujours vide en V1

Le champ `categories` du contrat `ArxivMetadataItem` est déclaré mais **reste
toujours vide (`[]`) dans cette version**. `scrape_service.scrape_arxiv()`
n'extrait pas le tag `<category>` de la réponse Atom XML d'arXiv — seul
`<author><name>` a été ajouté (cf. commit `feat(scrape): extract authors
field`). Ce n'est pas un bug : c'est une limitation assumée, documentée ici
pour rester honnête sur l'écart entre le contrat déclaré et les données
réellement disponibles. Roadmap V2 si un besoin réel d'afficher/filtrer par
catégorie est identifié (ajout de l'extraction `<category term="..."/>` dans
`scrape_service.py`).

## Tool implémenté : `send_email` (slide 10)

Wrappe `backend/app/services/email_service.send_email_smtp()`. Envoie
l'historique de conversation par email, via le serveur SMTP local Mailpit (remplaçant local de MailHog, abandonné depuis 2020)
(`SMTP_HOST`/`SMTP_PORT`, défaut `127.0.0.1:1025`).

**Params (`SendEmailParams`)** :
```
recipient_email: str
subject: str
conversation_history: List[Dict[str, str]]
# chaque élément attendu : {"role": ..., "content": ..., "timestamp": ...}
```

**Items** : ce tool ne retourne aucun item structuré (`items` reste toujours
`[]`, qu'il y ait succès ou échec). Il réutilise le même `ToolResponse` que
`arxiv_metadata` — seuls `ok`, `scraped_at` et `errors` sont pertinents ici.

**Comportement** :
- Construit un corps HTML simple (une ligne par message, pas de template
  engine).
- Sauvegarde une copie JSON de `conversation_history` dans
  `backend/data_lake/raw/conversation_history/` avant l'envoi.
- Envoie l'email via `smtplib` (stdlib), sans dépendance externe.

### Limitations connues

- Pas de pièce jointe : seulement du texte brut + HTML simple.
- Pas de vérification du format de l'adresse email côté backend (au-delà
  de la validation `str` de Pydantic) — une adresse mal formée échouera
  probablement côté serveur SMTP, pas avant.
- Conçu pour Mailpit (remplaçant local de MailHog, abandonné depuis 2020) en local ; aucune configuration TLS/authentification
  SMTP (non nécessaire pour un serveur de test local).

## Roadmap — non implémenté dans cette version

**Niveau 2 (contexte)** : `get_context(params: {"arxiv_id": str}) -> ToolResponse`
— DOI, historique des versions, dernière mise à jour. Nécessiterait de
scraper la page `/abs/<id>`, que l'API officielle arXiv ne fournit pas aussi
richement. Non implémenté : aucun consommateur actuel (KB, `ask.py`) n'en a
besoin.

**Niveau 3 (contenu profond)** : `get_deep_content(params: {"arxiv_id": str}) -> ToolResponse`
— méthodologie, références. Nécessiterait de scraper la page `/html/<id>`.
Non implémenté : effort de scraping conséquent, fragile, sans besoin
identifié à ce jour.

## Justification YAGNI

On implémente le strict nécessaire au cas d'usage actuel de `ask.py` (Niveau 1
uniquement, déjà câblé et suffisant pour répondre aux questions de recherche
scientifique avec citations). Les Niveaux 2 et 3 ne seront ajoutés que si un
besoin réel et concret se présente — pas de code spéculatif maintenu sans
consommateur.
