"""LLM wrapper.

Default: OpenRouter (because the starter project already used it).

Env vars:
  OPENROUTER_API_KEY   Required to use OpenRouter.
  OPENROUTER_MODEL     Optional (default set in code).
  OPENROUTER_BASE_URL  Optional (default https://openrouter.ai/api/v1)

If the API key is missing, the app will return a helpful, non-LLM fallback.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import requests


load_dotenv()


DEFAULT_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "alibaba/tongyi-deepresearch-30b-a3b:free",
)


def chat(
    *,
    system: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.4,
    max_tokens: int = 650,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Send a chat completion request.

    Returns a dict: {"ok": bool, "content": str, "raw": any}
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return {
            "ok": False,
            "content": (
                "LLM is not configured (missing OPENROUTER_API_KEY). "
                "I can still show you data and calculations, but I can't generate narrative advice yet."
            ),
            "raw": None,
        }

    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    url = f"{base_url.rstrip('/')}/chat/completions"

    payload: Dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra:
        payload.update(extra)

    r = requests.post(
        url=url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
        timeout=45,
    )

    try:
        data = r.json()
    except Exception:
        return {"ok": False, "content": f"LLM error: HTTP {r.status_code}", "raw": r.text}

    if r.status_code >= 400:
        msg = data.get("error", {}).get("message") if isinstance(data, dict) else None
        return {"ok": False, "content": f"LLM error: HTTP {r.status_code} {msg or ''}".strip(), "raw": data}

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        content = "LLM returned an unexpected response format."

    return {"ok": True, "content": content, "raw": data}
