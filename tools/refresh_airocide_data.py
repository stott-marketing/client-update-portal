from __future__ import annotations

import json
import subprocess
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "airocide"
CONFIG = Path.home() / ".config" / "stott-marketing"
CONSOLIDATION_START = date(2026, 4, 1)

AIROCIDE = {
    "display_name": "Airocide Systems",
    "google_profile": "stott-primary",
    "ga4_property_id": "534063449",
    "additional_ga4_properties": {
        "corporate_or_legacy": "529871368",
        "dealer_portal": "533070374",
    },
    "search_atlas_domain": "airocide.com",
    "search_console_site_url": "https://www.airocide.com/",
}


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict | None = None,
) -> dict:
    data = None
    request_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=request_headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def request_json_curl(url: str, *, headers: dict[str, str] | None = None) -> dict:
    cmd = ["curl", "-sS"]
    for key, value in (headers or {}).items():
        cmd.extend(["-H", f"{key}: {value}"])
    cmd.append(url)
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout or "{}")


def save(name: str, data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def google_access_token(profile: str) -> str:
    token_path = CONFIG / "google-data" / "tokens" / f"{profile}.json"
    client_path = CONFIG / "ga4-oauth-client.json"
    token = json.loads(token_path.read_text(encoding="utf-8"))
    client = json.loads(client_path.read_text(encoding="utf-8"))
    client_data = client.get("installed") or client.get("web") or client
    payload = urllib.parse.urlencode(
        {
            "client_id": client_data["client_id"],
            "client_secret": client_data["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["access_token"]


def refresh_ga4_property(access_token: str, property_id: str, start: str, end: str) -> dict:
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "metrics": [
            {"name": "activeUsers"},
            {"name": "sessions"},
            {"name": "newUsers"},
            {"name": "engagementRate"},
            {"name": "keyEvents"},
            {"name": "totalRevenue"},
            {"name": "ecommercePurchases"},
            {"name": "totalPurchasers"},
        ],
    }
    raw = request_json(url, method="POST", headers={"Authorization": f"Bearer {access_token}"}, body=body)
    values = [v.get("value") for v in raw.get("rows", [{}])[0].get("metricValues", [])]
    keys = [
        "active_users",
        "sessions",
        "new_users",
        "engagement_rate",
        "key_events",
        "total_revenue",
        "ecommerce_purchases",
        "total_purchasers",
    ]
    return {
        "property_id": property_id,
        "period": {"start": start, "end": end},
        "metrics": dict(zip(keys, values)),
        "raw": raw,
    }


def refresh_ga4_channels(access_token: str, property_id: str, start: str, end: str) -> dict:
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": [{"name": "sessionDefaultChannelGroup"}],
        "metrics": [
            {"name": "sessions"},
            {"name": "activeUsers"},
            {"name": "keyEvents"},
            {"name": "totalRevenue"},
            {"name": "ecommercePurchases"},
        ],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
        "limit": 12,
    }
    return request_json(url, method="POST", headers={"Authorization": f"Bearer {access_token}"}, body=body)


def refresh_ga4_report(
    access_token: str,
    property_id: str,
    start: str,
    end: str,
    *,
    dimensions: list[str],
    metrics: list[str],
    limit: int = 100,
    order_metric: str | None = None,
) -> dict:
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": [{"name": dimension} for dimension in dimensions],
        "metrics": [{"name": metric} for metric in metrics],
        "limit": limit,
    }
    if order_metric:
        body["orderBys"] = [{"metric": {"metricName": order_metric}, "desc": True}]
    return request_json(url, method="POST", headers={"Authorization": f"Bearer {access_token}"}, body=body)


def refresh_ga4_hostname_breakout(access_token: str, property_id: str, start: str, end: str) -> dict:
    return {
        "period": {"start": start, "end": end},
        "property_id": property_id,
        "hostname_totals": refresh_ga4_report(
            access_token,
            property_id,
            start,
            end,
            dimensions=["hostName"],
            metrics=[
                "sessions",
                "activeUsers",
                "keyEvents",
                "totalRevenue",
                "ecommercePurchases",
                "totalPurchasers",
            ],
            limit=50,
            order_metric="sessions",
        ),
        "hostname_events": refresh_ga4_report(
            access_token,
            property_id,
            start,
            end,
            dimensions=["hostName", "eventName"],
            metrics=["eventCount", "totalUsers", "totalRevenue"],
            limit=200,
            order_metric="eventCount",
        ),
        "hostname_pages": refresh_ga4_report(
            access_token,
            property_id,
            start,
            end,
            dimensions=["hostName", "pagePath"],
            metrics=["screenPageViews", "activeUsers", "keyEvents", "totalRevenue"],
            limit=300,
            order_metric="screenPageViews",
        ),
    }


def refresh_search_console(access_token: str, start: str, end: str) -> dict:
    base = "https://www.googleapis.com/webmasters/v3/sites/"
    site = urllib.parse.quote(AIROCIDE["search_console_site_url"], safe="")
    url = f"{base}{site}/searchAnalytics/query"
    headers = {"Authorization": f"Bearer {access_token}"}
    common = {"startDate": start, "endDate": end}
    summary = request_json(
        url,
        method="POST",
        headers=headers,
        body={**common, "rowLimit": 1},
    )
    queries = request_json(
        url,
        method="POST",
        headers=headers,
        body={
            **common,
            "dimensions": ["query"],
            "rowLimit": 10,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "descending"}],
        },
    )
    pages = request_json(
        url,
        method="POST",
        headers=headers,
        body={
            **common,
            "dimensions": ["page"],
            "rowLimit": 10,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "descending"}],
        },
    )
    return {
        "period": {"start": start, "end": end},
        "site_url": AIROCIDE["search_console_site_url"],
        "summary": summary,
        "queries": queries,
        "pages": pages,
    }


