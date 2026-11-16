"""Minimal client for a local model server with an OpenAI-compatible API (for example llama.cpp).

The model runs on the local machine. No report text leaves the machine.
Set LLM_URL to use a different server.
"""
from __future__ import annotations

import json
import os
import urllib.request

URL = os.environ.get("LLM_URL", "http://127.0.0.1:8091")


def chat(system: str, user: str, schema: dict, max_tokens: int = 500, seed: int = 1) -> dict:
    """Return the JSON answer of the model. The server forces the answer to follow `schema`."""
    body = {
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
        "seed": seed,
        "max_tokens": max_tokens,
        "cache_prompt": True,
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "answer", "strict": True, "schema": schema}},
    }
    request = urllib.request.Request(URL + "/v1/chat/completions",
                                     data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=900) as response:
        answer = json.load(response)
    return json.loads(answer["choices"][0]["message"]["content"])


def model_name() -> str:
    with urllib.request.urlopen(URL + "/v1/models", timeout=30) as response:
        return json.load(response)["data"][0]["id"]
