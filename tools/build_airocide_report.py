from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from public_update_renderer import add_posted_update_js, public_update_css, public_update_js_helpers


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "airocide"
OUT = ROOT / "firebase-static" / "public" / "airocide"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


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
    return f"{float(value or 0):,.{digits}f}"


def pct(value: float | int | str, digits: int = 1) -> str:
    return f"{float(value or 0) * 100:.{digits}f}%"


def pct_plain(value: float | int | str, digits: int = 1) -> str:
    return f"{float(value or 0):.{digits}f}%"


def safe(value: object) -> str:
    return html.escape(str(value), quote=True)


def period_label(period: dict) -> str:
    start = period.get("start") or ""
    end = period.get("end") or ""
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        return f"{start} to {end}".strip(" to")
    if start_date.year == end_date.year:
        return f"{start_date.strftime('%b')} {start_date.day} - {end_date.strftime('%b')} {end_date.day}, {end_date.year}"
    return f"{start_date.strftime('%b')} {start_date.day}, {start_date.year} - {end_date.strftime('%b')} {end_date.day}, {end_date.year}"


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


def atlas_card(project: dict) -> str:
    metrics = project.get("metrics") or {}
    domain = project.get("domain") or "Airocide domain"
    current = float(metrics.get("llm_current_mentions") or 0)
    previous = float(metrics.get("llm_previous_mentions") or 0)
    llm_delta = ((current - previous) / previous * 100) if previous else 0
    return f"""
            <article class="panel seo">
              <h3>{safe(domain)}</h3>
              <p>{safe(project.get("ai_summary") or "Search Atlas is connected for SEO and authority tracking.")}</p>
              <div class="stat-list">
                <div class="stat"><span>Tracked keywords</span><strong>{number(metrics.get("keyword_count"))}</strong></div>
                <div class="stat"><span>Top-3 rankings</span><strong>{number(metrics.get("top_3_keywords_count"))}</strong></div>
                <div class="stat"><span>Organic traffic estimate</span><strong>{number(metrics.get("organic_traffic"))}</strong></div>
                <div class="stat"><span>Referring domains</span><strong>{number(metrics.get("refdomain_count"))}</strong></div>
                <div class="stat"><span>Backlinks</span><strong>{number(metrics.get("backlinks"))}</strong></div>
                <div class="stat"><span>LLM visibility</span><strong>{number(current)} <small>({pct_plain(llm_delta)})</small></strong></div>
              </div>
            </article>
"""