def extract_search_atlas_project(project: dict) -> dict:
    se = ((project.get("data_v2") or {}).get("se") or {})
    legacy_se = ((project.get("data") or {}).get("se") or {})
    sa = ((project.get("data_v2") or {}).get("sa") or {})
    otto = ((project.get("data_v2") or {}).get("otto_v2") or {})
    llm = ((project.get("data_v2") or {}).get("llmv") or {})
    keyword_trend = se.get("organic_keywords_trend") or legacy_se.get("organic_keywords_trend") or []
    traffic_trend = se.get("organic_traffic_trend") or legacy_se.get("organic_traffic_trend") or []
    return {
        "project_id": project.get("id"),
        "domain": project.get("domain_url"),
        "ai_summary": project.get("ai_summary"),
        "organic_keywords_trend": keyword_trend,
        "organic_traffic_trend": traffic_trend,
        "metrics": {
            "site_health": sa.get("health"),
            "domain_power": se.get("domain_power"),
            "domain_rating": se.get("domain_rating"),
            "domain_authority": se.get("domain_authority"),
            "organic_traffic": se.get("organic_traffic") or se.get("traffic"),
            "traffic_change": se.get("traffic_change"),
            "traffic_change_percent": se.get("traffic_change_percent"),
            "keyword_count": se.get("keyword_count") or se.get("organic_keywords"),
            "keyword_count_change": se.get("keyword_count_change"),
            "keyword_count_change_percent": se.get("keyword_count_change_percent"),
            "top_3_keywords_count": se.get("top_3_keywords_count"),
            "refdomain_count": se.get("refdomain_count") or se.get("refdomains"),
            "refdomain_new_count": se.get("refdomain_new_count"),
            "refdomain_lost_count": se.get("refdomain_lost_count"),
            "backlinks": se.get("backlinks"),
            "spam_score": se.get("spam_score"),
            "otto_score": otto.get("seo_optimization_score"),
            "otto_total_deployed_fixes": otto.get("total_deployed_fixes"),
            "otto_total_time_saved": otto.get("total_time_saved"),
            "llm_current_mentions": llm.get("current_mentions"),
            "llm_previous_mentions": llm.get("previous_mentions"),
        },
    }


def refresh_search_atlas() -> dict:
    key = read_text(CONFIG / "search-atlas" / "tokens" / "search-atlas-key.txt")
    data = request_json_curl("https://api.searchatlas.com/api/customer/projects/projects/", headers={"X-API-Key": key})
    projects = data.get("results") or data.get("data") or []
    by_domain = {project.get("domain_url"): project for project in projects}
    domain = AIROCIDE["search_atlas_domain"]
    if domain not in by_domain:
        raise RuntimeError(f"Search Atlas project not found for {domain}")
    return {
        "source": "search_atlas_api",
        "domain": extract_search_atlas_project(by_domain[domain]),
    }


def main() -> None:
    today = date.today()
    end = today - timedelta(days=1)
    start = CONSOLIDATION_START
    ytd_start = date(today.year, 1, 1)
    access_token = google_access_token(AIROCIDE["google_profile"])

    refresh_summary = {
        "client_slug": "airocide-systems",
        "client_name": AIROCIDE["display_name"],
        "domain": AIROCIDE["search_atlas_domain"],
        "brand_consolidation_start": CONSOLIDATION_START.isoformat(),
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "ytd_period": {"start": ytd_start.isoformat(), "end": end.isoformat()},
        "sources": {
            "ga4": "connected",
            "meta_ads": "available_but_not_used",
            "search_atlas": "connected_read_only",
            "google_ads": "not_configured",
            "search_console": "connected",
        },
    }

    main_ga4 = refresh_ga4_property(access_token, AIROCIDE["ga4_property_id"], start.isoformat(), end.isoformat())
    main_ga4_ytd = refresh_ga4_property(access_token, AIROCIDE["ga4_property_id"], ytd_start.isoformat(), end.isoformat())
    ga4_channels = refresh_ga4_channels(access_token, AIROCIDE["ga4_property_id"], start.isoformat(), end.isoformat())
    ga4_hostname = refresh_ga4_hostname_breakout(
        access_token,
        AIROCIDE["ga4_property_id"],
        start.isoformat(),
        end.isoformat(),
    )
    additional = {
        name: refresh_ga4_property(access_token, property_id, start.isoformat(), end.isoformat())
        for name, property_id in AIROCIDE["additional_ga4_properties"].items()
    }
    search_console = refresh_search_console(access_token, start.isoformat(), end.isoformat())
    atlas = refresh_search_atlas()

    save("refresh_summary.json", refresh_summary)
    save("ga4.json", main_ga4)
    save("ga4_ytd.json", main_ga4_ytd)
    save("ga4_channels.json", {"period": refresh_summary["period"], "rows": ga4_channels.get("rows") or [], "raw": ga4_channels})
    save("ga4_hostname.json", ga4_hostname)
    save("ga4_additional.json", additional)
    save("search_console.json", search_console)
    save("search_atlas.json", atlas)
    print(json.dumps(refresh_summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
