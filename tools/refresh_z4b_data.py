from __future__ import annotations

import json
import csv
import subprocess
import urllib.parse
import urllib.request
import os
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "z4b"
CONFIG = Path.home() / ".config" / "stott-marketing"

Z4B = {
    "domain": "zincsforboats.com",
    "ga4_property_id": "255281532",
    "google_profile": "stott-primary",
    "search_console_site_url": "https://zincsforboats.com/",
    "search_atlas_domain": "zincsforboats.com",
    "google_ads_customer_id": "4994545253",
}

SHOPIFY_API_VERSION = "2026-07"
SHOPIFY_ALL_TIME_START = "2000-01-01"
GOOGLE_ADS_EXPORT = (
    Path.home()
    / "Library/CloudStorage/OneDrive-stott.marketing/Clients/Z4B/Google Ads/Search keyword report (1).csv"
)


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


def request_json_curl(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict | None = None,
) -> dict:
    cmd = ["curl", "-sS", "-X", method]
    for key, value in (headers or {}).items():
        cmd.extend(["-H", f"{key}: {value}"])
    if body is not None:
        cmd.extend(["-H", "Content-Type: application/json", "--data-binary", json.dumps(body)])
    cmd.append(url)
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout or "{}")


def save(name: str, data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def shopify_config() -> dict:
    env_shop = os.getenv("Z4B_SHOPIFY_SHOP") or os.getenv("SHOPIFY_SHOP")
    env_token = os.getenv("Z4B_SHOPIFY_ACCESS_TOKEN") or os.getenv("SHOPIFY_ACCESS_TOKEN")
    if env_shop and env_token:
        return {"shop": env_shop, "access_token": env_token, "source": "environment"}

    candidates = [
        CONFIG / "shopify" / "tokens" / "z4b.json",
        CONFIG / "shopify" / "tokens" / "zincsforboats.json",
        CONFIG / "z4b" / "shopify.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        shop = data.get("shop") or data.get("store") or data.get("shop_domain")
        token = data.get("access_token") or data.get("admin_access_token") or data.get("token")
        if shop and token:
            if token.startswith("shpss_"):
                raise ValueError(
                    "Shopify credential looks like an API secret key, not an Admin API access token. "
                    "Use the token that starts with shpat_."
                )
            return {"shop": shop, "access_token": token, "source": str(path)}
    raise FileNotFoundError(
        "No Shopify credentials found. Expected env Z4B_SHOPIFY_SHOP and "
        "Z4B_SHOPIFY_ACCESS_TOKEN, or ~/.config/stott-marketing/shopify/tokens/z4b.json."
    )


def normalize_shop_domain(shop: str) -> str:
    shop = shop.strip().removeprefix("https://").removeprefix("http://").strip("/")
    if "." not in shop:
        return f"{shop}.myshopify.com"
    return shop


def shopify_graphql(shop: str, access_token: str, query: str, variables: dict | None = None) -> dict:
    domain = normalize_shop_domain(shop)
    url = f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    body = {"query": query, "variables": variables or {}}
    data = request_json(
        url,
        method="POST",
        headers={
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        },
        body=body,
    )
    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"], sort_keys=True))
    return data


def amount(money_bag: dict | None) -> float:
    return float((((money_bag or {}).get("shopMoney") or {}).get("amount")) or 0)


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


def parse_float(value: object) -> float:
    text = str(value or "0").replace(",", "").replace("%", "").replace("--", "0").strip()
    try:
        return float(text or 0)
    except ValueError:
        return 0.0


def refresh_ga4(access_token: str, start: str, end: str) -> dict:
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{Z4B['ga4_property_id']}:runReport"
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
    return {"period": {"start": start, "end": end}, "metrics": dict(zip(keys, values)), "raw": raw}


def refresh_ga4_channels(access_token: str, start: str, end: str) -> dict:
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{Z4B['ga4_property_id']}:runReport"
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


def refresh_search_console(access_token: str, start: str, end: str) -> dict:
    base = "https://www.googleapis.com/webmasters/v3/sites/"
    site = urllib.parse.quote(Z4B["search_console_site_url"], safe="")
    url = f"{base}{site}/searchAnalytics/query"
    headers = {"Authorization": f"Bearer {access_token}"}
    summary = request_json(
        url,
        method="POST",
        headers=headers,
        body={"startDate": start, "endDate": end, "rowLimit": 1},
    )
    queries = request_json(
        url,
        method="POST",
        headers=headers,
        body={
            "startDate": start,
            "endDate": end,
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
            "startDate": start,
            "endDate": end,
            "dimensions": ["page"],
            "rowLimit": 10,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "descending"}],
        },
    )
    return {"period": {"start": start, "end": end}, "summary": summary, "queries": queries, "pages": pages}


