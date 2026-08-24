from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from public_update_renderer import add_posted_update_js, public_update_css, public_update_js_helpers


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "sjawc"
OUT = ROOT / "firebase-static" / "public" / "st-johns-aesthetics"
LOGO = OUT / "assets" / "sjawc-logo.png"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_optional(name: str) -> dict:
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def money(value: float | int | str, digits: int = 0) -> str:
    number = float(value or 0)
    return f"${number:,.{digits}f}"


def number(value: float | int | str, digits: int = 0) -> str:
    number_value = float(value or 0)
    return f"{number_value:,.{digits}f}"


def pct(value: float | int | str, digits: int = 1) -> str:
    return f"{float(value or 0) * 100:.{digits}f}%"


def pct_plain(value: float | int | str, digits: int = 1) -> str:
    return f"{float(value or 0):.{digits}f}%"


def safe(value: object) -> str:
    return html.escape(str(value), quote=True)


def trend_badge(current: float | int | str, previous: float | int | str) -> str:
    current_value = float(current or 0)
    previous_value = float(previous or 0)
    if previous_value == 0:
        return ""
    change = ((current_value - previous_value) / previous_value) * 100
    if change > 0:
        return f' <span style="color:#059669">↑ +{change:.1f}%</span>'
    if change < 0:
        return f' <span style="color:#dc2626">↓ {change:.1f}%</span>'
    return ' <span style="color:#6b7280">0.0%</span>'


def number_with_trend(current: float | int | str, previous: float | int | str, digits: int = 0) -> str:
    return f"{number(current, digits)}{trend_badge(current, previous)}"


def pct_with_trend(current: float | int | str, previous: float | int | str, digits: int = 1) -> str:
    return f"{pct(current, digits)}{trend_badge(current, previous)}"


