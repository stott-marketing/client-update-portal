from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "data" / "sjawc" / "boulevard_revenue_match_summary.json"
DEFAULT_WORKBOOK = ROOT / "data" / "sjawc" / "workbook.json"
DEFAULT_PRIVATE_AUDIT = ROOT / "output" / "private" / "sjawc_boulevard_revenue_match_audit.csv"


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9 ]+", " ", text).lower()
    skip = {"jr", "sr", "ii", "iii", "iv"}
    return " ".join(part for part in text.split() if part not in skip)


def money(value: str | int | float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    text = re.sub(r"[^0-9.-]", "", str(value or ""))
    return Decimal(text or "0")


def as_float(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def split_tags(value: str) -> list[str]:
    return [tag.strip() for tag in re.split(r"[,;|]", value or "") if tag.strip()]


def classify_source(tags: list[str]) -> str:
    lower = [tag.lower() for tag in tags]
    if any("entitymed" in tag for tag in lower):
        return "entitymed"
    if any(tag == "facebook lead" or tag.startswith("fb -") or "facebook" in tag for tag in lower):
        return "meta"
    if any("contact form" in tag or "website" in tag for tag in lower):
        return "website_contact"
    if any(
        tag in {"boulevard", "new_appointment_zap", "new_appointment_staff_zap", "client_updated_zap"}
        or "appointment" in tag
        for tag in lower
    ):
        return "boulevard_existing_or_unknown"
    return "unattributed"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_workbook(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"known_summary": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def choose_contact(matches: list[dict[str, str]]) -> dict[str, str]:
    return max(matches, key=lambda row: row.get("Last Activity") or row.get("Created") or "")


def build_match(
    *,
    sales_rows: list[dict[str, str]],
    contact_rows: list[dict[str, str]],
    revenue_column: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    contacts_by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in contact_rows:
        full_name = f"{row.get('First Name', '')} {row.get('Last Name', '')}"
        normalized = normalize_name(full_name)
        if normalized:
            contacts_by_name[normalized].append(row)

    revenue_by_source: dict[str, Decimal] = defaultdict(Decimal)
    gross_by_source: dict[str, Decimal] = defaultdict(Decimal)
    net_by_source: dict[str, Decimal] = defaultdict(Decimal)
    buyers_by_source: Counter[str] = Counter()
    rows_by_source: Counter[str] = Counter()
    match_status: Counter[str] = Counter()
    audit_rows: list[dict[str, Any]] = []

    for row in sales_rows:
        normalized = normalize_name(row.get("Client name", ""))
        matches = contacts_by_name.get(normalized, [])
        source = "unmatched"
        match_type = "unmatched"
        matched_contact: dict[str, str] | None = None

        if matches:
            matched_contact = choose_contact(matches)
            source = classify_source(split_tags(matched_contact.get("Tags", "")))
            match_type = "exact_name_multi" if len(matches) > 1 else "exact_name"

        revenue = money(row.get(revenue_column, "0"))
        gross = money(row.get("Gross Sales", "0"))
        net = money(row.get("Net Sales", "0"))
        revenue_by_source[source] += revenue
        gross_by_source[source] += gross
        net_by_source[source] += net
        buyers_by_source[source] += 1
        rows_by_source[source] += 1
        match_status[match_type] += 1

        audit_rows.append(
            {
                "client_name": row.get("Client name", ""),
                "match_type": match_type,
                "source_bucket": source,
                "revenue": str(revenue),
                "gross_sales": str(gross),
                "net_sales": str(net),
                "matched_contact_id": (matched_contact or {}).get("Contact Id", ""),
                "matched_email": (matched_contact or {}).get("Email", ""),
                "matched_phone": (matched_contact or {}).get("Phone", ""),
                "matched_tags": (matched_contact or {}).get("Tags", ""),
            }
        )

    bucket_summary = {
        source: {
            "buyers": buyers_by_source[source],
            "rows": rows_by_source[source],
            "revenue": as_float(revenue_by_source[source]),
            "gross_sales": as_float(gross_by_source[source]),
            "net_sales": as_float(net_by_source[source]),
        }
        for source in sorted(revenue_by_source, key=lambda key: revenue_by_source[key], reverse=True)
    }

    total_revenue = sum(revenue_by_source.values(), Decimal("0"))
    matched_revenue = total_revenue - revenue_by_source.get("unmatched", Decimal("0"))
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "sales_file": "Client Sales.csv",
            "contacts_file": "Export_Contacts_undefined_Aug_2026_9_24_PM.csv",
            "revenue_column": revenue_column,
        },
        "row_counts": {
            "sales": len(sales_rows),
            "contacts": len(contact_rows),
        },
        "match_status": dict(match_status),
        "match_rate": {
            "sales_rows_matched": len(sales_rows) - match_status.get("unmatched", 0),
            "sales_rows_total": len(sales_rows),
            "percent": round(((len(sales_rows) - match_status.get("unmatched", 0)) / len(sales_rows) * 100), 1)
            if sales_rows
            else 0,
        },
        "totals": {
            "revenue": as_float(total_revenue),
            "matched_revenue": as_float(matched_revenue),
            "unmatched_revenue": as_float(revenue_by_source.get("unmatched", Decimal("0"))),
        },
        "source_buckets": bucket_summary,
        "attribution_note": (
            "Revenue is matched from Boulevard sales to GHL contacts by normalized client name. "
            "Source buckets are based on GHL tags and should be treated as confirmed only where tags explicitly support the source."
        ),
    }
    return summary, audit_rows


def update_workbook(workbook_path: Path, summary: dict[str, Any]) -> dict[str, Any]:
    workbook = load_workbook(workbook_path)
    known = workbook.setdefault("known_summary", {})
    buckets = summary["source_buckets"]

    meta = buckets.get("meta", {})
    entity = buckets.get("entitymed", {})
    website = buckets.get("website_contact", {})
    existing_unknown = buckets.get("boulevard_existing_or_unknown", {})
    unattributed = buckets.get("unattributed", {})
    unmatched = buckets.get("unmatched", {})

    known["meta_revenue"] = meta.get("revenue", 0)
    known["meta_buyers"] = meta.get("buyers", 0)
    known["entity_revenue"] = entity.get("revenue", 0)
    known["entity_buyers"] = entity.get("buyers", 0)
    known["boulevard_revenue_total"] = summary["totals"]["revenue"]
    known["boulevard_matched_revenue"] = summary["totals"]["matched_revenue"]
    known["boulevard_unmatched_revenue"] = summary["totals"]["unmatched_revenue"]
    known["website_contact_revenue"] = website.get("revenue", 0)
    known["boulevard_existing_or_unknown_revenue"] = existing_unknown.get("revenue", 0)
    known["unattributed_revenue"] = unattributed.get("revenue", 0)
    known["unmatched_revenue"] = unmatched.get("revenue", 0)

    if known.get("entity_spend"):
        known["entity_roas"] = round(float(known["entity_revenue"]) / float(known["entity_spend"]), 2)

    previous_meta_revenue = float(known.get("meta_revenue_previous_basis") or 3012.53)
    previous_meta_roas = float(known.get("meta_roas_previous_basis") or known.get("meta_roas") or 0)
    inferred_meta_spend = previous_meta_revenue / previous_meta_roas if previous_meta_roas else 0
    if inferred_meta_spend:
        known["meta_roas"] = round(float(known["meta_revenue"]) / inferred_meta_spend, 2)

    workbook["boulevard_revenue_match"] = summary
    return workbook


def write_private_audit(path: Path, audit_rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "client_name",
        "match_type",
        "source_bucket",
        "revenue",
        "gross_sales",
        "net_sales",
        "matched_contact_id",
        "matched_email",
        "matched_phone",
        "matched_tags",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Match SJAWC Boulevard sales revenue to GHL contact source tags.")
    parser.add_argument("--sales-csv", required=True, type=Path)
    parser.add_argument("--contacts-csv", required=True, type=Path)
    parser.add_argument("--revenue-column", default="Net Sales")
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY, type=Path)
    parser.add_argument("--workbook", default=DEFAULT_WORKBOOK, type=Path)
    parser.add_argument("--update-workbook", action="store_true")
    parser.add_argument("--private-audit", default=DEFAULT_PRIVATE_AUDIT, type=Path)
    parser.add_argument("--write-private-audit", action="store_true")
    args = parser.parse_args()

    sales_rows = read_csv(args.sales_csv)
    contact_rows = read_csv(args.contacts_csv)
    if sales_rows and args.revenue_column not in sales_rows[0]:
        raise ValueError(f"Revenue column not found in sales CSV: {args.revenue_column}")

    summary, audit_rows = build_match(
        sales_rows=sales_rows,
        contact_rows=contact_rows,
        revenue_column=args.revenue_column,
    )
    save_json(args.summary_output, summary)

    if args.update_workbook:
        save_json(args.workbook, update_workbook(args.workbook, summary))

    if args.write_private_audit:
        write_private_audit(args.private_audit, audit_rows)

    print(json.dumps({
        "summary_output": str(args.summary_output),
        "workbook_updated": bool(args.update_workbook),
        "private_audit_written": bool(args.write_private_audit),
        "match_rate": summary["match_rate"],
        "totals": summary["totals"],
        "source_buckets": summary["source_buckets"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
