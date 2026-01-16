import os
import time
import requests
from typing import Any, Dict, Optional


class OllamaClient:
    """
    Minimal Ollama HTTP client.
    Default endpoint: http://127.0.0.1:11434
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_s: float = 60.0,
        min_interval_s: float = 1.0,  # rate limit: 1 req/s
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or "llama3"
        self.timeout_s = float(timeout_s)
        self.min_interval_s = float(min_interval_s)

        self._last_call_ts = 0.0

    def _throttle(self) -> None:
        now = time.time()
        elapsed = now - self._last_call_ts
        if elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)
        self._last_call_ts = time.time()

    def tags(self) -> Dict[str, Any]:
        """List locally available models."""
        url = f"{self.base_url}/api/tags"
        r = requests.get(url, timeout=self.timeout_s)
        r.raise_for_status()
        return r.json()

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        num_predict: int = 600,
        model: Optional[str] = None,
    ) -> str:
        """
        Calls Ollama /api/generate (non-stream).
        Returns the generated text.
        """
        self._throttle()

        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        if system:
            payload["system"] = system

        try:
            r = requests.post(url, json=payload, timeout=self.timeout_s)
        except requests.RequestException as e:
            raise RuntimeError(f"Ollama unreachable at {self.base_url} ({e})")

        if r.status_code != 200:
            # show concise error
            raise RuntimeError(f"Ollama error {r.status_code}: {r.text}")

        data = r.json()
        return (data.get("response") or "").strip()
