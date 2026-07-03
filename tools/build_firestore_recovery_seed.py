from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "private-recovery" / "manage" / "updateEntries-backup-2026-06-27T03-46-09-786Z.json"
OUT = ROOT / "private-recovery" / "manage" / "firestore-recovery-seed-2026-06-27.json"
FIRESTORE_METADATA = {"id", "name", "createTime", "updateTime"}


def cleaned_document(source: dict) -> dict:
    return {
        key: value
        for key, value in source.items()
        if key not in FIRESTORE_METADATA
    }


def cleaned_update_entry(source: dict) -> dict:
    document = cleaned_document(source)
    if "recommendation_status" not in document:
        document["recommendation_status"] = "draft_saved" if document.get("recommended_response") else "needs_codex"
    return document


def main() -> None:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    documents = []

    portfolio = snapshot.get("workspacePortfolio")
    if not isinstance(portfolio, dict):
        raise ValueError("Snapshot is missing workspacePortfolio")
    documents.append({
        "path": "workspace/portfolio",
        "data": cleaned_document(portfolio),
    })

    update_entries = snapshot.get("updateEntries")
    if not isinstance(update_entries, list):
        raise ValueError("Snapshot is missing updateEntries")

    for entry in update_entries:
        if not isinstance(entry, dict) or not entry.get("id"):
            raise ValueError("Every update entry must include an id")
        documents.append({
            "path": f"updateEntries/{entry['id']}",
            "data": cleaned_update_entry(entry),
        })

    seed = {
        "source_snapshot": SNAPSHOT.name,
        "source_project": snapshot.get("source_project"),
        "exported_at": snapshot.get("exported_at"),
        "document_count": len(documents),
        "documents": documents,
    }

    OUT.write_text(json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(documents)} Firestore documents to {OUT}")


if __name__ == "__main__":
    main()
