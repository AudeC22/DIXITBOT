import json
import os

# Paths

RAW_DIR = "data_lake/raw"
PROCESSED_DIR = "data_lake/processed"
OUTPUT_FILE = "arxiv_cleaned.json"

# Règles métier

DEFAULT_MISSING_MESSAGE = (
    "Information non disponible automatiquement. "
    "Veuillez consulter l’article original : "
)

MAX_ABSTRACT_LENGTH = 1200
MAX_PAPERS = 20

# Processing principal

def clean_arxiv_raw():
    raw_files = sorted(
        [f for f in os.listdir(RAW_DIR) if f.startswith("arxiv_raw_") and f.endswith(".json")]
    )

    if not raw_files:
        print("Aucun fichier raw trouvé")
        return

    latest_raw = raw_files[-1]
    raw_path = os.path.join(RAW_DIR, latest_raw)

    print(f"Lecture du fichier : {latest_raw}")

    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    cleaned_items = []

    for item in raw_data.get("items", []):
        title = (item.get("title") or "").strip()
        url = (item.get("abs_url") or "").strip()

        if not title:
            continue

        abstract = (item.get("abstract") or "").strip()
        if not abstract:
            abstract = DEFAULT_MISSING_MESSAGE + url
        else:
            abstract = abstract[:MAX_ABSTRACT_LENGTH]

        authors = item.get("authors") or ["Auteur non spécifié"]

        submitted_date = item.get("submitted_date") or "Date non disponible"

        cleaned_items.append({
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "submitted_date": submitted_date,
            "source_url": url
        })

        if len(cleaned_items) >= MAX_PAPERS:
            break

    final_data = {
        "source": "arXiv",
        "query": raw_data.get("query", ""),
        "count": len(cleaned_items),
        "papers": cleaned_items
    }

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    output_path = os.path.join(PROCESSED_DIR, OUTPUT_FILE)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"Processing terminé {output_path}")

# Test

if __name__ == "__main__":
    print("Démarrage du processing arXiv...")
    clean_arxiv_raw()