def page() -> str:
    refresh = load("refresh_summary.json")
    ga4 = load("ga4.json")
    ga4_prev30 = load_optional("ga4_prev30.json")
    meta = load("meta.json")
    ghl = load("ghl.json")
    atlas = load("search_atlas.json")
    workbook = load("workbook.json")
    key_events = load_optional("ga4_key_events.json")
    key_events_prev30 = load_optional("ga4_key_events_prev30.json")
    gbp = load_optional("search_atlas_gbp_comparison.json")
    organic = load_optional("ga4_organic_content.json")

    period = refresh["period"]
    ga = ga4["metrics"]
    me = meta["metrics"]
    gh = ghl["metrics"]
    se = atlas["metrics"]
    roas = workbook["known_summary"]
    gbp_attrs = (((gbp.get("data") or {}).get("attributes") or {}))
    gbp_current = ((gbp_attrs.get("current_period") or {}).get("metrics") or {})
    gbp_comparison = gbp_attrs.get("comparison") or {}

    key_event_rows = key_events.get("rows") or []
    key_event_map = {
        row.get("dimensionValues", [{}])[0].get("value"): float(row.get("metricValues", [{}, {}])[0].get("value", 0) or 0)
        for row in key_event_rows
    }
    key_event_prev_rows = key_events_prev30.get("rows") or []
    key_event_prev_map = {
        row.get("dimensionValues", [{}])[0].get("value"): float(row.get("metricValues", [{}, {}])[0].get("value", 0) or 0)
        for row in key_event_prev_rows
    }
    lead_events = key_event_map.get("generate_lead", 0)
    purchase_events = key_event_map.get("purchase", 0)
    prev_lead_events = key_event_prev_map.get("generate_lead", 0)
    prev_purchase_events = key_event_prev_map.get("purchase", 0)
    ga_prev = ga4_prev30.get("metrics") or {}
    organic_values = [
        metric.get("value", 0)
        for metric in (((organic.get("organic_aggregate") or {}).get("rows") or [{}])[0].get("metricValues") or [])
    ]
    content_values = [
        metric.get("value", 0)
        for metric in (((organic.get("content_aggregate") or {}).get("rows") or [{}])[0].get("metricValues") or [])
    ]
    content_rows = ((organic.get("content_pages") or {}).get("rows") or [])
    top_content = content_rows[0] if content_rows else {}
    top_content_title = ((top_content.get("dimensionValues") or [{}, {}])[1].get("value") or "Top content page")
    top_content_views = ((top_content.get("metricValues") or [{}])[0].get("value") or 0)
    organic_sessions = organic_values[0] if len(organic_values) > 0 else 0
    organic_active_users = organic_values[1] if len(organic_values) > 1 else 0
    organic_engagement = organic_values[2] if len(organic_values) > 2 else 0
    organic_key_events = organic_values[3] if len(organic_values) > 3 else 0
    content_views = content_values[0] if len(content_values) > 0 else 0
    content_active_users = content_values[1] if len(content_values) > 1 else 0
    content_engagement = content_values[2] if len(content_values) > 2 else 0

    google_spend = roas.get("google_spend", 8800.00)
    google_profit = roas["google_revenue"] - google_spend
    entity_profit = roas["entity_revenue"] - roas["entity_spend"]
    llm_lift = ((se["llm_current_mentions"] - se["llm_previous_mentions"]) / se["llm_previous_mentions"]) * 100
    ghl_facebook_ytd = gh.get("facebook_ytd") or {}
    meta_ytd_opportunities = float(ghl_facebook_ytd.get("opportunities") or 129)
    meta_ytd_appointment_stage = float(ghl_facebook_ytd.get("appointment_stage_opportunities") or 19)
    meta_ytd_appointment_rate = meta_ytd_appointment_stage / meta_ytd_opportunities * 100
    meta_ytd_buyer_rate = roas["meta_buyers"] / meta_ytd_opportunities * 100

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow, noarchive">
    <title>SJAWC Executive Marketing Performance | Stott Marketing</title>
    <style>
      :root {{
        color-scheme: light;
        --ink: #17212b;
        --muted: #65727e;
        --line: #dce5e7;
        --soft: #f6f9fa;
        --aqua: #58bdc7;
        --aqua-dark: #126a74;
        --navy: #152938;
        --green: #0d7b56;
        --gold: #b7791f;
        --white: #fff;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink);
        background: #f4f8f9;
      }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; min-height: 100vh; background: #f4f8f9; }}
      .app {{ width: min(1120px, calc(100% - 40px)); margin: 0 auto; padding: 26px 0 48px; }}
      .topbar {{ display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 20px; }}
      .brand {{ display: flex; align-items: center; gap: 15px; min-width: 0; }}
      .brand img {{ width: 78px; height: 64px; object-fit: contain; }}
      .brand-copy strong {{ display: block; font-family: Georgia, "Times New Roman", serif; font-size: 18px; line-height: 1.2; }}
      .brand-copy small {{ display: block; margin-top: 4px; color: var(--muted); font-weight: 700; font-size: 12px; letter-spacing: .02em; text-transform: uppercase; }}
      .pill {{ padding: 8px 12px; border: 1px solid #bfe5e8; border-radius: 999px; background: #effbfc; color: var(--aqua-dark); font-size: 13px; font-weight: 800; white-space: nowrap; }}
      .hero {{ position: relative; overflow: hidden; padding: 38px; border-radius: 8px; background: linear-gradient(135deg, #102331, #173544 62%, #0d5964); color: #fff; box-shadow: 0 18px 46px rgba(20, 54, 66, .16); }}
      .hero::after {{ content: ""; position: absolute; right: -70px; top: -90px; width: 280px; height: 280px; border: 44px solid rgba(88, 189, 199, .28); border-radius: 999px; }}
      .hero > * {{ position: relative; z-index: 1; }}
      .eyebrow {{ margin: 0 0 10px; color: #bcecf1; font-size: 13px; font-weight: 850; text-transform: uppercase; }}
      h1, h2, h3, p {{ margin-top: 0; }}
      h1 {{ max-width: 820px; margin-bottom: 12px; font-family: Georgia, "Times New Roman", serif; font-size: clamp(38px, 5.8vw, 62px); line-height: 1; font-weight: 500; }}
      .hero p.lede {{ max-width: 820px; margin-bottom: 26px; color: rgba(255,255,255,.82); font-size: 18px; line-height: 1.58; }}
      .hero-metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; overflow: hidden; border: 1px solid rgba(255,255,255,.16); border-radius: 8px; background: rgba(255,255,255,.18); }}
      .hero-metric {{ min-height: 126px; padding: 17px; background: rgba(255,255,255,.09); }}
      .hero-metric span {{ display: block; margin-bottom: 8px; color: rgba(255,255,255,.68); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .hero-metric strong {{ display: block; margin-bottom: 8px; font-size: 28px; }}
      .hero-metric small {{ color: rgba(255,255,255,.76); line-height: 1.4; }}
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
      .highlight {{ border-left: 4px solid var(--aqua); background: #effbfc; }}
      .revenue {{ border-left: 4px solid var(--green); background: #f1fbf6; }}
      .seo {{ border-left: 4px solid var(--gold); background: #fff9ed; }}
      .status {{ display: flex; align-items: flex-start; gap: 10px; margin-top: 16px; padding: 14px; border: 1px solid #d6eadf; border-radius: 8px; background: #f2fbf6; color: #2c6047; line-height: 1.5; }}
      .dot {{ width: 9px; height: 9px; margin-top: 6px; border-radius: 999px; background: var(--green); flex: 0 0 auto; }}
      .source-note {{ margin-top: 14px; color: var(--muted); font-size: 12px; line-height: 1.5; }}
      .meeting-takeaways {{
        display: grid;
        gap: 10px;
        margin: 0;
        padding: 0;
        list-style: none;
      }}
      .meeting-takeaways li {{
        display: grid;
        grid-template-columns: 24px 1fr;
        gap: 11px;
        align-items: start;
        padding: 12px 0;
        border-top: 1px solid var(--line);
        color: #3f4c56;
        line-height: 1.5;
      }}
      .meeting-takeaways li:first-child {{
        border-top: 0;
        padding-top: 0;
      }}
      .meeting-takeaways .box {{
        width: 18px;
        height: 18px;
        margin-top: 2px;
        border: 2px solid #95a8b3;
        border-radius: 4px;
        background: #fff;
      }}
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
          <img src="/st-johns-aesthetics/assets/sjawc-logo.png" alt="St. Johns Aesthetics and Wellness Center logo">
          <div class="brand-copy">
            <strong>St. Johns Aesthetics &amp; Wellness Center</strong>
            <small>Executive performance report by Stott Marketing</small>
          </div>
        </div>
        <div class="pill">Private client update</div>
      </header>

      <section class="hero">
        <p class="eyebrow">Executive Marketing Performance</p>
        <h1>Revenue, lead generation, and SEO visibility are working together.</h1>
        <p class="lede">The strongest story for this update is business impact: paid search is producing confirmed revenue at a very strong return, EntityMed is also positive on matched revenue, and organic visibility has a measurable SEO foundation through Search Atlas keyword and authority tracking.</p>
        <div class="hero-metrics">
          <div class="hero-metric"><span>Google Ads ROAS</span><strong>{number(roas['google_roas'], 2)}x</strong><small>{money(roas['google_revenue'], 2)} confirmed YTD revenue</small></div>
          <div class="hero-metric"><span>EntityMed ROAS</span><strong>{number(roas['entity_roas'], 2)}x</strong><small>{money(roas['entity_revenue'], 2)} confirmed revenue</small></div>
          <div class="hero-metric"><span>Tracked Keywords</span><strong>{number(se['keyword_count'])}</strong><small>{number(se['top_3_keywords_count'])} ranking in top 3 positions</small></div>
          <div class="hero-metric"><span>LLM Visibility</span><strong>{number(se['llm_current_mentions'])}</strong><small>Up {number(llm_lift, 1)}% from previous</small></div>
        </div>
      </section>

      <main>
        <section class="card">
          <h2>Executive Summary</h2>
          <p class="summary">The strongest revenue signal in this report is Google Ads. Based on the Boulevard revenue match, Google Ads is connected to {money(roas['google_revenue'], 2)} in confirmed revenue and a {number(roas['google_roas'], 2)}x ROAS. ROAS means return on ad spend, so a {number(roas['google_roas'], 2)}x return means every aligned dollar of Google Ads spend is tied to more than {money(roas['google_roas'], 2)} in confirmed revenue. That is a very strong performance indicator, especially because the match also shows approximately {money(google_profit, 2)} in revenue above spend. EntityMed is also producing a positive revenue story, with {money(roas['entity_revenue'], 2)} in confirmed revenue and {number(roas['entity_roas'], 2)}x ROAS.</p>
          <p class="summary">The supporting performance data is also useful. The website recorded {number(ga['active_users'])} active users, {number(ga['key_events'])} key events, and a {pct(ga['engagement_rate'])} engagement rate, including {number(lead_events)} lead-generation key events and {number(purchase_events)} purchase key events in GA4. Facebook and Instagram show a clearer YTD funnel in GoHighLevel, with {number(meta_ytd_opportunities)} Facebook form pipeline opportunities, {number(meta_ytd_appointment_stage)} appointment-stage opportunities, and {number(roas['meta_buyers'])} purchasing clients confirmed in the Boulevard match. Search Atlas shows a solid SEO footprint with {number(se['keyword_count'])} tracked keywords, {number(se['top_3_keywords_count'])} top-3 rankings in the tracked keyword set, {number(se['backlinks'])} backlinks, and a site health score of {number(se['site_health'])}.</p>
        </section>

        <section class="card">
          <h2>Revenue Performance</h2>
          <div class="grid-3">
            <article class="panel revenue">
              <h3>Google Ads: strongest confirmed return</h3>
              <p>Paid search is the standout revenue channel in the matched workbook, showing strong buyer quality and efficient confirmed revenue generation.</p>
              <div class="stat-list">
                <div class="stat"><span>Confirmed YTD revenue</span><strong>{money(roas['google_revenue'], 2)}</strong></div>
                <div class="stat"><span>YTD spend</span><strong>{money(google_spend, 2)}</strong></div>
                <div class="stat"><span>ROAS</span><strong>{number(roas['google_roas'], 2)}x</strong></div>
                <div class="stat"><span>Purchasing clients</span><strong>73</strong></div>
                <div class="stat"><span>YTD revenue above spend</span><strong>{money(google_profit, 2)}</strong></div>
              </div>
            </article>
            <article class="panel revenue">
              <h3>Facebook &amp; Instagram: active lead channel</h3>
              <p>Meta is included in the revenue view because it is producing measurable YTD lead volume and a trackable appointment-to-revenue funnel.</p>
              <div class="stat-list">
                <div class="stat"><span>YTD opportunities</span><strong>{number(meta_ytd_opportunities)}</strong></div>
                <div class="stat"><span>Appointment-stage opportunities</span><strong>{number(meta_ytd_appointment_stage)}</strong></div>
                <div class="stat"><span>Confirmed YTD revenue</span><strong>{money(roas['meta_revenue'], 2)}</strong></div>
                <div class="stat"><span>YTD spend</span><strong>{money(3600, 2)}</strong></div>
                <div class="stat"><span>ROAS</span><strong>{number(roas['meta_roas'], 2)}x</strong></div>
                <div class="stat"><span>Appointment-stage rate</span><strong>{number(meta_ytd_appointment_rate, 1)}%</strong></div>
                <div class="stat"><span>Buyer rate</span><strong>{number(meta_ytd_buyer_rate, 1)}%</strong></div>
              </div>
            </article>
            <article class="panel revenue">
              <h3>EntityMed: positive matched revenue</h3>
              <p>EntityMed is producing confirmed patient value with a positive return profile and a clean aggregate attribution story.</p>
              <div class="stat-list">
                <div class="stat"><span>Confirmed YTD revenue</span><strong>{money(roas['entity_revenue'], 2)}</strong></div>
                <div class="stat"><span>YTD spend</span><strong>{money(roas['entity_spend'], 2)}</strong></div>
                <div class="stat"><span>ROAS</span><strong>{number(roas['entity_roas'], 2)}x</strong></div>
                <div class="stat"><span>Purchasing clients</span><strong>{number(roas['entity_buyers'])}</strong></div>
                <div class="stat"><span>YTD revenue above spend</span><strong>{money(entity_profit, 2)}</strong></div>
              </div>
            </article>
          </div>
        </section>

        <section class="card">
          <h2>SEO, Content, and AI Visibility</h2>
          <div class="grid-3">
            <article class="panel seo">
              <h3>Search Atlas ranking profile</h3>
              <p>The SEO foundation is measurable: SJAWC is being tracked across a meaningful keyword set, with top-position visibility already present and authority signals in place. The top-3 count is presented as a ranking-health indicator from the tracked keyword set.</p>
              <div class="stat-list">
                <div class="stat"><span>Tracked organic keywords</span><strong>{number(se['keyword_count'])}</strong></div>
                <div class="stat"><span>Top 3 keyword rankings</span><strong>{number(se['top_3_keywords_count'])}</strong></div>
                <div class="stat"><span>Site health</span><strong>{number(se['site_health'])}</strong></div>
                <div class="stat"><span>Referring domains</span><strong>{number(se['refdomain_count'])}</strong></div>
              </div>
            </article>
            <article class="panel seo">
              <h3>LLM visibility is growing</h3>
              <p>Search Atlas is showing stronger visibility in AI-driven discovery, which is increasingly important as people use AI tools alongside traditional search.</p>
              <div class="stat-list">
                <div class="stat"><span>LLM mentions</span><strong>{number(se['llm_current_mentions'])}</strong></div>
                <div class="stat"><span>Previous mentions</span><strong>{number(se['llm_previous_mentions'])}</strong></div>
                <div class="stat"><span>Visibility lift</span><strong>{number(llm_lift, 1)}%</strong></div>
                <div class="stat"><span>Backlinks</span><strong>{number(se['backlinks'])}</strong></div>
              </div>
            </article>
            <article class="panel seo">
              <h3>Organic content performance</h3>
              <p>GA4 shows organic search and blog content creating engaged site activity, which helps connect SEO work to actual website behavior.</p>
              <div class="stat-list">
                <div class="stat"><span>Organic sessions</span><strong>{number(organic_sessions)}</strong></div>
                <div class="stat"><span>Organic engagement</span><strong>{pct(organic_engagement)}</strong></div>
                <div class="stat"><span>Organic key events</span><strong>{number(organic_key_events)}</strong></div>
                <div class="stat"><span>Blog/resource views</span><strong>{number(content_views)}</strong></div>
                <div class="stat"><span>Top content views</span><strong>{number(top_content_views)}</strong></div>
              </div>
            </article>
          </div>
          <p class="source-note">Top content page in the connected period: {safe(top_content_title)}.</p>
        </section>

        <section class="card">
          <h2>Current Channel Performance</h2>
          <div class="grid-3">
            <article class="panel">
              <h3>Website engagement and conversions</h3>
              <p>The site is producing measurable engagement and conversion activity during the latest connected window.</p>
              <div class="stat-list">
                <div class="stat"><span>Active users</span><strong>{number_with_trend(ga['active_users'], ga_prev.get('active_users'))}</strong></div>
                <div class="stat"><span>Sessions</span><strong>{number_with_trend(ga['sessions'], ga_prev.get('sessions'))}</strong></div>
                <div class="stat"><span>Engagement rate</span><strong>{pct_with_trend(ga['engagement_rate'], ga_prev.get('engagement_rate'))}</strong></div>
                <div class="stat"><span>Lead key events</span><strong>{number_with_trend(lead_events, prev_lead_events)}</strong></div>
                <div class="stat"><span>Purchase key events</span><strong>{number_with_trend(purchase_events, prev_purchase_events)}</strong></div>
              </div>
            </article>
            <article class="panel">
              <h3>Meta lead activity</h3>
              <p>Facebook and Instagram continue to support reach, engagement, and lead generation, adding social visibility to the channel mix.</p>
              <div class="stat-list">
                <div class="stat"><span>Spend</span><strong>{money(me['spend'], 2)}</strong></div>
                <div class="stat"><span>Leads</span><strong>{number(me['leads'])}</strong></div>
                <div class="stat"><span>Reach</span><strong>{number(me['reach'])}</strong></div>
                <div class="stat"><span>Link clicks</span><strong>{number(me['link_clicks'])}</strong></div>
                <div class="stat"><span>Video views</span><strong>{number(me['video_views'])}</strong></div>
              </div>
            </article>
            <article class="panel">
              <h3>Google Business Profile</h3>
              <p>The connected business profile data adds a local visibility layer to the marketing story.</p>
              <div class="stat-list">
                <div class="stat"><span>GBP score</span><strong>{number(gbp_current.get('gbp_score', 0))}</strong></div>
                <div class="stat"><span>Citation score</span><strong>{number(gbp_current.get('citation_score', 0))}</strong></div>
                <div class="stat"><span>Rating</span><strong>{number(gbp_current.get('rating', 0), 1)}</strong></div>
                <div class="stat"><span>Direction requests</span><strong>{number(gbp_current.get('direction_requests', 0))}</strong></div>
                <div class="stat"><span>Direction request change</span><strong>{number(((gbp_comparison.get('direction_requests') or {}).get('percent_change') or 0), 1)}%</strong></div>
              </div>
            </article>
          </div>
        </section>

        <section class="card">
          <h2>Meeting Takeaways - July 1, 2026</h2>
          <ul id="meeting-takeaway-list" class="meeting-takeaways">
            <li><span class="box" aria-hidden="true"></span><span>Add Taylor’s profile to the website</span></li>
            <li><span class="box" aria-hidden="true"></span><span>Redesign financing page with package examples and 0% APR messaging</span></li>
            <li><span class="box" aria-hidden="true"></span><span>Add Botox, Dysport, and Xeomin sub-line to New Patient Offer page</span></li>
            <li><span class="box" aria-hidden="true"></span><span>Embed microneedling video on the service page</span></li>
            <li><span class="box" aria-hidden="true"></span><span>Refine banner design with softer blended edge treatment</span></li>
            <li><span class="box" aria-hidden="true"></span><span>Build monthly lead-to-consult and consult-to-treatment trend report by source</span></li>
            <li><span class="box" aria-hidden="true"></span><span>Develop Christmas in July promotion assets and ManyChat trigger flow</span></li>
            <li><span class="box" aria-hidden="true"></span><span>Create life-event campaign concepts for Mother of the Bride, reunions, and business events</span></li>
            <li><span class="box" aria-hidden="true"></span><span>Set up automated re-engagement workflow for lapsed clients</span></li>
            <li><span class="box" aria-hidden="true"></span><span>Share new website draft link for image/content review</span></li>
            <li><span class="box" aria-hidden="true"></span><span>Review Meta lead quality and buyer conversion rate</span></li>
            <li><span class="box" aria-hidden="true"></span><span>Build higher-intent aesthetic package campaign strategy</span></li>
          </ul>
        </section>

        <section id="posted-updates-section" class="card" hidden>
          <h2>Current Updates</h2>
          <div id="posted-updates" class="posted-updates"></div>
        </section>
      </main>
    </div>
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

      function textNode(value) {{
        return document.createTextNode(value || "");
      }}

{public_update_js_helpers()}

      function addMeetingTakeaway(text, completed) {{
        const list = document.querySelector("#meeting-takeaway-list");
        const item = document.createElement("li");
        const box = document.createElement("span");
        box.className = "box";
        box.setAttribute("aria-hidden", "true");
        const label = document.createElement("span");
        label.append(textNode(text));
        if (completed) label.style.textDecoration = "line-through";
        item.append(box, label);
        list.append(item);
      }}

{add_posted_update_js(show_section_call='document.querySelector("#posted-updates-section").hidden = false;')}

      async function loadPostedUpdates() {{
        try {{
          const snapshot = await getDocs(query(
            collection(db, "clientPublicUpdates", "st-johns-aesthetics", "items"),
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
          console.error("Could not load posted client updates", error);
        }}
      }}

      loadPostedUpdates();
    </script>
  </body>
</html>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    # Keep the live downloaded logo if present. If not, leave the path for deployment checks to catch.
    (OUT / "index.html").write_text(page(), encoding="utf-8")
    print(f"Wrote executive SJAWC report to {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
