from __future__ import annotations

import html
import json
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
        --ink: #15222d;
        --muted: #65727e;
        --line: #dce5e7;
        --soft: #f5f8f9;
        --navy: #102f42;
        --teal: #0f8c8c;
        --green: #0d7b56;
        --gold: #a56b18;
        --white: #fff;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink);
        background: #f3f7f8;
      }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; min-height: 100vh; }}
      .app {{ width: min(1120px, calc(100% - 40px)); margin: 0 auto; padding: 26px 0 48px; }}
      .topbar {{ display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 20px; }}
      .brand {{ display: flex; align-items: center; gap: 14px; }}
      .brand-mark {{ display: grid; place-items: center; width: 58px; height: 58px; border-radius: 8px; background: var(--navy); color: #fff; font-weight: 900; }}
      .brand-copy strong {{ display: block; font-size: 19px; line-height: 1.2; }}
      .brand-copy small {{ display: block; margin-top: 4px; color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .pill {{ padding: 8px 12px; border: 1px solid #b9ddeb; border-radius: 999px; background: #edf8fc; color: #165d7d; font-size: 13px; font-weight: 800; white-space: nowrap; }}
      .hero {{ padding: 38px; border-radius: 8px; background: linear-gradient(135deg, #102f42, #155f72 64%, #0f8c8c); color: #fff; box-shadow: 0 18px 46px rgba(20, 54, 66, .16); }}
      .eyebrow {{ margin: 0 0 10px; color: #bcecf1; font-size: 13px; font-weight: 850; text-transform: uppercase; }}
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
      .foundation {{ border-left: 4px solid var(--teal); background: #effbfc; }}
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
        .hero-metrics, .grid-3, .grid-2 {{ grid-template-columns: 1fr; }}
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
            <small>SEO foundation report by Stott Marketing</small>
          </div>
        </div>
        <div class="pill">Private client update</div>
      </header>

      <section class="hero">
        <p class="eyebrow">Brand Consolidation SEO Update</p>
        <h1>Airocide.com is becoming the center of organic visibility.</h1>
        <p class="lede">Since April 1, 2026, the SEO work has focused on consolidating authority into Airocide.com, separating the residential ecommerce path at shop.airocide.com, and building the page structure needed for future commercial lead generation.</p>
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
          <p class="summary">The current SEO work is intentionally foundational. The priority has been to make Airocide.com the core authority destination, clarify the commercial and residential pathways, and organize the site around the product and industry categories that can support future organic lead generation. Search Atlas still has read-only project data available for this report, and it shows tracked keywords increasing from {number(april_keywords)} in April to {number(current_keywords)} currently, a {pct_change(april_keywords, current_keywords)} gain during the consolidation period.</p>
          <p class="summary">GA4 shows {number(ga.get("active_users"))} active users, {number(ga.get("sessions"))} sessions, {pct(ga.get("engagement_rate"))} engagement, and {number(ga.get("key_events"))} key events from {safe(period_label(refresh["period"]))}. Google Search Console is now connected for {safe(sc.get("site_url"))}, adding verified organic search performance to the report: {number(sc_summary.get("clicks"))} clicks, {number(sc_summary.get("impressions"))} impressions, {float(sc_summary.get("ctr") or 0) * 100:.1f}% CTR, and {float(sc_summary.get("position") or 0):.1f} average position.</p>
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
          <p class="source-note">Search Atlas was used as the SEO visibility source for this report. If the Search Atlas subscription is not restored, future visibility reporting should shift to GA4, Google Search Console, Clarity, and manually maintained keyword/content tracking.</p>
        </section>

        <section class="card">
          <h2>SEO Foundation Work Completed or Underway</h2>
          <ul class="progress-list">
            <li>Consolidating the website structure under Airocide.com so SEO value is focused on one authority destination.</li>
            <li>Separating the residential ecommerce experience through shop.airocide.com while keeping Airocide.com focused on brand, commercial, product, and category authority.</li>
            <li>Improving the commercial/residential structure so visitors have clearer pathways based on intent.</li>
            <li>Building SEO around Airocide Systems’ core product categories, industry verticals, and business lines.</li>
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
          <h2>Lead Reporting Standard</h2>
          <p class="summary">A submitted Contact Us form should be counted as a direct conversion. Commercial-intent visitors who do not submit a form should be reported separately as behavior signals, using page visits, Contact Us page activity, quote/contact CTA clicks, form starts, abandoned sessions, repeat visits, and Clarity recordings. That keeps the report useful without overstating anonymous traffic as named leads.</p>
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
