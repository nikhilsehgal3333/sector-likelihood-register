"""Download the LkSG reports listed in corpus.csv and extract their text, page by page.

The reports are documents of the companies. This repository does not contain them. It stores only
the address, the download date and the SHA-256 value of each file in `corpus_lock.csv`.

    py ai/fetch_corpus.py <folder for the PDF files>
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
AGENT = "python-urllib (research download)"


def main() -> None:
    folder = Path(sys.argv[1])
    folder.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(HERE / "corpus.csv", encoding="utf-8")))
    lock = [["id", "sha256", "bytes", "pages", "retrieved", "status"]]
    for row in rows:
        pdf = folder / f"{row['id']}.pdf"
        status = "ok"
        if not pdf.exists():
            try:
                request = urllib.request.Request(row["url"], headers={"User-Agent": AGENT})
                with urllib.request.urlopen(request, timeout=90) as response:
                    body = response.read()
                if not body.startswith(b"%PDF"):
                    raise ValueError("not a PDF file")
                pdf.write_bytes(body)
            except Exception as error:  # the list must continue if one site refuses
                lock.append([row["id"], "", 0, 0, date.today().isoformat(), f"failed: {error}"])
                print(f"{row['id']}: failed ({error})")
                continue
        body = pdf.read_bytes()
        try:
            pages = [page.extract_text() or "" for page in PdfReader(str(pdf)).pages]
        except Exception as error:
            lock.append([row["id"], "", len(body), 0, date.today().isoformat(), f"unreadable: {error}"])
            print(f"{row['id']}: unreadable ({error})")
            continue
        (folder / f"{row['id']}.pages.json").write_text(json.dumps(pages, ensure_ascii=False),
                                                        encoding="utf-8")
        lock.append([row["id"], hashlib.sha256(body).hexdigest(), len(body), len(pages),
                     date.today().isoformat(), status])
        print(f"{row['id']}: {len(pages)} pages, {sum(len(p) for p in pages):,} characters")
    with open(HERE / "corpus_lock.csv", "w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(lock)


if __name__ == "__main__":
    main()
