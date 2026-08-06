from __future__ import annotations

import html
import json
import base64
from datetime import datetime
from pathlib import Path

from public_update_renderer import add_posted_update_js, public_update_css, public_update_js_helpers


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "airocide"
OUT = ROOT / "firebase-static" / "public" / "airocide-systems"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def money(value: float | int | str, digits: int = 0) -> str:
    return f"${float(value or 0):,.{digits}f}"


def number(value: float | int | str, digits: int = 0) -> str:
    return f"{float(value or 0):,.{digits}f}"


def pct(value: float | int | str, digits: int = 1) -> str:
    return f"{float(value or 0) * 100:.{digits}f}%"


def pct_change(start: float, end: float) -> str:
    if not start:
        return "New baseline"
    change = ((end - start) / start) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.1f}%"


def safe(value: object) -> str:
    return html.escape(str(value), quote=True)


def asset_data_uri(path: Path, mime_type: str) -> str:
    return f"data:{mime_type};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def search_summary(sc: dict) -> dict:
    return ((sc.get("summary") or {}).get("rows") or [{}])[0]


def search_rows(sc: dict, key: str) -> list[dict]:
    return (sc.get(key) or {}).get("rows") or []


def row_key(row: dict) -> str:
    return ((row.get("keys") or [""])[0] or "")


def period_label(period: dict) -> str:
    start = period.get("start") or ""
    end = period.get("end") or ""
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        return f"{start} to {end}".strip(" to")
    return f"{start_date.strftime('%b')} {start_date.day} - {end_date.strftime('%b')} {end_date.day}, {end_date.year}"


def trend_value(rows: list[dict], prefix: str) -> float:
    for row in rows:
        if str(row.get("date") or "").startswith(prefix):
            return float(row.get("value") or 0)
    return 0


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


CONTENT_CATEGORIES = [
    {
        "category": "Education & Institutional Air Safety",
        "summary": "Content supports school, university, and institutional air-safety search intent with proof-based case study material.",
        "primary": (
            "Far-UVC Cuts Classroom Infection Risk 91% | Roger Williams University",
            "https://www.airocide.com/roger-williams-university-visium-far-uvc-case-study/",
        ),
        "supporting": [
            (
                "UV-C HVAC Disinfection in Schools | Jefferson County",
                "https://www.airocide.com/fighter-flex-school-case-study-jefferson-county/",
            )
        ],
    },
    {
        "category": "Commercial Facilities & HVAC",
        "summary": "Content expands Airocide Systems into commercial facility, HVAC maintenance, hotel, and building operations search paths.",
        "primary": (
            "Benefits of HVAC UV Coil Cleaning for Commercial Facilities",
            "https://www.airocide.com/benefits-of-hvac-uv-coil-cleaning-for-commercial-facilities/",
        ),
        "supporting": [
            (
                "Fighter Flex UVC Hotel Case Study",
                "https://www.airocide.com/fighter-flex-uvc-hotel-case-study-airocide-systems/",
            )
        ],
    },
    {
        "category": "Food Safety & Shelf-Life Protection",
        "summary": "Content builds relevance around spoilage reduction, ethylene control, mold prevention, and food-storage applications.",
        "primary": (
            "Del Monte Case Study: 99.8% Ethylene Reduction",
            "https://www.airocide.com/del-monte-case-study-99-8-percent-ethylene-reduction/",
        ),
        "supporting": [
            (
                "Ebrocork Mold & TCA Prevention",
                "https://www.airocide.com/case-study-ebrocork/",
            ),
            (
                "Banana Shelf Life Extended 118%",
                "https://www.airocide.com/banana-shelf-life-extended-118-percent-dod-validated-case-study/",
            ),
            (
                "87% Mold Reduction in Cheese Maturation",
                "https://www.airocide.com/sirimon-cheese-case-study-maturation-room-spoilage/",
            ),
        ],
    },
    {
        "category": "Healthcare & Pharmacy Compliance",
        "summary": "Content supports healthcare, pharmacy, and USP 797-related research paths with a focused compliance case study.",
        "primary": (
            "Airocide Mobile Pharmacy Case Study | USP 797 Compliance",
            "https://www.airocide.com/airocide-mobile-pharmacy-case-study-usp-797-compliance/",
        ),
        "supporting": [],
    },
    {
        "category": "Floral & Perishable Inventory Protection",
        "summary": "Content connects Airocide Systems to floral cooler protection, perishable inventory, and business-loss prevention.",
        "primary": (
            "Mold & Bacteria Reduction in Floral Coolers",
            "https://www.airocide.com/high-efficiency-air-purifier-eliminating-mold-bacteria-floral-coolers/",
        ),
        "supporting": [
            (
                "Flower Shop Air Purification",
                "https://www.airocide.com/flower-shop-air-purification-airocide-systems-case-study/",
            )
        ],
    },
]