def refresh_search_atlas() -> dict:
    key = read_text(CONFIG / "search-atlas" / "tokens" / "search-atlas-key.txt")
    data = request_json_curl("https://api.searchatlas.com/api/customer/projects/projects/", headers={"X-API-Key": key})
    projects = data.get("results") or data.get("data") or []
    project = next((p for p in projects if p.get("domain_url") == Z4B["search_atlas_domain"]), None)
    if not project:
        raise RuntimeError("Search Atlas project not found for zincsforboats.com")
    se = ((project.get("data_v2") or {}).get("se") or {})
    sa = ((project.get("data_v2") or {}).get("sa") or {})
    otto = ((project.get("data_v2") or {}).get("otto_v2") or {})
    llm = ((project.get("data_v2") or {}).get("llmv") or {})
    return {
        "project_id": project.get("id"),
        "domain": project.get("domain_url"),
        "ai_summary": project.get("ai_summary"),
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


def refresh_google_ads_export() -> dict:
    if not GOOGLE_ADS_EXPORT.exists():
        raise FileNotFoundError(f"Google Ads export not found: {GOOGLE_ADS_EXPORT}")

    rows = list(csv.DictReader(GOOGLE_ADS_EXPORT.open(encoding="utf-8-sig")))
    totals = Counter()
    by_ad_group: dict[str, Counter] = {}
    by_keyword = []
    for row in rows:
        ad_group = row.get("Ad group") or "Unknown"
        metrics = {
            "cost": parse_float(row.get("Cost")),
            "clicks": parse_float(row.get("Clicks")),
            "impressions": parse_float(row.get("Impr.")),
            "conversions": parse_float(row.get("Conversions")),
            "conversion_value": parse_float(row.get("Conv. value")),
        }
        for key, value in metrics.items():
            totals[key] += value
        ad_group_counter = by_ad_group.setdefault(ad_group, Counter())
        for key, value in metrics.items():
            ad_group_counter[key] += value
        if metrics["cost"] or metrics["clicks"] or metrics["impressions"] or metrics["conversion_value"]:
            by_keyword.append(
                {
                    "keyword": row.get("Keyword") or "",
                    "match_type": row.get("Match type") or "",
                    "ad_group": ad_group,
                    "status": row.get("Status") or "",
                    **metrics,
                }
            )

    cost = totals["cost"]
    conversions = totals["conversions"]
    conversion_value = totals["conversion_value"]
    metrics = {
        "cost": cost,
        "clicks": totals["clicks"],
        "impressions": totals["impressions"],
        "conversions": conversions,
        "conversion_value": conversion_value,
        "avg_cpc": cost / totals["clicks"] if totals["clicks"] else 0,
        "cost_per_conversion": cost / conversions if conversions else 0,
        "conversion_rate": conversions / totals["clicks"] if totals["clicks"] else 0,
        "reported_roas": conversion_value / cost if cost else 0,
    }
    return {
        "source": "local_google_ads_keyword_export",
        "source_file": str(GOOGLE_ADS_EXPORT),
        "period": "export_period_unknown",
        "metrics": metrics,
        "top_ad_groups": [
            {
                "ad_group": name,
                "cost": values["cost"],
                "clicks": values["clicks"],
                "impressions": values["impressions"],
                "conversions": values["conversions"],
                "conversion_value": values["conversion_value"],
                "reported_roas": values["conversion_value"] / values["cost"] if values["cost"] else 0,
            }
            for name, values in sorted(by_ad_group.items(), key=lambda item: item[1]["cost"], reverse=True)[:8]
        ],
        "top_keywords": sorted(by_keyword, key=lambda item: item["cost"], reverse=True)[:12],
    }


def google_ads_headers(access_token: str, *, login_customer_id: str | None = None) -> dict[str, str]:
    ads_config = json.loads((CONFIG / "google-data" / "google-ads.json").read_text(encoding="utf-8"))
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": ads_config["developer_token"],
    }
    if login_customer_id:
        headers["login-customer-id"] = login_customer_id.replace("-", "")
    return headers


