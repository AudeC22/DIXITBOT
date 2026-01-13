# ============================================================  # # 📌 Début du script
# 🕷️ arXiv Scraper (search/cs) -> JSON + sauvegarde data_lake/raw  # # 🎯 Objectif du script
# ============================================================  # # 📌 Séparateur visuel

import os  # # 📁 Gérer les chemins et dossiers
import re  # # 🔎 Extraire des infos via regex (ID, dates, versions)
import json  # # 🧾 Exporter en JSON
import time  # # ⏱️ Pause polie entre requêtes
import random  # # 🎲 Jitter pour éviter un rythme trop "robot"
import datetime  # # 🕒 Générer timestamps pour fichiers
from typing import Dict, Any, List, Optional  # # 🧩 Typage pour clarté
import requests  # # 🌐 Faire des requêtes HTTP GET
from bs4 import BeautifulSoup  # # 🍲 Parser HTML et sélectionner des balises

ARXIV_BASE = "https://arxiv.org"  # # 🌍 Domaine arXiv
ARXIV_SEARCH_CS = "https://arxiv.org/search/cs"  # # 🔎 Endpoint recherche Computer Science

DEFAULT_RAW_DIR = os.path.join("data_lake", "raw")  # # 📦 Dossier de stockage raw
DEFAULT_META_DIR = os.path.join("data_lake", "metadata")  # # 🧾 Dossier metadata sources

MAX_RESULTS_HARD_LIMIT = 100  # # 🚧 Limite globale demandée (max 100)
PAGE_SIZE = 50  # # 📄 arXiv permet size=50 en général (pratique pour paginer)
