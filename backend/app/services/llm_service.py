from __future__ import annotations

from typing import Any, Dict
import requests


def ollama_generate(prompt: str, model: str = "qwen3:1.7b", timeout_s: int = 180) -> str:
    url = "http://localhost:11434/api/generate"
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip()
