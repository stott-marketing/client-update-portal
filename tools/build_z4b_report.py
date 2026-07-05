from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from public_update_renderer import add_posted_update_js, public_update_css, public_update_js_helpers


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "z4b"
OUT = ROOT / "firebase-static" / "public" / "zincs-for-boats"
LOGO_SOURCE = Path(
    "/Users/apple/Library/CloudStorage/GoogleDrive-mike@stott.marketing/.shortcut-targets-by-id/"
    "1g0HnTEV-N2e3DoBRh1afMx6wgi71w4DN/Shared Drive - Z4B/Images/zfb_logos/z4b-logo.png"
)
LOGO = OUT / "assets" / "z4b-logo.png"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_optional(name: str) -> dict:
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def money(value: float | int | str, digits: int = 0) -> str:
    number = float(value or 0)
    return f"${number:,.{digits}f}"


def compact_money(value: float | int | str) -> str:
    number = float(value or 0)
    if abs(number) >= 1_000_000:
        return f"${number / 1_000_000:.1f}M"
    if abs(number) >= 1_000:
        return f"${number / 1_000:.1f}K"
    return money(number, 0)


def number(value: float | int | str, digits: int = 0) -> str:
    number_value = float(value or 0)
    return f"{number_value:,.{digits}f}"


def pct(value: float | int | str, digits: int = 1) -> str:
    return f"{float(value or 0) * 100:.{digits}f}%"


def pct_plain(value: float | int | str, digits: int = 1) -> str:
    return f"{float(value or 0):.{digits}f}%"


def safe(value: object) -> str:
    return html.escape(str(value), quote=True)


def metric_values(row: dict) -> list[str]:
    return [item.get("value", "0") for item in row.get("metricValues", [])]


def channel_rows(channels: dict) -> list[dict[str, str]]:
    rows = []
    for row in channels.get("rows") or []:
        values = metric_values(row)
        rows.append(
            {
                "channel": ((row.get("dimensionValues") or [{}])[0].get("value") or "Unknown"),
                "sessions": values[0] if len(values) > 0 else "0",
                "active_users": values[1] if len(values) > 1 else "0",
                "key_events": values[2] if len(values) > 2 else "0",
                "revenue": values[3] if len(values) > 3 else "0",
                "purchases": values[4] if len(values) > 4 else "0",
            }
        )
    return rows


def search_rows(data: dict, key: str) -> list[dict]:
    return (data.get(key) or {}).get("rows") or []


def search_summary(sc: dict) -> dict:
    return ((sc.get("summary") or {}).get("rows") or [{}])[0]


def row_key(row: dict) -> str:
    return ((row.get("keys") or [""])[0] or "")


def public_updates_script(client_slug: str) -> str:
    return f"""
    <script type="module">
      import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/12.6.0/firebase-app.js";
      import {{
        collection,
        getDocs,
        getFirestore,
        orderBy,
        query
      }} from "https://www.gstatic.com/firebasejs/12.6.0/firebase-firestore.js";

      const firebaseConfig = {{
        apiKey: "AIzaSyDRpeu3P6qrbHQ69PsPjOdUZw0slbxTbsA",
        authDomain: "clients.stott.marketing",
        projectId: "stott-mktg-client-update-data",
        storageBucket: "stott-mktg-client-update-data.firebasestorage.app",
        messagingSenderId: "446049206946",
        appId: "1:446049206946:web:bab80b19302e5d03a58dfb",
        measurementId: "G-PFDY1X5S54"
      }};

      const app = initializeApp(firebaseConfig);
      const db = getFirestore(app);

      function showSection() {{
        document.querySelector("#posted-updates-section").hidden = false;
      }}

{public_update_js_helpers()}
{add_posted_update_js(show_section_call='showSection();')}

      function addMeetingTakeaway(text, completed) {{
        const list = document.querySelector("#dynamic-takeaways");
        const item = document.createElement("li");
        const box = document.createElement("span");
        box.className = "box";
        box.setAttribute("aria-hidden", "true");
        const label = document.createElement("span");
        label.textContent = text || "";
        if (completed) label.style.textDecoration = "line-through";
        item.append(box, label);
        list.append(item);
        showSection();
      }}

      async function loadPostedUpdates() {{
        try {{
          const snapshot = await getDocs(query(
            collection(db, "clientPublicUpdates", "{client_slug}", "items"),
            orderBy("posted_at", "asc")
          ));
          snapshot.forEach((documentSnapshot) => {{
            const entry = documentSnapshot.data();
            if (!entry.text) return;
            if (entry.entry_type === "meeting_takeaway") {{
              addMeetingTakeaway(entry.text, Boolean(entry.completed));
            }} else {{
              addPostedUpdate(entry.text);
            }}
          }});
        }} catch (error) {{
          console.error("Unable to load posted updates", error);
        }}
      }}

      loadPostedUpdates();
    </script>
"""


