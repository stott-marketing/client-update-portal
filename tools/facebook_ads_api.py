from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


CONFIG = Path.home() / ".config" / "stott-marketing"
DEFAULT_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0")


def request_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def read_token(token_name: str = "michaelrstott") -> str:
    tokens_json = os.getenv("META_ACCESS_TOKENS_JSON") or os.getenv("FACEBOOK_ACCESS_TOKENS_JSON")
    if tokens_json:
        tokens = json.loads(tokens_json)
        if isinstance(tokens, dict) and tokens.get(token_name):
            return str(tokens[token_name]).strip()

    named_token_key = "".join(ch if ch.isalnum() else "_" for ch in token_name.upper())
    named_env_token = os.getenv(f"META_ACCESS_TOKEN_{named_token_key}") or os.getenv(
        f"FACEBOOK_ACCESS_TOKEN_{named_token_key}"
    )
    if named_env_token:
        return named_env_token.strip()

    env_token = os.getenv("META_ACCESS_TOKEN") or os.getenv("FACEBOOK_ACCESS_TOKEN")
    if env_token:
        return env_token.strip()

    token_path = CONFIG / "meta-data" / "tokens" / f"{token_name}.txt"
    if not token_path.exists():
        raise FileNotFoundError(
            f"No Meta access token found. Expected META_ACCESS_TOKEN env var or {token_path}."
        )
    return token_path.read_text(encoding="utf-8").strip()


def normalize_ad_account_id(ad_account_id: str) -> str:
    account = str(ad_account_id).strip()
    return account if account.startswith("act_") else f"act_{account}"


def parse_action_values(actions: list[dict[str, Any]] | None) -> dict[str, float]:
    values: dict[str, float] = {}
    for action in actions or []:
        action_type = action.get("action_type")
        if not action_type:
            continue
        try:
            values[action_type] = float(action.get("value", 0) or 0)
        except (TypeError, ValueError):
            values[action_type] = 0.0
    return values


def primary_leads(actions: dict[str, float]) -> float:
    lead_keys = [
        "lead",
        "onsite_conversion.lead_grouped",
        "onsite_conversion.messaging_conversation_started_7d",
        "offsite_conversion.fb_pixel_lead",
    ]
    return sum(actions.get(key, 0) for key in lead_keys)


def fetch_ad_account_insights(
    *,
    ad_account_id: str,
    access_token: str,
    start: str,
    end: str,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    account = normalize_ad_account_id(ad_account_id)
    fields = [
        "spend",
        "impressions",
        "clicks",
        "reach",
        "frequency",
        "cpc",
        "cpm",
        "ctr",
        "actions",
        "action_values",
        "purchase_roas",
    ]
    params = urllib.parse.urlencode(
        {
            "fields": ",".join(fields),
            "time_range": json.dumps({"since": start, "until": end}),
            "level": "account",
            "access_token": access_token,
        }
    )
    raw = request_json(f"https://graph.facebook.com/{api_version}/{account}/insights?{params}")
    row = (raw.get("data") or [{}])[0]
    actions = parse_action_values(row.get("actions"))
    action_values = parse_action_values(row.get("action_values"))
    purchase_roas = row.get("purchase_roas") or []
    roas_by_type = parse_action_values(purchase_roas if isinstance(purchase_roas, list) else [])

    spend = float(row.get("spend", 0) or 0)
    leads = primary_leads(actions)
    purchases = (
        actions.get("purchase", 0)
        or actions.get("omni_purchase", 0)
        or actions.get("offsite_conversion.fb_pixel_purchase", 0)
    )
    purchase_value = (
        action_values.get("purchase", 0)
        or action_values.get("omni_purchase", 0)
        or action_values.get("offsite_conversion.fb_pixel_purchase", 0)
    )

    return {
        "period": {"start": start, "end": end},
        "api_version": api_version,
        "ad_account_id": account,
        "metrics": {
            "spend": spend,
            "impressions": int(float(row.get("impressions", 0) or 0)),
            "clicks": int(float(row.get("clicks", 0) or 0)),
            "reach": int(float(row.get("reach", 0) or 0)),
            "frequency": float(row.get("frequency", 0) or 0),
            "cpc": float(row.get("cpc", 0) or 0),
            "cpm": float(row.get("cpm", 0) or 0),
            "ctr": float(row.get("ctr", 0) or 0),
            "leads": leads,
            "cost_per_lead": spend / leads if leads else 0,
            "link_clicks": actions.get("link_click", 0),
            "landing_page_views": actions.get("landing_page_view", 0),
            "video_views": actions.get("video_view", 0),
            "purchases": purchases,
            "purchase_value": purchase_value,
            "roas": purchase_value / spend if spend else 0,
            "reported_purchase_roas": max(roas_by_type.values()) if roas_by_type else 0,
        },
        "actions": actions,
        "action_values": action_values,
        "raw": raw,
    }


def combine_insights(records: list[dict[str, Any]]) -> dict[str, Any]:
    totals = Counter()
    weighted = Counter()
    for record in records:
        metrics = record.get("metrics") or {}
        spend = float(metrics.get("spend", 0) or 0)
        for key in [
            "spend",
            "impressions",
            "clicks",
            "reach",
            "leads",
            "link_clicks",
            "landing_page_views",
            "video_views",
            "purchases",
            "purchase_value",
        ]:
            totals[key] += float(metrics.get(key, 0) or 0)
        weighted["cpc"] += float(metrics.get("cpc", 0) or 0) * spend
        weighted["cpm"] += float(metrics.get("cpm", 0) or 0) * spend
        weighted["ctr"] += float(metrics.get("ctr", 0) or 0) * spend
        weighted["frequency"] += float(metrics.get("frequency", 0) or 0) * spend

    spend = totals["spend"]
    return {
        "spend": spend,
        "impressions": int(totals["impressions"]),
        "clicks": int(totals["clicks"]),
        "reach": int(totals["reach"]),
        "leads": totals["leads"],
        "cost_per_lead": spend / totals["leads"] if totals["leads"] else 0,
        "link_clicks": totals["link_clicks"],
        "landing_page_views": totals["landing_page_views"],
        "video_views": totals["video_views"],
        "purchases": totals["purchases"],
        "purchase_value": totals["purchase_value"],
        "roas": totals["purchase_value"] / spend if spend else 0,
        "cpc": weighted["cpc"] / spend if spend else 0,
        "cpm": weighted["cpm"] / spend if spend else 0,
        "ctr": weighted["ctr"] / spend if spend else 0,
        "frequency": weighted["frequency"] / spend if spend else 0,
    }
