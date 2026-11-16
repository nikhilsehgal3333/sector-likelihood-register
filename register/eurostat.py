"""Fetch Eurostat datasets (JSON-stat 2.0) and keep a local copy so results can be reproduced.

Data source: Eurostat dissemination API. Reuse is allowed with attribution (CC BY 4.0).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def fetch(dataset: str, name: str, refresh: bool = False, **filters: str) -> dict:
    """Return the JSON-stat document for `dataset`. Use the local copy unless `refresh` is set."""
    path = RAW / f"{name}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    query = urllib.parse.urlencode({"format": "JSON", "lang": "EN", **filters})
    url = f"{API}{dataset}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "python-urllib"})
    with urllib.request.urlopen(request, timeout=60) as response:
        doc = json.load(response)
    doc["_retrieved"] = date.today().isoformat()
    doc["_url"] = url
    RAW.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return doc


def cells(doc: dict) -> dict[tuple[str, ...], tuple[float, str]]:
    """Map each (code per dimension) tuple to (value, status flag). Empty cells are left out."""
    dims = doc["id"]
    sizes = doc["size"]
    codes = []
    for dim in dims:
        index = doc["dimension"][dim]["category"]["index"]
        codes.append(sorted(index, key=index.get))
    strides = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    status = doc.get("status", {})
    out = {}
    for key, value in doc["value"].items():
        flat = int(key)
        parts = []
        for i in range(len(dims)):
            parts.append(codes[i][(flat // strides[i]) % sizes[i]])
        out[tuple(parts)] = (float(value), status.get(key, ""))
    return out


def labels(doc: dict, dim: str) -> dict[str, str]:
    return dict(doc["dimension"][dim]["category"]["label"])


def meta(doc: dict) -> str:
    return f"Eurostat, updated {doc.get('updated', '?')[:10]}, retrieved {doc.get('_retrieved', '?')}"