def page() -> str:
    refresh = load("refresh_summary.json")
    ga4 = load("ga4.json")
    ga4_ytd = load("ga4_ytd.json")
    channels = channel_rows(load("ga4_channels.json"))
    sc = load("search_console.json")
    atlas = load("search_atlas.json")
    access = load("access_status.json")
    shopify = load_optional("shopify.json")
    ads = load_optional("google_ads.json")

    period = refresh["period"]
    ytd_period = refresh["ytd_period"]
    ga = ga4["metrics"]
    ga_ytd = ga4_ytd["metrics"]
    se = atlas["metrics"]
    sc_summary = search_summary(sc)
    top_queries = search_rows(sc, "queries")[:5]
    top_pages = search_rows(sc, "pages")[:5]
    top_channel = channels[0] if channels else {"channel": "Cross-network", "revenue": 0, "purchases": 0}
    paid_search = next((row for row in channels if row["channel"] == "Paid Search"), None)
    organic = next((row for row in channels if row["channel"] == "Organic Search"), None)
    cross_network = next((row for row in channels if row["channel"] == "Cross-network"), None)
    llm_lift = 0
    if se.get("llm_current_mentions") and se.get("llm_previous_mentions"):
        previous = float(se["llm_previous_mentions"] or 0)
        llm_lift = ((float(se["llm_current_mentions"]) - previous) / previous * 100) if previous else 0
    shopify_status = (access.get("shopify") or {}).get("status") or "pending"
    ads_status = (access.get("google_ads") or {}).get("status") or "pending"
    shopify_current = (shopify.get("current") or {})
    shopify_ytd = (shopify.get("ytd") or {})
    shopify_metrics = shopify_current.get("metrics") or {}
    shopify_ytd_metrics = shopify_ytd.get("metrics") or {}
    shopify_connected = bool(shopify_metrics)
    shopify_products = shopify_current.get("top_products") or []
    shopify_weekday_sales = shopify_current.get("weekday_sales") or []
    ads_metrics = ads.get("metrics") or {}
    ads_connected = bool(ads_metrics)
    ads_source_label = "Google Ads export" if ads.get("source") == "local_google_ads_keyword_export" else "Google Ads API"
    ga_sessions = float(ga.get("sessions", 0) or 0)
    ga_purchases = float(ga.get("ecommerce_purchases", 0) or 0)
    ga_revenue = float(ga.get("total_revenue", 0) or 0)
    ga_conversion_rate = ga_purchases / ga_sessions if ga_sessions else 0
    ga_revenue_per_session = ga_revenue / ga_sessions if ga_sessions else 0
    max_channel_sessions = max([float(row["sessions"] or 0) for row in channels] or [1])
    top_sales_day = max(shopify_weekday_sales or [], key=lambda row: row.get("orders", 0), default={})
    top_revenue_day = max(shopify_weekday_sales or [], key=lambda row: row.get("revenue", 0), default={})
    if shopify_connected:
        revenue_headline = (
            f"{compact_money(shopify_metrics.get('revenue', 0))} in June Shopify revenue "
            f"from {number(shopify_metrics.get('orders', 0))} orders"
        )
        revenue_lede = (
            f"Zincs for Boats averaged {money(shopify_metrics.get('average_order_value', 0), 2)} per Shopify order "
            f"in June and has reached {compact_money(shopify_ytd_metrics.get('revenue', 0))} in Shopify revenue year to date. "
            f"{top_sales_day.get('weekday', 'Monday')} delivered the most sales volume with "
            f"{number(top_sales_day.get('orders', 0))} orders, while {top_revenue_day.get('weekday', 'Wednesday')} "
            f"led revenue with {money(top_revenue_day.get('revenue', 0), 2)}."
        )
        hero_revenue_value = money(shopify_metrics.get("revenue", 0), 0)
        hero_revenue_label = "June Shopify Revenue"
        hero_revenue_detail = "Store revenue source of truth"
        hero_orders_value = number(shopify_metrics.get("orders", 0))
        hero_orders_label = "June Orders"
        hero_orders_detail = f"{money(shopify_metrics.get('average_order_value', 0), 2)} average order value"
        hero_aov_value = money(shopify_metrics.get("average_order_value", 0), 2)
        hero_aov_label = "Average Order Value"
        hero_aov_detail = f"{number(shopify_ytd_metrics.get('orders', 0))} YTD Shopify orders"
        ytd_revenue_value = money(shopify_ytd_metrics.get("revenue", 0), 0)
        ytd_revenue_label = "YTD Shopify Revenue"
        ytd_revenue_detail = f"{number(shopify_ytd_metrics.get('orders', 0))} Shopify orders since Jan. 1"
    else:
        revenue_headline = "Shopify revenue is visible in GA4, with paid and organic channels both contributing."
        revenue_lede = (
            "This first Zincs for Boats report is built from the live data sources already connected: GA4, "
            "Google Search Console, and Search Atlas. Direct Shopify and Google Ads account access still need "
            "to be connected, so the current revenue view should be treated as GA4 ecommerce reporting rather "
            "than final Shopify financial reconciliation."
        )
        hero_revenue_value = money(ga["total_revenue"], 0)
        hero_revenue_label = "June GA4 Revenue"
        hero_revenue_detail = f"{number(ga['ecommerce_purchases'])} ecommerce purchases"
        hero_orders_value = number(ga["ecommerce_purchases"])
        hero_orders_label = "GA4 Purchases"
        hero_orders_detail = f"{number(ga['total_purchasers'])} purchasers"
        hero_aov_value = money(float(ga["total_revenue"] or 0) / float(ga["ecommerce_purchases"] or 1), 2)
        hero_aov_label = "GA4 Revenue / Purchase"
        hero_aov_detail = "Fallback until Shopify is connected"
        ytd_revenue_value = money(ga_ytd["total_revenue"], 0)
        ytd_revenue_label = "YTD GA4 Revenue"
        ytd_revenue_detail = f"{number(ga_ytd['ecommerce_purchases'])} purchases since Jan. 1"

    query_items = "\n".join(
        f"""
                <div class="table-row">
                  <span>{safe(row_key(row))}</span>
                  <strong>{number(row.get("clicks", 0))}</strong>
                  <strong>{number(row.get("impressions", 0))}</strong>
                  <strong>{pct(row.get("ctr", 0), 1)}</strong>
                  <strong>{number(row.get("position", 0), 1)}</strong>
                </div>"""
        for row in top_queries
    )
    page_items = "\n".join(
        f"""
                <div class="table-row page-row">
                  <span>{safe(row_key(row).replace("https://zincsforboats.com", "") or "/")}</span>
                  <strong>{number(row.get("clicks", 0))}</strong>
                  <strong>{number(row.get("impressions", 0))}</strong>
                  <strong>{number(row.get("position", 0), 1)}</strong>
                </div>"""
        for row in top_pages
    )
    channel_items = "\n".join(
        f"""
              <article class="channel">
                <span>{safe(row["channel"])}</span>
                <strong>{money(row["revenue"], 2)}</strong>
                <small>{number(row["sessions"])} sessions · {number(row["purchases"])} purchases</small>
              </article>"""
        for row in channels[:8]
    )
    analytics_bar_items = "\n".join(
        f"""
              <div class="analytics-row">
                <div class="analytics-label">
                  <strong>{safe(row["channel"])}</strong>
                  <span>{number(row["sessions"])} sessions</span>
                </div>
                <div class="analytics-track" aria-hidden="true"><span style="width: {max(4, min(100, float(row["sessions"] or 0) / max_channel_sessions * 100)):.1f}%"></span></div>
                <div class="analytics-values">
                  <strong>{money(row["revenue"], 0)}</strong>
                  <span>{number(row["purchases"])} purchases</span>
                </div>
              </div>"""
        for row in channels[:8]
    )
    product_items = "\n".join(
        f"""
                <div class="table-row page-row">
                  <span>{safe(product.get("title", "Unknown product"))}</span>
                  <strong>{number(product.get("quantity", 0))}</strong>
                  <strong>{money(product.get("revenue", 0), 2)}</strong>
                  <strong>{money(float(product.get("revenue", 0) or 0) / float(product.get("quantity", 1) or 1), 2)}</strong>
                </div>"""
        for product in shopify_products[:8]
    )
    weekday_lookup = {row.get("weekday"): row for row in shopify_weekday_sales}
    weekday_sales_items = "\n".join(
        f"""
            <article class="weekday-card">
              <h3>{safe(weekday)}</h3>
              <div class="weekday-split">
                <span>Sales</span>
                <strong>{number((weekday_lookup.get(weekday) or {}).get("orders", 0))}</strong>
              </div>
              <div class="weekday-split">
                <span>Revenue</span>
                <strong>{money((weekday_lookup.get(weekday) or {}).get("revenue", 0), 2)}</strong>
              </div>
            </article>"""
        for weekday in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    )
    ad_group_items = "\n".join(
        f"""
                <div class="table-row">
                  <span>{safe(row.get("ad_group", "Unknown"))}</span>
                  <strong>{money(row.get("cost", 0), 2)}</strong>
                  <strong>{number(row.get("clicks", 0))}</strong>
                  <strong>{number(row.get("conversions", 0), 1)}</strong>
                  <strong>{number(row.get("reported_roas", 0), 2)}x</strong>
                </div>"""
        for row in (ads.get("top_ad_groups") or [])[:8]
    )
    shopify_panel = (
        f"""
            <article class="panel revenue">
              <h3>Shopify store revenue</h3>
              <p>Direct Shopify reporting is connected and should now be treated as the store revenue source of truth for the report period.</p>
              <div class="stat-list">
                <div class="stat"><span>June Shopify revenue</span><strong>{money(shopify_metrics.get("revenue", 0), 2)}</strong></div>
                <div class="stat"><span>June orders</span><strong>{number(shopify_metrics.get("orders", 0))}</strong></div>
                <div class="stat"><span>Average order value</span><strong>{money(shopify_metrics.get("average_order_value", 0), 2)}</strong></div>
                <div class="stat"><span>YTD Shopify revenue</span><strong>{money(shopify_ytd_metrics.get("revenue", 0), 2)}</strong></div>
              </div>
            </article>"""
        if shopify_connected
        else f"""
            <article class="panel pending">
              <h3>Shopify and Ads access</h3>
              <p>Direct Shopify status is {safe(shopify_status)} and Google Ads status is {safe(ads_status)}. Once connected, this section should show actual store revenue, ad spend, ROAS, CPA, and product-level sales.</p>
              <div class="stat-list">
                <div class="stat"><span>Shopify financials</span><strong>Pending</strong></div>
                <div class="stat"><span>Google Ads spend</span><strong>Pending</strong></div>
                <div class="stat"><span>ROAS</span><strong>Pending</strong></div>
              </div>
            </article>"""
    )
    ads_panel_copy = (
        "Live Google Ads API data is now included for the connected Z4B customer."
        if ads.get("source") != "local_google_ads_keyword_export"
        else "Google Ads export data is now included while the API customer mapping is being finalized."
    )
    ads_panel = (
        f"""
            <article class="panel traffic">
              <h3>Google Ads performance</h3>
              <p>{safe(ads_panel_copy)}</p>
              <div class="stat-list">
                <div class="stat"><span>Spend</span><strong>{money(ads_metrics.get("cost", 0), 2)}</strong></div>
                <div class="stat"><span>Conversion value</span><strong>{money(ads_metrics.get("conversion_value", 0), 2)}</strong></div>
                <div class="stat"><span>Reported ROAS</span><strong>{number(ads_metrics.get("reported_roas", 0), 2)}x</strong></div>
                <div class="stat"><span>Conversions</span><strong>{number(ads_metrics.get("conversions", 0), 1)}</strong></div>
              </div>
            </article>"""
        if ads_connected
        else f"""
            <article class="panel pending">
              <h3>Google Ads access</h3>
              <p>Google Ads status is {safe(ads_status)}. Once connected, this section should show spend, conversion value, ROAS, CPA, and campaign-level results.</p>
              <div class="stat-list">
                <div class="stat"><span>Google Ads spend</span><strong>Pending</strong></div>
                <div class="stat"><span>ROAS</span><strong>Pending</strong></div>
              </div>
            </article>"""
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow, noarchive">
    <title>Zincs for Boats Executive Marketing Performance | Stott Marketing</title>
    <style>
      :root {{
        color-scheme: light;
        --ink: #14202a;
        --muted: #667481;
        --line: #d9e3e7;
        --soft: #f3f7f8;
        --navy: #17324a;
        --blue: #2567b1;
        --teal: #0f8a9a;
        --green: #177245;
        --gold: #b77416;
        --white: #fff;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink);
        background: #eef4f6;
      }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; min-height: 100vh; background: #eef4f6; }}
      .app {{ width: min(1120px, calc(100% - 40px)); margin: 0 auto; padding: 26px 0 48px; }}
      .topbar {{ display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 20px; }}
      .brand {{ display: flex; align-items: center; gap: 16px; min-width: 0; }}
      .brand img {{ width: 150px; height: 58px; object-fit: contain; }}
      .brand-copy strong {{ display: block; font-family: Georgia, "Times New Roman", serif; font-size: 18px; line-height: 1.2; }}
      .brand-copy small {{ display: block; margin-top: 4px; color: var(--muted); font-weight: 800; font-size: 12px; letter-spacing: .02em; text-transform: uppercase; }}
      .pill {{ padding: 8px 12px; border: 1px solid #b9d5e8; border-radius: 999px; background: #eff8ff; color: #1f5f98; font-size: 13px; font-weight: 800; white-space: nowrap; }}
      .hero {{ position: relative; overflow: hidden; padding: 38px; border-radius: 8px; background: #132838; color: #fff; box-shadow: 0 18px 46px rgba(25, 58, 75, .16); }}
      .hero::before {{ content: ""; position: absolute; inset: 0; background: linear-gradient(135deg, rgba(37,103,177,.62), rgba(15,138,154,.42) 52%, rgba(19,40,56,.94)); }}
      .hero::after {{ content: ""; position: absolute; right: -90px; top: -50px; width: 390px; height: 190px; border: 34px solid rgba(255,255,255,.13); transform: rotate(-12deg); }}
      .hero > * {{ position: relative; z-index: 1; }}
      .eyebrow {{ margin: 0 0 10px; color: #c9edf8; font-size: 13px; font-weight: 850; text-transform: uppercase; }}
      h1, h2, h3, p {{ margin-top: 0; }}
      h1 {{ max-width: 850px; margin-bottom: 12px; font-family: Georgia, "Times New Roman", serif; font-size: clamp(36px, 5.4vw, 60px); line-height: 1; font-weight: 500; }}
      .hero p.lede {{ max-width: 830px; margin-bottom: 26px; color: rgba(255,255,255,.84); font-size: 18px; line-height: 1.58; }}
      .hero-metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; overflow: hidden; border: 1px solid rgba(255,255,255,.16); border-radius: 8px; background: rgba(255,255,255,.18); }}
      .hero-metric {{ min-height: 126px; padding: 17px; background: rgba(255,255,255,.09); }}
      .hero-metric span {{ display: block; margin-bottom: 8px; color: rgba(255,255,255,.68); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .hero-metric strong {{ display: block; margin-bottom: 8px; font-size: 28px; }}
      .hero-metric small {{ color: rgba(255,255,255,.77); line-height: 1.4; }}
      main {{ display: grid; gap: 18px; margin-top: 20px; }}
      .card {{ min-width: 0; padding: 26px; border: 1px solid var(--line); border-radius: 8px; background: var(--white); box-shadow: 0 12px 34px rgba(34, 74, 86, .08); }}
      .card h2 {{ margin-bottom: 14px; font-size: 22px; }}
      .summary {{ color: #3f4c56; font-size: 16px; line-height: 1.68; }}
      .grid-3 {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
      .grid-2 {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
      .panel {{ padding: 18px; border: 1px solid var(--line); border-radius: 8px; background: var(--soft); }}
      .panel h3 {{ margin-bottom: 9px; font-size: 17px; }}
      .panel p {{ margin-bottom: 0; color: #43525d; line-height: 1.55; }}
      .stat-list {{ display: grid; gap: 10px; margin-top: 14px; }}
      .stat {{ display: flex; justify-content: space-between; gap: 16px; padding-top: 10px; border-top: 1px solid #dde7ea; }}
      .stat span {{ color: var(--muted); }}
      .stat strong {{ text-align: right; }}
      .revenue {{ border-left: 4px solid var(--green); background: #f1fbf6; }}
      .seo {{ border-left: 4px solid var(--gold); background: #fff9ed; }}
      .traffic {{ border-left: 4px solid var(--blue); background: #f2f8ff; }}
      .pending {{ border-left: 4px solid #8a99a8; background: #f6f8fa; }}
      .status {{ display: flex; align-items: flex-start; gap: 10px; margin-top: 16px; padding: 14px; border: 1px solid #cfe3ef; border-radius: 8px; background: #f3f9fc; color: #31596d; line-height: 1.5; }}
      .dot {{ width: 9px; height: 9px; margin-top: 6px; border-radius: 999px; background: var(--teal); flex: 0 0 auto; }}
      .source-note {{ margin-top: 14px; color: var(--muted); font-size: 12px; line-height: 1.5; }}
      .analytics-strip {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; overflow: hidden; border: 1px solid var(--line); border-radius: 8px; background: var(--line); }}
      .analytics-metric {{ min-height: 116px; padding: 17px; background: #fbfdfe; }}
      .analytics-metric span {{ display: block; margin-bottom: 8px; color: var(--muted); font-size: 12px; font-weight: 850; text-transform: uppercase; }}
      .analytics-metric strong {{ display: block; margin-bottom: 7px; font-size: 28px; color: var(--navy); }}
      .analytics-metric small {{ color: #53616c; line-height: 1.4; }}
      .analytics-board {{ display: grid; gap: 10px; margin-top: 16px; }}
      .analytics-row {{ display: grid; grid-template-columns: minmax(150px, .8fr) minmax(180px, 1.6fr) minmax(140px, .7fr); gap: 14px; align-items: center; padding: 12px 0; border-top: 1px solid var(--line); }}
      .analytics-row:first-child {{ border-top: 0; }}
      .analytics-label strong, .analytics-values strong {{ display: block; color: #24323d; }}
      .analytics-label span, .analytics-values span {{ display: block; margin-top: 3px; color: var(--muted); font-size: 13px; }}
      .analytics-values {{ text-align: right; }}
      .analytics-track {{ height: 12px; overflow: hidden; border-radius: 999px; background: #e6eef2; }}
      .analytics-track span {{ display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--blue), var(--teal)); }}
      .weekday-sales {{ display: grid; width: 100%; min-width: 0; grid-template-columns: repeat(7, minmax(118px, 1fr)); gap: 1px; overflow: hidden; border: 1px solid var(--line); border-radius: 8px; background: var(--line); }}
      .weekday-card {{ min-height: 158px; display: grid; align-content: start; background: #fbfdfe; }}
      .weekday-card h3 {{ margin: 0; padding: 13px 12px; border-bottom: 1px solid var(--line); background: #f3f7f8; color: #2f3e48; font-size: 13px; text-align: center; text-transform: uppercase; }}
      .weekday-split {{ display: grid; grid-template-columns: 1fr; gap: 4px; padding: 14px 12px; text-align: center; }}
      .weekday-split + .weekday-split {{ border-top: 1px solid var(--line); }}
      .weekday-split span {{ color: var(--muted); font-size: 11px; font-weight: 850; text-transform: uppercase; }}
      .weekday-split strong {{ color: var(--navy); font-size: 18px; }}
      .channels {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
      .channel {{ min-height: 118px; padding: 16px; border: 1px solid var(--line); border-radius: 8px; background: #fbfdfe; }}
      .channel span {{ display: block; margin-bottom: 8px; color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .channel strong {{ display: block; margin-bottom: 8px; font-size: 24px; }}
      .channel small {{ color: #53616c; line-height: 1.45; }}
      .table {{ display: grid; gap: 0; overflow: hidden; border: 1px solid var(--line); border-radius: 8px; }}
      .table-row {{ display: grid; grid-template-columns: minmax(180px, 1fr) repeat(4, minmax(78px, .25fr)); gap: 12px; align-items: center; padding: 12px 14px; border-top: 1px solid var(--line); background: #fff; }}
      .table-row:first-child {{ border-top: 0; }}
      .table-head {{ background: #f3f7f8; color: var(--muted); font-size: 12px; font-weight: 850; text-transform: uppercase; }}
      .table-row span {{ min-width: 0; overflow-wrap: anywhere; color: #394853; }}
      .table-row strong {{ text-align: right; }}
      .page-row {{ grid-template-columns: minmax(180px, 1fr) repeat(3, minmax(78px, .25fr)); }}
{public_update_css(text_color="#3f4c56", line_color="var(--line)")}
      @media (max-width: 820px) {{
        .app {{ width: min(100% - 24px, 1120px); }}
        .topbar {{ align-items: flex-start; flex-direction: column; }}
        .brand img {{ width: 136px; }}
        .hero, .card {{ padding: 21px; }}
        .hero-metrics, .grid-3, .grid-2, .channels, .analytics-strip {{ grid-template-columns: 1fr; }}
        .analytics-row {{ grid-template-columns: 1fr; gap: 7px; }}
        .analytics-values {{ text-align: left; }}
        .weekday-sales {{ overflow-x: auto; grid-template-columns: repeat(7, minmax(128px, 1fr)); }}
        .table-row, .page-row {{ grid-template-columns: 1fr 1fr; }}
        .table-row strong {{ text-align: left; }}
        .table-head {{ display: none; }}
      }}
      @media (min-width: 821px) and (max-width: 1040px) {{
        .hero-metrics, .channels, .analytics-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        .grid-3 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      }}
    </style>
  </head>
  <body>
    <div class="app">
      <header class="topbar">
        <div class="brand">
          <img src="/zincs-for-boats/assets/z4b-logo.png" alt="Zincs for Boats logo">
          <div class="brand-copy">
            <strong>Zincs for Boats</strong>
            <small>Executive performance report by Stott Marketing</small>
          </div>
        </div>
        <div class="pill">Private client update</div>
      </header>

      <section class="hero">
        <p class="eyebrow">Executive Marketing Performance</p>
        <h1>{safe(revenue_headline)}</h1>
        <p class="lede">{safe(revenue_lede)}</p>
          <div class="hero-metrics">
            <div class="hero-metric"><span>{safe(hero_revenue_label)}</span><strong>{hero_revenue_value}</strong><small>{safe(hero_revenue_detail)}</small></div>
          <div class="hero-metric"><span>{safe(hero_orders_label)}</span><strong>{hero_orders_value}</strong><small>{safe(hero_orders_detail)}</small></div>
          <div class="hero-metric"><span>{safe(hero_aov_label)}</span><strong>{hero_aov_value}</strong><small>{safe(hero_aov_detail)}</small></div>
          <div class="hero-metric"><span>{safe(ytd_revenue_label)}</span><strong>{ytd_revenue_value}</strong><small>{safe(ytd_revenue_detail)}</small></div>
        </div>
      </section>

      <main>
        <section id="posted-updates-section" class="card" hidden>
          <h2>Current Updates</h2>
          <div id="posted-updates" class="posted-updates"></div>
          <ul id="dynamic-takeaways" class="dynamic-takeaways"></ul>
        </section>

        <section class="card">
          <h2>Executive Summary</h2>
          <p class="summary">For June 1 through June 30, 2026, {"Shopify recorded " + number(shopify_metrics.get("orders", 0)) + " orders and " + money(shopify_metrics.get("revenue", 0), 2) + " in store revenue. " if shopify_connected else ""}GA4 recorded {number(ga["active_users"])} active users, {number(ga["sessions"])} sessions, {number(ga["ecommerce_purchases"])} ecommerce purchases, and {money(ga["total_revenue"], 2)} in tracked revenue. Year to date through June 30, {"Shopify shows " + money(shopify_ytd_metrics.get("revenue", 0), 2) + " in revenue from " + number(shopify_ytd_metrics.get("orders", 0)) + " orders, while " if shopify_connected else ""}GA4 shows {money(ga_ytd["total_revenue"], 2)} in tracked revenue from {number(ga_ytd["ecommerce_purchases"])} ecommerce purchases. The strongest June channel by tracked revenue was {safe(top_channel["channel"])}, with {money(top_channel["revenue"], 2)} from {number(top_channel["purchases"])} purchases.</p>
          <p class="summary">Organic search is meaningful but has clear upside. Search Console recorded {number(sc_summary.get("clicks", 0))} clicks and {number(sc_summary.get("impressions", 0))} impressions with an average position of {number(sc_summary.get("position", 0), 1)}. Search Atlas shows {number(se["keyword_count"])} tracked keywords, {number(se["top_3_keywords_count"])} top-3 rankings, a site health score of {number(se["site_health"])}, and {number(se["refdomain_count"])} referring domains. {safe(ads_source_label) + " data shows " + money(ads_metrics.get("cost", 0), 2) + " in spend, " + money(ads_metrics.get("conversion_value", 0), 2) + " in conversion value, and " + number(ads_metrics.get("reported_roas", 0), 2) + "x reported ROAS. " if ads_connected else ""}The key operating focus is improving the channels that already prove purchase intent while using SEO to lower dependency on paid acquisition.</p>
        </section>

        <section class="card">
          <h2>Website Analytics Performance</h2>
          <div class="analytics-strip">
            <article class="analytics-metric">
              <span>Sessions</span>
              <strong>{number(ga["sessions"])}</strong>
              <small>{number(ga["active_users"])} active users</small>
            </article>
            <article class="analytics-metric">
              <span>Engagement</span>
              <strong>{pct(ga["engagement_rate"])}</strong>
              <small>{number(ga["key_events"])} key events</small>
            </article>
            <article class="analytics-metric">
              <span>Purchase Rate</span>
              <strong>{pct(ga_conversion_rate)}</strong>
              <small>{number(ga["ecommerce_purchases"])} GA4 purchases</small>
            </article>
            <article class="analytics-metric">
              <span>Revenue / Session</span>
              <strong>{money(ga_revenue_per_session, 2)}</strong>
              <small>{money(ga["total_revenue"], 0)} GA4 revenue</small>
            </article>
          </div>
          <div class="analytics-board">
{analytics_bar_items}
          </div>
          <p class="source-note">Source: GA4 channel performance for {safe(period["start"])} through {safe(period["end"])}.</p>
        </section>

        <section class="card">
          <h2>Revenue and Channel Performance</h2>
          <div class="grid-3">
            <article class="panel revenue">
              <h3>GA4 ecommerce revenue</h3>
              <p>GA4 is tracking purchase activity and provides the channel view beside direct Shopify revenue.</p>
              <div class="stat-list">
                <div class="stat"><span>June revenue</span><strong>{money(ga["total_revenue"], 2)}</strong></div>
                <div class="stat"><span>June purchases</span><strong>{number(ga["ecommerce_purchases"])}</strong></div>
                <div class="stat"><span>June purchasers</span><strong>{number(ga["total_purchasers"])}</strong></div>
                <div class="stat"><span>Engagement rate</span><strong>{pct(ga["engagement_rate"])}</strong></div>
              </div>
            </article>
{shopify_panel}
{ads_panel}
          </div>
          <p class="source-note">Sources: {"Shopify Admin GraphQL API " + safe(shopify.get("api_version", "")) + ", " if shopify_connected else ""}GA4 property 255281532{", and " + safe(ads_source_label) if ads_connected else ""}. Shopify totals should be reconciled with payout and tax reporting before using this as a financial close report.</p>
        </section>

        {f'''
        <section class="card">
          <h2>Shopify Daily Sales Reporting - June, 2026</h2>
          <div class="weekday-sales">
{weekday_sales_items}
          </div>
          <p class="source-note">Source: Shopify Admin GraphQL API {safe(shopify.get("api_version", ""))}. Sales are grouped by order creation day for June 1 through June 30, 2026.</p>
        </section>
        ''' if shopify_connected else ''}

        {f'''
        <section class="card">
          <h2>Top Shopify Products</h2>
          <div class="table">
            <div class="table-row table-head page-row"><span>Product</span><strong>Qty.</strong><strong>Revenue</strong><strong>Avg.</strong></div>
{product_items}
          </div>
        </section>
        ''' if shopify_connected else ''}

        {f'''
        <section class="card">
          <h2>Google Ads Performance</h2>
          <div class="table">
            <div class="table-row table-head"><span>Ad Group</span><strong>Spend</strong><strong>Clicks</strong><strong>Conv.</strong><strong>ROAS</strong></div>
{ad_group_items}
          </div>
          <p class="source-note">Source: {safe(ads_source_label)}.</p>
        </section>
        ''' if ads_connected else ''}

        <section class="card">
          <h2>Channel Breakdown</h2>
          <div class="channels">
{channel_items}
          </div>
        </section>

        <section class="card">
          <h2>Organic Search</h2>
          <div class="grid-2">
            <article class="panel seo">
              <h3>Search Console performance</h3>
              <p>Search Console shows where Google organic search is already producing visits and which terms are close enough to improve with targeted SEO work.</p>
              <div class="stat-list">
                <div class="stat"><span>Clicks</span><strong>{number(sc_summary.get("clicks", 0))}</strong></div>
                <div class="stat"><span>Impressions</span><strong>{number(sc_summary.get("impressions", 0))}</strong></div>
                <div class="stat"><span>CTR</span><strong>{pct(sc_summary.get("ctr", 0), 2)}</strong></div>
                <div class="stat"><span>Avg. position</span><strong>{number(sc_summary.get("position", 0), 1)}</strong></div>
              </div>
            </article>
            <article class="panel seo">
              <h3>Search Atlas opportunity</h3>
              <p>{safe(atlas.get("ai_summary") or "Search Atlas is showing a clear opportunity to strengthen authority and technical SEO.")}</p>
              <div class="stat-list">
                <div class="stat"><span>Site health</span><strong>{number(se["site_health"])}</strong></div>
                <div class="stat"><span>Domain power</span><strong>{number(se["domain_power"])}</strong></div>
                <div class="stat"><span>Referring domains</span><strong>{number(se["refdomain_count"])}</strong></div>
                <div class="stat"><span>OTTO deployed fixes</span><strong>{number(se["otto_total_deployed_fixes"])}</strong></div>
              </div>
            </article>
          </div>
        </section>

        <section class="card">
          <h2>Top Organic Queries</h2>
          <div class="table">
            <div class="table-row table-head"><span>Query</span><strong>Clicks</strong><strong>Impr.</strong><strong>CTR</strong><strong>Pos.</strong></div>
{query_items}
          </div>
        </section>

        <section class="card">
          <h2>Top Organic Landing Pages</h2>
          <div class="table">
            <div class="table-row table-head page-row"><span>Page</span><strong>Clicks</strong><strong>Impr.</strong><strong>Pos.</strong></div>
{page_items}
          </div>
        </section>

        <section class="card">
          <h2>SEO and AI Visibility</h2>
          <div class="grid-3">
            <article class="panel seo">
              <h3>Keyword footprint</h3>
              <p>Zincs for Boats has a broad tracked keyword set. The practical opportunity is moving more page-one and near-page-one rankings into top positions.</p>
              <div class="stat-list">
                <div class="stat"><span>Tracked keywords</span><strong>{number(se["keyword_count"])}</strong></div>
                <div class="stat"><span>Top-3 keywords</span><strong>{number(se["top_3_keywords_count"])}</strong></div>
                <div class="stat"><span>Organic traffic estimate</span><strong>{number(se["organic_traffic"])}</strong></div>
              </div>
            </article>
            <article class="panel traffic">
              <h3>AI discovery signal</h3>
              <p>Search Atlas is also tracking LLM visibility, which matters as customers increasingly use AI tools alongside search for product research.</p>
              <div class="stat-list">
                <div class="stat"><span>Current mentions</span><strong>{number(se["llm_current_mentions"])}</strong></div>
                <div class="stat"><span>Previous mentions</span><strong>{number(se["llm_previous_mentions"])}</strong></div>
                <div class="stat"><span>Lift</span><strong>{pct_plain(llm_lift)} </strong></div>
              </div>
            </article>
            <article class="panel pending">
              <h3>Priority recommendation</h3>
              <p>Connect Shopify and Google Ads first, then use the combined revenue and search data to prioritize profitable products, landing pages, and backlink targets.</p>
              <div class="stat-list">
                <div class="stat"><span>Next data connection</span><strong>Shopify</strong></div>
                <div class="stat"><span>Next paid media connection</span><strong>Google Ads</strong></div>
                <div class="stat"><span>SEO focus</span><strong>Authority</strong></div>
              </div>
            </article>
          </div>
          <div class="status"><span class="dot"></span><span>This report covers {safe(period["start"])} through {safe(period["end"])} for current-period GA4 and Search Console, with YTD GA4 covering {safe(ytd_period["start"])} through {safe(ytd_period["end"])}.</span></div>
        </section>
      </main>
    </div>
{public_updates_script("zincs-for-boats")}
  </body>
</html>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    LOGO.parent.mkdir(parents=True, exist_ok=True)
    if LOGO_SOURCE.exists():
        shutil.copyfile(LOGO_SOURCE, LOGO)
    (OUT / "index.html").write_text(page(), encoding="utf-8")
    print(f"Wrote Zincs for Boats report to {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