def google_ads_search(access_token: str, customer_id: str, query: str) -> list[dict]:
    raw = request_json_curl(
        f"https://googleads.googleapis.com/v21/customers/{customer_id}/googleAds:searchStream",
        method="POST",
        headers=google_ads_headers(access_token),
        body={"query": query},
    )
    if isinstance(raw, dict) and raw.get("error"):
        raise RuntimeError(json.dumps(raw["error"], sort_keys=True))
    rows = []
    for batch in raw if isinstance(raw, list) else []:
        rows.extend(batch.get("results", []))
    return rows


def refresh_google_ads_api(access_token: str, start: str, end: str) -> dict:
    customer_id = Z4B.get("google_ads_customer_id")
    if not customer_id:
        return refresh_google_ads_export()

    summary_query = f"""
      SELECT
        customer.id,
        customer.descriptive_name,
        customer.currency_code,
        customer.status,
        metrics.cost_micros,
        metrics.clicks,
        metrics.impressions,
        metrics.conversions,
        metrics.conversions_value
      FROM customer
      WHERE segments.date BETWEEN '{start}' AND '{end}'
    """
    ad_group_query = f"""
      SELECT
        ad_group.name,
        metrics.cost_micros,
        metrics.clicks,
        metrics.impressions,
        metrics.conversions,
        metrics.conversions_value
      FROM ad_group
      WHERE segments.date BETWEEN '{start}' AND '{end}'
      ORDER BY metrics.cost_micros DESC
      LIMIT 12
    """
    keyword_query = f"""
      SELECT
        ad_group.name,
        ad_group_criterion.keyword.text,
        ad_group_criterion.keyword.match_type,
        metrics.cost_micros,
        metrics.clicks,
        metrics.impressions,
        metrics.conversions,
        metrics.conversions_value
      FROM keyword_view
      WHERE segments.date BETWEEN '{start}' AND '{end}'
        AND metrics.impressions > 0
      ORDER BY metrics.cost_micros DESC
      LIMIT 12
    """
    summary_rows = google_ads_search(access_token, customer_id, summary_query)
    summary = summary_rows[0] if summary_rows else {}
    summary_metrics = summary.get("metrics") or {}
    customer = summary.get("customer") or {}

    cost = int(float(summary_metrics.get("costMicros", 0) or 0)) / 1_000_000
    clicks = float(summary_metrics.get("clicks", 0) or 0)
    impressions = float(summary_metrics.get("impressions", 0) or 0)
    conversions = float(summary_metrics.get("conversions", 0) or 0)
    conversion_value = float(summary_metrics.get("conversionsValue", 0) or 0)

    def row_metrics(row: dict) -> dict:
        metrics = row.get("metrics") or {}
        row_cost = int(float(metrics.get("costMicros", 0) or 0)) / 1_000_000
        row_clicks = float(metrics.get("clicks", 0) or 0)
        row_conversions = float(metrics.get("conversions", 0) or 0)
        row_conversion_value = float(metrics.get("conversionsValue", 0) or 0)
        return {
            "cost": row_cost,
            "clicks": row_clicks,
            "impressions": float(metrics.get("impressions", 0) or 0),
            "conversions": row_conversions,
            "conversion_value": row_conversion_value,
            "reported_roas": row_conversion_value / row_cost if row_cost else 0,
        }

    return {
        "source": "google_ads_api",
        "customer": customer,
        "period": {"start": start, "end": end},
        "metrics": {
            "cost": cost,
            "clicks": clicks,
            "impressions": impressions,
            "conversions": conversions,
            "conversion_value": conversion_value,
            "avg_cpc": cost / clicks if clicks else 0,
            "cost_per_conversion": cost / conversions if conversions else 0,
            "conversion_rate": conversions / clicks if clicks else 0,
            "reported_roas": conversion_value / cost if cost else 0,
        },
        "top_ad_groups": [
            {
                "ad_group": (row.get("adGroup") or {}).get("name") or "Unknown",
                **row_metrics(row),
            }
            for row in google_ads_search(access_token, customer_id, ad_group_query)
        ],
        "top_keywords": [
            {
                "keyword": ((row.get("adGroupCriterion") or {}).get("keyword") or {}).get("text") or "",
                "match_type": ((row.get("adGroupCriterion") or {}).get("keyword") or {}).get("matchType") or "",
                "ad_group": (row.get("adGroup") or {}).get("name") or "Unknown",
                **row_metrics(row),
            }
            for row in google_ads_search(access_token, customer_id, keyword_query)
        ],
    }


