# module_Email/conversation_store.py

import os
import json
import datetime
from typing import List, Dict, Any

def _now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")

def _default_base_dir(project_root: str) -> str:
    return os.path.join(project_root, "data_lake", "raw", "conversations")

def load_history(session_id: str, project_root: str) -> List[Dict[str, Any]]:
    base_dir = _default_base_dir(project_root)
    os.makedirs(base_dir, exist_ok=True)
    path = os.path.join(base_dir, f"conv_{session_id}.json")

    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def append_message(session_id: str, project_root: str, role: str, content: str) -> str:
    history = load_history(session_id=session_id, project_root=project_root)

    history.append({
        "role": role,
        "content": content,
        "timestamp": _now_iso(),
    })

    base_dir = _default_base_dir(project_root)
    os.makedirs(base_dir, exist_ok=True)
    path = os.path.join(base_dir, f"conv_{session_id}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return path  # renvoie le chemin du fichier sauvegardé

def get_history(session_id: str, project_root: str) -> List[Dict[str, Any]]:
    return load_history(session_id=session_id, project_root=project_root)
