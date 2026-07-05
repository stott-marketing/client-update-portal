from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from facebook_ads_api import fetch_ad_account_insights, read_token


ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path.home() / ".config" / "stott-marketing"
OUT = ROOT / "data" / "facebook_ads"
CLIENT_CONFIG = CONFIG / "meta-data" / "facebook_ads_clients.json"


def safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value.strip().lower()).strip("-")


def load_clients() -> list[dict[str, Any]]:
    env_config = os.getenv("PUNCH_FACEBOOK_ADS_CLIENTS_JSON") or os.getenv("FACEBOOK_ADS_CLIENTS_JSON")
    if env_config:
        data = json.loads(env_config)
        clients = data.get("clients") if isinstance(data, dict) else data
        if not isinstance(clients, list):
            raise ValueError("Facebook Ads client env config must be a list or an object with a clients list.")
        return clients

    if not CLIENT_CONFIG.exists():
        return []
    data = json.loads(CLIENT_CONFIG.read_text(encoding="utf-8"))
    clients = data.get("clients") if isinstance(data, dict) else data
    if not isinstance(clients, list):
        raise ValueError("Facebook Ads client config must be a list or an object with a clients list.")
    return clients


def output_name(client: dict[str, Any]) -> str:
    client_slug = safe_slug(client["client_slug"])
    child_slug = safe_slug(client.get("child_client_slug") or "")
    account_slug = safe_slug(str(client.get("ad_account_id") or "").removeprefix("act_"))
    parts = [client_slug]
    if child_slug:
        parts.append(child_slug)
    if account_slug:
        parts.append(account_slug)
    return "__".join(parts) + ".json"


def refresh_client(client: dict[str, Any], start: str, end: str) -> dict[str, Any]:
    token = read_token(client.get("token_name") or "michaelrstott")
    insight = fetch_ad_account_insights(
        ad_account_id=client["ad_account_id"],
        access_token=token,
        start=start,
        end=end,
        api_version=client.get("api_version") or "v23.0",
    )
    return {
        "client_slug": client["client_slug"],
        "client_name": client.get("client_name") or client.get("display_name") or client["client_slug"],
        "child_client_slug": client.get("child_client_slug") or "",
        "child_client_name": client.get("child_client_name") or "",
        "source": "meta_ads_api",
        **insight,
    }


def main() -> None:
    today = date.today()
    end = today - timedelta(days=1)
    start = end - timedelta(days=29)
    start_s = start.isoformat()
    end_s = end.isoformat()
    OUT.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "period": {"start": start_s, "end": end_s},
        "config": str(CLIENT_CONFIG),
        "refreshed": {},
    }

    client_slug_filter = safe_slug(os.getenv("FACEBOOK_ADS_CLIENT_SLUG_FILTER") or "")
    clients = load_clients()
    if client_slug_filter:
        clients = [
            client
            for client in clients
            if safe_slug(str(client.get("client_slug") or "")) == client_slug_filter
        ]
    if not clients:
        summary["status"] = "pending"
        summary["reason"] = (
            f"No Facebook Ads client config is mapped for {client_slug_filter}."
            if client_slug_filter
            else "No Facebook Ads client config is mapped yet."
        )
    if client_slug_filter:
        summary["client_slug_filter"] = client_slug_filter

    for client in clients:
        name = output_name(client)
        try:
            data = refresh_client(client, start_s, end_s)
            (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
            summary["refreshed"][name] = "ok"
        except Exception as exc:
            summary["refreshed"][name] = f"{type(exc).__name__}: {exc}"

    (OUT / "refresh_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