def refresh_shopify(start: str, end: str, ytd_start: str, period_ranges: dict[str, dict[str, str]] | None = None) -> dict:
    config = shopify_config()
    shop = config["shop"]
    token = config["access_token"]
    query = """
      query Orders($first: Int!, $after: String, $search: String!) {
        shop {
          name
          myshopifyDomain
          primaryDomain { url }
          currencyCode
        }
        orders(first: $first, after: $after, query: $search, sortKey: CREATED_AT) {
          pageInfo { hasNextPage endCursor }
          edges {
            node {
              id
              name
              createdAt
              displayFinancialStatus
              displayFulfillmentStatus
              currentTotalPriceSet { shopMoney { amount currencyCode } }
              currentSubtotalPriceSet { shopMoney { amount currencyCode } }
              totalShippingPriceSet { shopMoney { amount currencyCode } }
              lineItems(first: 50) {
                edges {
                  node {
                    title
                    quantity
                    sku
                    originalTotalSet { shopMoney { amount currencyCode } }
                  }
                }
              }
            }
          }
        }
      }
    """

    def collect(period_start: str, period_end: str) -> dict:
        after = None
        orders = []
        search = f"created_at:>={period_start} created_at:<={period_end}"
        while True:
            raw = shopify_graphql(
                shop,
                token,
                query,
                {"first": 100, "after": after, "search": search},
            )
            orders_data = ((raw.get("data") or {}).get("orders") or {})
            orders.extend(edge.get("node") or {} for edge in orders_data.get("edges") or [])
            page_info = orders_data.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                shop_data = (raw.get("data") or {}).get("shop") or {}
                break
            after = page_info.get("endCursor")

        product_revenue: Counter[str] = Counter()
        product_quantity: Counter[str] = Counter()
        status_counts = Counter()
        weekday_orders: Counter[str] = Counter()
        weekday_revenue: Counter[str] = Counter()
        revenue = 0.0
        subtotal = 0.0
        shipping = 0.0
        for order in orders:
            status_counts[order.get("displayFinancialStatus") or "UNKNOWN"] += 1
            order_revenue = amount(order.get("currentTotalPriceSet"))
            revenue += order_revenue
            subtotal += amount(order.get("currentSubtotalPriceSet"))
            shipping += amount(order.get("totalShippingPriceSet"))
            created_at = order.get("createdAt") or ""
            if created_at:
                weekday = datetime.fromisoformat(created_at.replace("Z", "+00:00")).strftime("%A")
                weekday_orders[weekday] += 1
                weekday_revenue[weekday] += order_revenue
            for edge in ((order.get("lineItems") or {}).get("edges") or []):
                item = edge.get("node") or {}
                title = item.get("title") or item.get("sku") or "Unknown product"
                product_quantity[title] += int(item.get("quantity") or 0)
                product_revenue[title] += amount(item.get("originalTotalSet"))

        actual_start = period_start
        if period_start == SHOPIFY_ALL_TIME_START and orders:
            created_dates = [str(order.get("createdAt") or "")[:10] for order in orders if order.get("createdAt")]
            if created_dates:
                actual_start = min(created_dates)

        return {
            "period": {"start": actual_start, "end": period_end},
            "shop": shop_data,
            "metrics": {
                "orders": len(orders),
                "revenue": revenue,
                "subtotal": subtotal,
                "shipping": shipping,
                "average_order_value": revenue / len(orders) if orders else 0,
                "financial_status": dict(status_counts.most_common()),
            },
            "top_products": [
                {
                    "title": title,
                    "quantity": product_quantity[title],
                    "revenue": product_revenue[title],
                }
                for title, _ in product_revenue.most_common(10)
            ],
            "weekday_sales": [
                {
                    "weekday": weekday,
                    "orders": weekday_orders[weekday],
                    "revenue": weekday_revenue[weekday],
                }
                for weekday in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
            ],
        }

    current = collect(start, end)
    ytd = collect(ytd_start, end)
    periods = {
        key: collect(period["start"], period["end"])
        for key, period in (period_ranges or {}).items()
    }
    periods.setdefault("last_30", current)
    periods.setdefault("this_year", ytd)
    return {
        "api_version": SHOPIFY_API_VERSION,
        "credential_source": config["source"],
        "current": current,
        "ytd": ytd,
        "periods": periods,
    }