def content_category_cards() -> str:
    cards = []
    for item in CONTENT_CATEGORIES:
        supporting = "".join(
            f'<li><span>Supporting Content Case Study</span><a href="{safe(url)}" target="_blank" rel="noopener">{safe(label)}</a></li>'
            for label, url in item["supporting"]
        )
        supporting_html = f"<ul>{supporting}</ul>" if supporting else ""
        cards.append(
            f"""
            <article class="content-card">
              <h3>{safe(item["category"])}</h3>
              <p>{safe(item["summary"])}</p>
              <div class="content-links">
                <span>Primary SEO Page</span>
                <a href="{safe(item["primary"][1])}" target="_blank" rel="noopener">{safe(item["primary"][0])}</a>
                {supporting_html}
              </div>
            </article>"""
        )
    return "\n".join(cards)


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
    channels = channel_rows(load("ga4_channels.json"))
    sc = load("search_console.json")
    atlas = load("search_atlas.json")

    ga = ga4["metrics"]
    project = atlas["domain"]
    se = project["metrics"]
    keyword_trend = project.get("organic_keywords_trend") or []
    traffic_trend = project.get("organic_traffic_trend") or []
    april_keywords = trend_value(keyword_trend, "2026-04")
    april_traffic = trend_value(traffic_trend, "2026-04")
    current_keywords = float(se.get("keyword_count") or se.get("organic_keywords") or 0)
    current_traffic = float(se.get("organic_traffic") or se.get("traffic") or 0)
    current_llm = float(se.get("llm_current_mentions") or 0)
    previous_llm = float(se.get("llm_previous_mentions") or 0)
    llm_delta = pct_change(previous_llm, current_llm)
    organic = next((row for row in channels if row["channel"] == "Organic Search"), None) or {}
    direct = next((row for row in channels if row["channel"] == "Direct"), None) or {}
    ai_channel = next((row for row in channels if row["channel"] == "AI Assistant"), None) or {}
    sc_summary = search_summary(sc)
    top_queries = search_rows(sc, "queries")[:5]
    top_pages = search_rows(sc, "pages")[:5]
    logo_src = asset_data_uri(OUT / "assets" / "airocide-logo-1x.png", "image/png")

    query_rows_html = "\n".join(
        f"""
                <tr>
                  <td>{safe(row_key(row))}</td>
                  <td>{number(row.get("clicks"))}</td>
                  <td>{number(row.get("impressions"))}</td>
                  <td>{float(row.get("ctr") or 0) * 100:.1f}%</td>
                  <td>{float(row.get("position") or 0):.1f}</td>
                </tr>"""
        for row in top_queries
    )
    page_rows_html = "\n".join(
        f"""
                <tr>
                  <td>{safe(row_key(row))}</td>
                  <td>{number(row.get("clicks"))}</td>
                  <td>{number(row.get("impressions"))}</td>
                  <td>{float(row.get("ctr") or 0) * 100:.1f}%</td>
                  <td>{float(row.get("position") or 0):.1f}</td>
                </tr>"""
        for row in top_pages
    )

    channel_rows_html = "\n".join(
        f"""
                <tr>
                  <td>{safe(row["channel"])}</td>
                  <td>{number(row["sessions"])}</td>
                  <td>{number(row["active_users"])}</td>
                  <td>{number(row["key_events"])}</td>
                  <td>{money(row["revenue"], 0)}</td>
                  <td>{number(row["purchases"])}</td>
                </tr>"""
        for row in channels[:8]
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow, noarchive">
    <title>Airocide Systems SEO Update | Stott Marketing</title>
    <style>
      :root {{
        color-scheme: light;
        --ink: #111827;
        --muted: #5f6b78;
        --line: #d9e2ea;
        --soft: #f5f9fc;
        --navy: #0B1E3C;
        --blue: #005fc2;
        --sky: #2b81d1;
        --ice: #deeffd;
        --green: #0d7b56;
        --gold: #8A5E10;
        --cream: #EDE4D4;
        --white: #fff;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink);
        background: #f3f7f8;
      }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; min-height: 100vh; }}
      .app {{ width: min(1120px, calc(100% - 40px)); margin: 0 auto; padding: 26px 0 48px; }}
      .topbar {{ display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 20px; }}
      .brand {{ display: flex; align-items: center; gap: 16px; }}
      .brand-logo {{ display: grid; place-items: center; width: 188px; height: 66px; padding: 10px 14px; border: 1px solid var(--line); border-radius: 8px; background: #fff; }}
      .brand-logo img {{ display: block; max-width: 100%; max-height: 100%; object-fit: contain; }}
      .brand-copy strong {{ display: block; font-size: 19px; line-height: 1.2; }}
      .brand-copy small {{ display: block; margin-top: 4px; color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .pill {{ padding: 8px 12px; border: 1px solid #bad7ef; border-radius: 999px; background: #eef7ff; color: var(--navy); font-size: 13px; font-weight: 800; white-space: nowrap; }}
      .hero {{ padding: 38px; border-radius: 8px; background: linear-gradient(135deg, #0B1E3C, #005fc2 66%, #2b81d1); color: #fff; box-shadow: 0 18px 46px rgba(11, 30, 60, .2); }}
      .eyebrow {{ margin: 0 0 10px; color: #d8ecff; font-size: 13px; font-weight: 850; text-transform: uppercase; }}
      h1, h2, h3, p {{ margin-top: 0; }}
      h1 {{ max-width: 920px; margin-bottom: 12px; font-size: clamp(36px, 5.6vw, 60px); line-height: 1; font-weight: 720; letter-spacing: 0; }}
      .hero p.lede {{ max-width: 900px; margin-bottom: 26px; color: rgba(255,255,255,.84); font-size: 18px; line-height: 1.58; }}
      .hero-metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; overflow: hidden; border: 1px solid rgba(255,255,255,.16); border-radius: 8px; background: rgba(255,255,255,.18); }}
      .hero-metric {{ min-height: 126px; padding: 17px; background: rgba(255,255,255,.09); }}
      .hero-metric span {{ display: block; margin-bottom: 8px; color: rgba(255,255,255,.7); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .hero-metric strong {{ display: block; margin-bottom: 8px; font-size: 28px; }}
      .hero-metric small {{ color: rgba(255,255,255,.78); line-height: 1.4; }}
      main {{ display: grid; gap: 18px; margin-top: 20px; }}
      .card {{ padding: 26px; border: 1px solid var(--line); border-radius: 8px; background: var(--white); box-shadow: 0 12px 34px rgba(34, 74, 86, .08); }}
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
      .seo {{ border-left: 4px solid var(--gold); background: #fff9ed; }}
      .growth {{ border-left: 4px solid var(--green); background: #f1fbf6; }}
      .foundation {{ border-left: 4px solid var(--blue); background: #eff7ff; }}
      .content-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 16px; }}
      .content-card {{ padding: 20px; border: 1px solid var(--line); border-radius: 8px; background: #fff; box-shadow: 0 8px 26px rgba(11, 30, 60, .06); }}
      .content-card h3 {{ margin-bottom: 9px; font-size: 18px; color: var(--navy); }}
      .content-card p {{ margin-bottom: 14px; color: #43525d; line-height: 1.55; }}
      .content-links {{ display: grid; gap: 6px; }}
      .content-links span, .content-links li span {{ display: block; color: var(--muted); font-size: 11px; font-weight: 850; text-transform: uppercase; }}
      .content-links a {{ color: var(--blue); font-weight: 800; text-decoration: none; }}
      .content-links a:hover {{ text-decoration: underline; }}
      .content-links ul {{ display: grid; gap: 8px; margin: 8px 0 0; padding: 12px 0 0; border-top: 1px solid var(--line); list-style: none; }}
      .content-links li {{ display: grid; gap: 3px; }}
      .highlight-band {{ padding: 20px; border: 1px solid #c6daef; border-radius: 8px; background: linear-gradient(180deg, #f8fbff, #edf6ff); }}
      .highlight-band p:last-child {{ margin-bottom: 0; }}
      .link-list {{ display: grid; gap: 9px; margin: 14px 0 0; padding: 0; list-style: none; }}
      .link-list li {{ display: flex; justify-content: space-between; gap: 14px; align-items: center; padding: 12px 0; border-top: 1px solid var(--line); }}
      .link-list span {{ color: var(--muted); font-size: 12px; font-weight: 850; text-transform: uppercase; }}
      .link-list a {{ color: var(--blue); font-weight: 850; text-decoration: none; text-align: right; }}
      .link-list a:hover {{ text-decoration: underline; }}
      table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
      th, td {{ padding: 11px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
      th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
      .progress-list {{ display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }}
      .progress-list li {{ padding: 12px 0; border-top: 1px solid var(--line); color: #3f4c56; line-height: 1.55; }}
      .progress-list li:first-child {{ border-top: 0; padding-top: 0; }}
      .source-note {{ margin-top: 14px; color: var(--muted); font-size: 12px; line-height: 1.5; }}
      .dynamic-takeaways {{ display: grid; gap: 10px; margin: 14px 0 0; padding: 0; list-style: none; }}
      .dynamic-takeaways li {{ display: grid; grid-template-columns: 22px 1fr; gap: 10px; align-items: start; padding: 10px 0; border-top: 1px solid var(--line); color: #3f4c56; line-height: 1.5; }}
      .dynamic-takeaways .box {{ width: 17px; height: 17px; margin-top: 3px; border: 2px solid #95a8b3; border-radius: 4px; background: #fff; }}
{public_update_css(text_color="#3f4c56", line_color="var(--line)")}
      @media (max-width: 820px) {{
        .app {{ width: min(100% - 24px, 1120px); }}
        .topbar {{ align-items: flex-start; flex-direction: column; }}
        .hero, .card {{ padding: 21px; }}
        .hero-metrics, .grid-3, .grid-2, .content-grid {{ grid-template-columns: 1fr; }}
        .brand-logo {{ width: 176px; }}
        .link-list li {{ align-items: flex-start; flex-direction: column; }}
        .link-list a {{ text-align: left; }}
      }}
    </style>
  </head>
  <body>
    <div class="app">
      <header class="topbar">
        <div class="brand">
          <div class="brand-logo">
            <img src="{logo_src}" alt="Airocide Systems">
          </div>
          <div class="brand-copy">
            <strong>Airocide Systems</strong>
            <small>SEO foundation report by Stott Marketing</small>
          </div>
        </div>
        <div class="pill">Private client update</div>
      </header>

      <section class="hero">
        <p class="eyebrow">Brand Consolidation SEO Update</p>
        <h1>Airocide.com is becoming a stronger organic growth asset.</h1>
        <p class="lede">Since April 1, 2026, the work has focused on strengthening Airocide.com as the primary SEO destination for Airocide Systems, expanding commercial proof points, improving how the site supports buyer research, and preparing a launch-ready paid search option.</p>
        <div class="hero-metrics">
          <div class="hero-metric"><span>Tracked Keywords</span><strong>{number(current_keywords)}</strong><small>{pct_change(april_keywords, current_keywords)} from April baseline</small></div>
          <div class="hero-metric"><span>Top 3 Rankings</span><strong>{number(se.get("top_3_keywords_count"))}</strong><small>High-visibility keyword positions</small></div>
          <div class="hero-metric"><span>LLM Visibility</span><strong>{number(current_llm)}</strong><small>{llm_delta} vs previous Search Atlas read</small></div>
          <div class="hero-metric"><span>Authority Base</span><strong>{number(se.get("refdomain_count"))}</strong><small>{number(se.get("backlinks"))} backlinks</small></div>
        </div>
      </section>

      <main>
        <section class="card">
          <h2>Executive Summary</h2>
          <p class="summary">Since April 1, the focus has been on strengthening Airocide.com as the primary SEO asset for Airocide Systems. The work has centered on consolidating search value into one stronger domain, improving the site structure, expanding commercial and industry-specific content, and preparing the next layer of demand generation.</p>
          <p class="summary">The newest progress is meaningful: 11 new SEO-focused pages have been launched across education, healthcare, hospitality, food safety, agriculture, floral, and commercial facility use cases. These pages give Google more specific content to understand where Airocide Systems fits, while giving prospective buyers stronger proof points when they research air purification, UVC, spoilage reduction, and facility air-quality solutions.</p>
          <p class="summary">The data supports the foundation story. Search Atlas shows tracked keywords increasing from {number(april_keywords)} in April to {number(current_keywords)} currently, a {pct_change(april_keywords, current_keywords)} gain during the consolidation period. GA4 shows {number(ga.get("active_users"))} active users, {number(ga.get("sessions"))} sessions, {pct(ga.get("engagement_rate"))} engagement, and {number(ga.get("key_events"))} key events from {safe(period_label(refresh["period"]))}. Google Search Console is connected for {safe(sc.get("site_url"))}, adding verified organic search performance: {number(sc_summary.get("clicks"))} clicks, {number(sc_summary.get("impressions"))} impressions, {float(sc_summary.get("ctr") or 0) * 100:.1f}% CTR, and {float(sc_summary.get("position") or 0):.1f} average position.</p>
        </section>

        <section class="card">
          <h2>SEO Content Expansion</h2>
          <p class="summary">The newly launched pages expand Airocide Systems' search footprint into specific commercial and institutional categories. This matters because SEO performance is built through relevance, depth, and proof. These pages help connect Airocide Systems to real buyer use cases instead of relying only on broad product messaging.</p>
          <div class="content-grid">
            {content_category_cards()}
          </div>
        </section>

        <section class="card">
          <h2>Content Operations Progress</h2>
          <div class="highlight-band">
            <p class="summary">In addition to the pages already launched, I am continuing to work through the existing case study folder to identify usable assets, remove duplicate or overlapping versions, and prepare additional content for Airocide.com as each piece is optimized for website publishing.</p>
            <p class="summary">This work includes organizing the available case study material, improving formatting, creating hero images for the case study pages, and updating the presentation so the content feels current, credible, and aligned with today's website standards.</p>
            <p class="summary">The goal is to turn existing proof points into stronger web-accessible SEO assets, rather than simply uploading older documents or duplicate variations without structure.</p>
          </div>
        </section>

        <section class="card">
          <h2>Video SEO and YouTube Integration</h2>
          <div class="grid-2">
            <article class="panel foundation">
              <h3>Three video assets prepared and published</h3>
              <p>Three raw video assets were prepared for publishing, including caption and translation work so the videos could be properly uploaded through YouTube and embedded on the website.</p>
            </article>
            <article class="panel growth">
              <h3>Captions strengthen search and accessibility</h3>
              <p>Properly prepared videos with captions give search engines more readable context, improve accessibility, and strengthen the on-page experience. The videos are now presented on the website in a polished format that supports the brand.</p>
            </article>
          </div>
        </section>

        <section class="card">
          <h2>Paid Search Launch Readiness</h2>
          <p class="summary">Paid search was discussed as a possible next step, so a Google Ads account and launch-ready campaign structure have already been prepared for Airocide Systems. This gives the brand an immediate paid-search option that can run alongside the SEO foundation work.</p>
          <p class="summary">The campaign is ready to move forward once billing is connected. Paid search can help test high-intent demand faster, especially around commercial air purification, UVC air treatment, HVAC coil cleaning, food safety, and industry-specific use cases.</p>
          <div class="grid-3">
            <article class="panel foundation"><h3>Account ready</h3><p>Google Ads account opened and configured for Airocide Systems.</p></article>
            <article class="panel seo"><h3>Campaign built</h3><p>Campaign structure and search-intent targeting have been prepared for launch review.</p></article>
            <article class="panel growth"><h3>Activation step</h3><p>Ready to activate once billing is connected, with performance monitored against traffic quality, search terms, and lead activity.</p></article>
          </div>
        </section>

        <section class="card">
          <h2>SEO Progress Since April 1</h2>
          <div class="grid-3">
            <article class="panel growth">
              <h3>Keyword footprint is expanding</h3>
              <p>The consolidation work is increasing the tracked keyword footprint for Airocide.com.</p>
              <div class="stat-list">
                <div class="stat"><span>April keyword baseline</span><strong>{number(april_keywords)}</strong></div>
                <div class="stat"><span>Current tracked keywords</span><strong>{number(current_keywords)}</strong></div>
                <div class="stat"><span>Progress</span><strong>{pct_change(april_keywords, current_keywords)}</strong></div>
                <div class="stat"><span>Top-3 keywords</span><strong>{number(se.get("top_3_keywords_count"))}</strong></div>
              </div>
            </article>
            <article class="panel seo">
              <h3>Authority is concentrated on Airocide.com</h3>
              <p>A stronger central domain gives the SEO work a cleaner place to build authority, internal links, and topical depth.</p>
              <div class="stat-list">
                <div class="stat"><span>Domain authority</span><strong>{number(se.get("domain_authority"))}</strong></div>
                <div class="stat"><span>Domain rating</span><strong>{number(se.get("domain_rating"))}</strong></div>
                <div class="stat"><span>Referring domains</span><strong>{number(se.get("refdomain_count"))}</strong></div>
                <div class="stat"><span>Backlinks</span><strong>{number(se.get("backlinks"))}</strong></div>
              </div>
            </article>
            <article class="panel foundation">
              <h3>AI and search recognition are measurable</h3>
              <p>Search Atlas shows Airocide.com visibility in AI/search recognition signals, which supports the broader brand consolidation story.</p>
              <div class="stat-list">
                <div class="stat"><span>Current LLM mentions</span><strong>{number(current_llm)}</strong></div>
                <div class="stat"><span>Previous LLM mentions</span><strong>{number(se.get("llm_previous_mentions"))}</strong></div>
                <div class="stat"><span>Visibility change</span><strong>{llm_delta}</strong></div>
                <div class="stat"><span>Spam score</span><strong>{number(se.get("spam_score"))}</strong></div>
              </div>
            </article>
          </div>
          <p class="source-note">Search Atlas was used as the SEO visibility source for this report and had also served as a WordPress-connected optimization layer for page-level SEO, including title tags, metadata, content structure, keyword alignment, and on-page optimization.</p>
        </section>

        <section class="card">
          <h2>SEO Foundation Work Completed or Underway</h2>
          <ul class="progress-list">
            <li>Consolidating the website structure under Airocide.com so SEO value is focused on one authority destination.</li>
            <li>Separating the residential ecommerce experience through shop.airocide.com while keeping Airocide.com focused on brand, commercial, product, and category authority.</li>
            <li>Improving the commercial/residential structure so visitors have clearer pathways based on intent.</li>
            <li>Building SEO around Airocide Systems' core product categories, industry verticals, and business lines.</li>
            <li>Improving page structure, metadata, headings, internal linking, and technical SEO foundations.</li>
            <li>Using analytics behavior to identify where users engage, where they move toward Contact Us, and where the funnel may be leaking.</li>
            <li>Developing content direction for future blog and vertical SEO expansion.</li>
          </ul>
        </section>

        <section class="card">
          <h2>Website Behavior and Organic Lead Path</h2>
          <div class="grid-3">
            <article class="panel">
              <h3>Organic Search</h3>
              <p>Organic Search generated {number(organic.get("sessions"))} sessions, {number(organic.get("active_users"))} active users, {number(organic.get("key_events"))} key events, and {money(organic.get("revenue"), 0)} in tracked revenue during the consolidation reporting window.</p>
            </article>
            <article class="panel">
              <h3>Direct traffic</h3>
              <p>Direct traffic generated {number(direct.get("sessions"))} sessions and {money(direct.get("revenue"), 0)} in tracked revenue, supporting the brand-recognition side of the consolidation work.</p>
            </article>
            <article class="panel">
              <h3>AI Assistant traffic</h3>
              <p>GA4 is identifying AI Assistant traffic with {number(ai_channel.get("sessions"))} sessions and {number(ai_channel.get("key_events"))} key events. This is early but useful for monitoring AI-driven discovery.</p>
            </article>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Channel</th><th>Sessions</th><th>Active Users</th><th>Key Events</th><th>Revenue</th><th>Purchases</th></tr>
              </thead>
              <tbody>{channel_rows_html}
              </tbody>
            </table>
          </div>
        </section>

        <section class="card">
          <h2>Google Search Console Visibility</h2>
          <div class="grid-3">
            <article class="panel growth">
              <h3>Verified organic search demand</h3>
              <p>Search Console now provides direct Google visibility data for Airocide.com during the consolidation reporting window.</p>
              <div class="stat-list">
                <div class="stat"><span>Organic clicks</span><strong>{number(sc_summary.get("clicks"))}</strong></div>
                <div class="stat"><span>Search impressions</span><strong>{number(sc_summary.get("impressions"))}</strong></div>
                <div class="stat"><span>CTR</span><strong>{float(sc_summary.get("ctr") or 0) * 100:.1f}%</strong></div>
                <div class="stat"><span>Average position</span><strong>{float(sc_summary.get("position") or 0):.1f}</strong></div>
              </div>
            </article>
            <article class="panel seo">
              <h3>Top query signal</h3>
              <p>The top query list helps separate branded demand from commercial discovery and gives us a cleaner way to review whether consolidation is improving qualified visibility.</p>
            </article>
            <article class="panel foundation">
              <h3>Top page signal</h3>
              <p>The top page list shows where organic users are entering the site and helps prioritize commercial page structure, internal linking, and CTA improvements.</p>
            </article>
          </div>
          <div class="grid-2">
            <div class="table-wrap">
              <table>
                <thead>
                  <tr><th>Top Queries</th><th>Clicks</th><th>Impr.</th><th>CTR</th><th>Position</th></tr>
                </thead>
                <tbody>{query_rows_html}
                </tbody>
              </table>
            </div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr><th>Top Pages</th><th>Clicks</th><th>Impr.</th><th>CTR</th><th>Position</th></tr>
                </thead>
                <tbody>{page_rows_html}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section class="card">
          <h2>Conversion Tracking, Leads, and Phone Call Visibility</h2>
          <p class="summary">Conversion tracking has been strengthened on Airocide.com. GA4 is recording meaningful buyer and lead activity, including 373 homepage button clicks, 227 form starts, 76 form submissions, 42 purchases, and {money(13492, 0)} in tracked revenue during the consolidation reporting window.</p>
          <p class="summary">One important reporting limitation is phone-call attribution. Airocide.com displays a direct phone number, which is useful for visitors, but call tracking is not currently active. That means phone inquiries may be contributing to lead volume without being connected back to organic search, paid search, specific landing pages, or website content.</p>
          <div class="grid-3">
            <article class="panel growth">
              <h3>Lead activity is measurable</h3>
              <p>GA4 recorded 227 form starts and 76 form submissions, with 56 total users submitting forms. This confirms the website is producing measurable inquiry behavior, not only general traffic.</p>
            </article>
            <article class="panel foundation">
              <h3>Form storage is now in place</h3>
              <p>WPForms has been configured to store future form submissions in the website database, creating a cleaner lead reporting path going forward.</p>
            </article>
            <article class="panel seo">
              <h3>Phone calls may be underreported</h3>
              <p>Adding a tracking number would make reporting more complete by connecting phone inquiries to the same marketing channels being reviewed in GA4, Search Console, and future Google Ads reporting.</p>
            </article>
          </div>
          <p class="source-note">Historical WPForms entry recovery may be available if prior stored submissions are needed. Otherwise, reporting can move forward using newly stored form submissions from the current setup.</p>
        </section>

        <section class="card">
          <h2>Growth Infrastructure Assessment</h2>
          <p class="summary">Following the last discussion, I also reviewed the next layer of funnel management and lead infrastructure. The key question is not only how to generate more traffic, but how Airocide Systems will capture, organize, follow up with, and report on that demand once it reaches the website.</p>
          <p class="summary">Instantly is a strong outbound email platform, but it is more specialized around prospecting and email sequencing. Go High Level is broader and appears to be the better fit if the priority is managing inbound leads, form capture, workflows, SMS/email follow-up, advertising lead flow, and reporting in one place.</p>
          <div class="grid-2">
            <article class="panel seo">
              <h3>Instantly</h3>
              <p>Best fit for outbound email campaigns, inbox rotation, deliverability, sequencing, and prospecting workflows.</p>
            </article>
            <article class="panel growth">
              <h3>Go High Level</h3>
              <p>Better fit for form capture, contact management, automated follow-up workflows, email and text communication, audience organization, advertising integrations, and API-based reporting.</p>
            </article>
          </div>
        </section>

        <section class="card">
          <h2>Brand Protection Review</h2>
          <p class="summary">A second brand-protection review has been completed and organized for leadership/legal review. This phase moved beyond the initial "how it works / what can be done" discussion and into a more complete review of the Airocide Systems online footprint across Facebook, Instagram, domains, affiliate activity, and marketplace visibility.</p>
          <p class="summary">The review identified a broad legacy footprint using the Airocide name, logo, and country-specific positioning across multiple channels. The key issue is not only individual page misuse, but the possibility that older affiliate, distributor, or regional activity created a fragmented brand environment that now needs to be clarified and cleaned up.</p>
          <div class="highlight-band">
            <p class="summary">Brand protection directly supports the current SEO and brand-consolidation work. If users, search engines, or social platforms see multiple unofficial Airocide-branded pages, domains, and regional claims, it weakens the clarity of Airocide.com as the primary authority destination for Airocide Systems.</p>
          </div>
          <ul class="link-list">
            <li><span>Spreadsheet</span><a href="https://netorgft13443078-my.sharepoint.com/:x:/g/personal/mike_stott_marketing/IQAynFk1qqG4Rpi7CrWX8GqXAUVOSbvANh63jmri4fP_JrI?e=RcoZAa" target="_blank" rel="noopener">Airocide Systems Facebook Legal Ready Spreadsheet</a></li>
            <li><span>Language</span><a href="https://netorgft13443078-my.sharepoint.com/:t:/g/personal/mike_stott_marketing/IQBs0z6W7L9KT6o_22wpq5U8Aeve2PmPoqLwghBL7ZcywZ4?e=c1a6nr" target="_blank" rel="noopener">Airocide Systems Facebook Takedown Language</a></li>
            <li><span>Template</span><a href="https://netorgft13443078-my.sharepoint.com/:t:/g/personal/mike_stott_marketing/IQBj2ICIVJO8QrICd9LnvTLGAc3MVvz3jIUN4whw4lpHFCk?e=wNwUvW" target="_blank" rel="noopener">Airocide Systems Legal Declaration Template</a></li>
            <li><span>Research</span><a href="https://netorgft13443078-my.sharepoint.com/:x:/g/personal/mike_stott_marketing/IQDOemp8tMSDT5Jg7wxxCQAiASrHAJCaaz7J_8qHKPccs1g?e=5Y07X6" target="_blank" rel="noopener">Airocide Systems Brand Research Document</a></li>
          </ul>
          <p class="source-note">Supporting documentation is hosted in SharePoint so the sensitive detail remains outside the public report file while still being accessible for review.</p>
        </section>

        <section id="posted-updates-section" class="card" hidden>
          <h2>Current Updates</h2>
          <div id="posted-updates" class="posted-updates"></div>
          <ul id="dynamic-takeaways" class="dynamic-takeaways"></ul>
        </section>
      </main>
    </div>
{public_updates_script("airocide-systems")}
  </body>
</html>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page(), encoding="utf-8")
    print(f"Wrote Airocide Systems report to {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