def page() -> str:
    refresh = load("refresh_summary.json")
    ga4 = load("ga4.json")
    ga4_ytd = load("ga4_ytd.json")
    channels = channel_rows(load("ga4_channels.json"))
    additional = load("ga4_additional.json")
    meta = load("meta.json")
    atlas = load("search_atlas.json")

    period = refresh["period"]
    ytd_period = refresh["ytd_period"]
    ga = ga4["metrics"]
    ga_ytd = ga4_ytd["metrics"]
    me = meta["metrics"]
    atlas_domains = atlas.get("domains") or []
    primary_atlas = atlas_domains[0] if atlas_domains else {"metrics": {}}
    secondary_atlas = atlas_domains[1] if len(atlas_domains) > 1 else {"metrics": {}}
    primary_se = primary_atlas.get("metrics") or {}
    secondary_se = secondary_atlas.get("metrics") or {}
    total_keywords = float(primary_se.get("keyword_count") or 0) + float(secondary_se.get("keyword_count") or 0)
    total_top3 = float(primary_se.get("top_3_keywords_count") or 0) + float(secondary_se.get("top_3_keywords_count") or 0)
    total_backlinks = float(primary_se.get("backlinks") or 0) + float(secondary_se.get("backlinks") or 0)
    total_refdomains = float(primary_se.get("refdomain_count") or 0) + float(secondary_se.get("refdomain_count") or 0)
    total_llm_current = float(primary_se.get("llm_current_mentions") or 0) + float(secondary_se.get("llm_current_mentions") or 0)
    total_llm_previous = float(primary_se.get("llm_previous_mentions") or 0) + float(secondary_se.get("llm_previous_mentions") or 0)
    llm_lift = ((total_llm_current - total_llm_previous) / total_llm_previous * 100) if total_llm_previous else 0
    top_channel = channels[0] if channels else {"channel": "Direct", "sessions": 0, "revenue": 0, "purchases": 0}
    organic = next((row for row in channels if row["channel"] == "Organic Search"), None)
    direct = next((row for row in channels if row["channel"] == "Direct"), None)
    ai_channel = next((row for row in channels if row["channel"] == "AI Assistant"), None)
    legacy = additional.get("corporate_or_legacy") or {}
    dealer = additional.get("dealer_portal") or {}
    dealer_metrics = dealer.get("metrics") or {}
    legacy_metrics = legacy.get("metrics") or {}

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
    <title>Airocide Client Update | Stott Marketing</title>
    <style>
      :root {{
        color-scheme: light;
        --ink: #14232f;
        --muted: #64717f;
        --line: #dbe4e8;
        --soft: #f5f8f9;
        --blue: #1f6f9f;
        --teal: #0f8c8c;
        --green: #107a4d;
        --gold: #a56b18;
        --white: #fff;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink);
        background: #f3f7f8;
      }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; min-height: 100vh; background: #f3f7f8; }}
      .app {{ width: min(1120px, calc(100% - 40px)); margin: 0 auto; padding: 26px 0 48px; }}
      .topbar {{ display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 20px; }}
      .brand {{ display: flex; align-items: center; gap: 14px; }}
      .brand-mark {{ display: grid; place-items: center; width: 58px; height: 58px; border-radius: 8px; background: #102f42; color: #fff; font-weight: 900; letter-spacing: .08em; }}
      .brand-copy strong {{ display: block; font-size: 19px; line-height: 1.2; }}
      .brand-copy small {{ display: block; margin-top: 4px; color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .pill {{ padding: 8px 12px; border: 1px solid #b9ddeb; border-radius: 999px; background: #edf8fc; color: #165d7d; font-size: 13px; font-weight: 800; white-space: nowrap; }}
      .hero {{ position: relative; overflow: hidden; padding: 38px; border-radius: 8px; background: linear-gradient(135deg, #102f42, #155f72 64%, #0f8c8c); color: #fff; box-shadow: 0 18px 46px rgba(20, 54, 66, .16); }}
      .eyebrow {{ margin: 0 0 10px; color: #bcecf1; font-size: 13px; font-weight: 850; text-transform: uppercase; }}
      h1, h2, h3, p {{ margin-top: 0; }}
      h1 {{ max-width: 860px; margin-bottom: 12px; font-size: clamp(36px, 5.6vw, 60px); line-height: 1; font-weight: 720; letter-spacing: 0; }}
      .hero p.lede {{ max-width: 850px; margin-bottom: 26px; color: rgba(255,255,255,.84); font-size: 18px; line-height: 1.58; }}
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
      .revenue {{ border-left: 4px solid var(--green); background: #f1fbf6; }}
      .seo {{ border-left: 4px solid var(--gold); background: #fff9ed; }}
      .media {{ border-left: 4px solid var(--blue); background: #f2f8fc; }}
      table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
      th, td {{ padding: 11px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
      th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
      .source-note {{ margin-top: 14px; color: var(--muted); font-size: 12px; line-height: 1.5; }}
      .dynamic-takeaways {{ display: grid; gap: 10px; margin: 14px 0 0; padding: 0; list-style: none; }}
      .dynamic-takeaways li {{ display: grid; grid-template-columns: 22px 1fr; gap: 10px; align-items: start; padding: 10px 0; border-top: 1px solid var(--line); color: #3f4c56; line-height: 1.5; }}
      .dynamic-takeaways .box {{ width: 17px; height: 17px; margin-top: 3px; border: 2px solid #95a8b3; border-radius: 4px; background: #fff; }}
{public_update_css(text_color="#3f4c56", line_color="var(--line)")}
      @media (max-width: 820px) {{
        .app {{ width: min(100% - 24px, 1120px); }}
        .topbar {{ align-items: flex-start; flex-direction: column; }}
        .hero, .card {{ padding: 21px; }}
        .hero-metrics, .grid-3, .grid-2 {{ grid-template-columns: 1fr; }}
      }}
      @media (min-width: 821px) and (max-width: 1040px) {{
        .hero-metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        .grid-3 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      }}
    </style>
  </head>
  <body>
    <div class="app">
      <header class="topbar">
        <div class="brand">
          <div class="brand-mark">AIR</div>
          <div class="brand-copy">
            <strong>Airocide Systems</strong>
            <small>Client performance portal by Stott Marketing</small>
          </div>
        </div>
        <div class="pill">Private client update</div>
      </header>

      <section class="hero">
        <p class="eyebrow">Connected Marketing Performance</p>
        <h1>Website revenue and organic visibility are now measurable.</h1>
        <p class="lede">This first Airocide portal view connects GA4, Meta Ads, and Search Atlas so current performance can be reviewed from one private client page. The strongest immediate signal is website commerce activity, supported by meaningful SEO authority and AI visibility across the Airocide domain portfolio.</p>
        <div class="hero-metrics">
          <div class="hero-metric"><span>Last 30 Days Revenue</span><strong>{compact_money(ga.get("total_revenue"))}</strong><small>{number(ga.get("ecommerce_purchases"))} ecommerce purchases</small></div>
          <div class="hero-metric"><span>YTD Revenue</span><strong>{compact_money(ga_ytd.get("total_revenue"))}</strong><small>{number(ga_ytd.get("ecommerce_purchases"))} ecommerce purchases</small></div>
          <div class="hero-metric"><span>Tracked Keywords</span><strong>{number(total_keywords)}</strong><small>{number(total_top3)} ranking in top 3 positions</small></div>
          <div class="hero-metric"><span>LLM Visibility</span><strong>{number(total_llm_current)}</strong><small>{pct_plain(llm_lift)} vs previous</small></div>
        </div>
      </section>

      <main>
        <section class="card">
          <h2>Executive Summary</h2>
          <p class="summary">For {safe(period_label(period))}, the connected Airocide GA4 property recorded {number(ga.get("active_users"))} active users, {number(ga.get("sessions"))} sessions, {pct(ga.get("engagement_rate"))} engagement, {number(ga.get("key_events"))} key events, and {money(ga.get("total_revenue"), 0)} in tracked revenue from {number(ga.get("ecommerce_purchases"))} ecommerce purchases. Year to date, GA4 shows {money(ga_ytd.get("total_revenue"), 0)} in tracked revenue from {number(ga_ytd.get("ecommerce_purchases"))} ecommerce purchases.</p>
          <p class="summary">Search Atlas is connected for both airocidesystems.com and airocide.com, showing {number(total_keywords)} tracked keywords, {number(total_top3)} top-3 keyword rankings, {number(total_refdomains)} referring domains, {number(total_backlinks)} backlinks, and {number(total_llm_current)} current LLM mentions. Meta Ads access is connected for the Airocide ad account, with no spend or delivery recorded in the latest connected window.</p>
        </section>

        <section class="card">
          <h2>Revenue and Website Activity</h2>
          <div class="grid-3">
            <article class="panel revenue">
              <h3>Main GA4 property</h3>
              <p>The primary Airocide property is showing measurable ecommerce activity in the current reporting window.</p>
              <div class="stat-list">
                <div class="stat"><span>Revenue</span><strong>{money(ga.get("total_revenue"), 0)}</strong></div>
                <div class="stat"><span>Purchases</span><strong>{number(ga.get("ecommerce_purchases"))}</strong></div>
                <div class="stat"><span>Active users</span><strong>{number(ga.get("active_users"))}</strong></div>
                <div class="stat"><span>Sessions</span><strong>{number(ga.get("sessions"))}</strong></div>
                <div class="stat"><span>Engagement rate</span><strong>{pct(ga.get("engagement_rate"))}</strong></div>
              </div>
            </article>
            <article class="panel revenue">
              <h3>Year-to-date view</h3>
              <p>The YTD view gives the client a stable benchmark for commerce impact as future updates build history.</p>
              <div class="stat-list">
                <div class="stat"><span>YTD revenue</span><strong>{money(ga_ytd.get("total_revenue"), 0)}</strong></div>
                <div class="stat"><span>YTD purchases</span><strong>{number(ga_ytd.get("ecommerce_purchases"))}</strong></div>
                <div class="stat"><span>YTD active users</span><strong>{number(ga_ytd.get("active_users"))}</strong></div>
                <div class="stat"><span>YTD sessions</span><strong>{number(ga_ytd.get("sessions"))}</strong></div>
                <div class="stat"><span>YTD engagement</span><strong>{pct(ga_ytd.get("engagement_rate"))}</strong></div>
              </div>
            </article>
            <article class="panel media">
              <h3>Meta Ads connection</h3>
              <p>The Meta ad account is reachable by API. The latest period currently shows no active delivery.</p>
              <div class="stat-list">
                <div class="stat"><span>Spend</span><strong>{money(me.get("spend"), 2)}</strong></div>
                <div class="stat"><span>Impressions</span><strong>{number(me.get("impressions"))}</strong></div>
                <div class="stat"><span>Clicks</span><strong>{number(me.get("clicks"))}</strong></div>
                <div class="stat"><span>Leads</span><strong>{number(me.get("leads"))}</strong></div>
                <div class="stat"><span>ROAS</span><strong>{number(me.get("roas"), 2)}x</strong></div>
              </div>
            </article>
          </div>
        </section>

        <section class="card">
          <h2>Channel Performance</h2>
          <div class="grid-3">
            <article class="panel">
              <h3>Top source: {safe(top_channel["channel"])}</h3>
              <p>The leading channel by sessions is currently {safe(top_channel["channel"])}, with {number(top_channel["sessions"])} sessions and {money(top_channel["revenue"], 0)} in tracked revenue.</p>
            </article>
            <article class="panel">
              <h3>Organic Search</h3>
              <p>Organic Search generated {number((organic or {}).get("sessions"))} sessions, {number((organic or {}).get("key_events"))} key events, and {money((organic or {}).get("revenue"), 0)} in tracked revenue.</p>
            </article>
            <article class="panel">
              <h3>AI Assistant traffic</h3>
              <p>GA4 is already identifying AI Assistant traffic: {number((ai_channel or {}).get("sessions"))} sessions, {number((ai_channel or {}).get("key_events"))} key event, and {money((ai_channel or {}).get("revenue"), 0)} in tracked revenue.</p>
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
          <h2>SEO and AI Visibility</h2>
          <div class="grid-2">
{''.join(atlas_card(project) for project in atlas_domains)}
          </div>
          <p class="source-note">Search Atlas data is read-only and reflects existing project data for the connected Airocide domains.</p>
        </section>

        <section class="card">
          <h2>Additional Connected Properties</h2>
          <div class="grid-2">
            <article class="panel">
              <h3>Corporate / legacy property</h3>
              <p>Additional GA4 property {safe(legacy.get("property_id") or "not available")} recorded {number(legacy_metrics.get("active_users"))} active users, {number(legacy_metrics.get("sessions"))} sessions, and {money(legacy_metrics.get("total_revenue"), 0)} in revenue.</p>
            </article>
            <article class="panel">
              <h3>Dealer portal property</h3>
              <p>Additional GA4 property {safe(dealer.get("property_id") or "not available")} is mapped. No reporting rows were returned in the latest connected window.</p>
            </article>
          </div>
        </section>

        <section id="posted-updates-section" class="card" hidden>
          <h2>Current Updates</h2>
          <div id="posted-updates" class="posted-updates"></div>
          <ul id="dynamic-takeaways" class="dynamic-takeaways"></ul>
        </section>
      </main>
    </div>
{public_updates_script("airocide")}
  </body>
</html>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page(), encoding="utf-8")
    print(f"Wrote Airocide report to {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