def refresh_access_status() -> dict:
    shopify_candidates = [
        CONFIG / "shopify" / "tokens" / "z4b.json",
        CONFIG / "shopify" / "tokens" / "zincsforboats.json",
        CONFIG / "z4b" / "shopify.json",
    ]
    return {
        "shopify": {
            "status": "pending"
            if not (
                any(path.exists() for path in shopify_candidates)
                or (os.getenv("Z4B_SHOPIFY_SHOP") and os.getenv("Z4B_SHOPIFY_ACCESS_TOKEN"))
                or (os.getenv("SHOPIFY_SHOP") and os.getenv("SHOPIFY_ACCESS_TOKEN"))
            )
            else "configured",
            "checked_paths": [str(path) for path in shopify_candidates],
            "env_supported": ["Z4B_SHOPIFY_SHOP", "Z4B_SHOPIFY_ACCESS_TOKEN"],
        },
        "google_ads": {
            "status": "api_configured" if Z4B.get("google_ads_customer_id") else ("export_available" if GOOGLE_ADS_EXPORT.exists() else "pending"),
            "note": "Google Ads API customer ID is configured for Z4B; local export remains available as fallback.",
            "customer_id": Z4B.get("google_ads_customer_id"),
            "export_path": str(GOOGLE_ADS_EXPORT),
        },
    }


def main() -> None:
    today = date.today()
    end = today - timedelta(days=3)
    start = end - timedelta(days=29)
    last_7_start = end - timedelta(days=6)
    this_month_start = date(today.year, today.month, 1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = date(last_month_end.year, last_month_end.month, 1)
    ytd_start = date(today.year, 1, 1)
    last_year_start = date(today.year - 1, 1, 1)
    last_year_end = date(today.year - 1, 12, 31)
    start_s = start.isoformat()
    end_s = end.isoformat()
    ytd_start_s = ytd_start.isoformat()
    shopify_period_ranges = {
        "last_7": {"start": last_7_start.isoformat(), "end": end_s},
        "last_30": {"start": start_s, "end": end_s},
        "last_month": {"start": last_month_start.isoformat(), "end": last_month_end.isoformat()},
        "this_year": {"start": ytd_start_s, "end": end_s},
        "last_year": {"start": last_year_start.isoformat(), "end": last_year_end.isoformat()},
        "all_time": {"start": SHOPIFY_ALL_TIME_START, "end": end_s},
    }
    summary = {
        "period": {"start": start_s, "end": end_s},
        "ytd_period": {"start": ytd_start_s, "end": end_s},
        "shopify_periods": shopify_period_ranges,
        "refreshed": {},
    }

    google_token_cache: str | None = None

    def get_google_token() -> str:
        nonlocal google_token_cache
        if google_token_cache is None:
            google_token_cache = google_access_token(Z4B["google_profile"])
        return google_token_cache

    tasks = {
        "ga4.json": lambda: refresh_ga4(get_google_token(), start_s, end_s),
        "ga4_ytd.json": lambda: refresh_ga4(get_google_token(), ytd_start_s, end_s),
        "ga4_channels.json": lambda: refresh_ga4_channels(get_google_token(), start_s, end_s),
        "search_console.json": lambda: refresh_search_console(get_google_token(), start_s, end_s),
        "search_atlas.json": refresh_search_atlas,
        "shopify.json": lambda: refresh_shopify(start_s, end_s, ytd_start_s, shopify_period_ranges),
        "google_ads.json": lambda: refresh_google_ads_api(get_google_token(), start_s, end_s),
        "access_status.json": refresh_access_status,
    }

    for name, fn in tasks.items():
        try:
            data = fn()
            save(name, data)
            summary["refreshed"][name] = "ok"
        except Exception as exc:
            summary["refreshed"][name] = f"{type(exc).__name__}: {exc}"
    save("refresh_summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
