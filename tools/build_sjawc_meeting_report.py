from __future__ import annotations

import html
import json
import shutil
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "sjawc"
OUT = ROOT / "firebase-static" / "public" / "st-johns-aesthetics"
LOGO = OUT / "assets" / "sjawc-logo.png"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def num(value: object, digits: int = 0) -> str:
    return f"{float(value or 0):,.{digits}f}"


def money(value: object, digits: int = 0) -> str:
    return f"${float(value or 0):,.{digits}f}"


def percent(value: object, digits: int = 1, *, ratio: bool = False) -> str:
    number = float(value or 0)
    if ratio:
        number *= 100
    return f"{number:.{digits}f}%"


def safe(value: object) -> str:
    return html.escape(str(value), quote=True)


def display_date(value: str) -> str:
    return date.fromisoformat(value).strftime("%B %-d, %Y")


def metric_map(report: dict) -> dict[str, float]:
    result: dict[str, float] = {}
    for row in report.get("rows") or []:
        name = ((row.get("dimensionValues") or [{}])[0].get("value") or "")
        value = ((row.get("metricValues") or [{}])[0].get("value") or 0)
        result[name] = float(value)
    return result


def aggregate_values(report: dict, key: str) -> list[float]:
    rows = ((report.get(key) or {}).get("rows") or [])
    if not rows:
        return []
    return [float(item.get("value") or 0) for item in rows[0].get("metricValues") or []]


def page() -> str:
    refresh = load("refresh_summary.json")
    ga4 = load("ga4.json")
    google_ads = load("google_ads.json")
    meta = load("meta.json")
    ghl = load("ghl.json")
    key_events = load("ga4_key_events.json")
    organic = load("ga4_organic_content.json")
    revenue = load("revenue_attribution.json")

    period = refresh["period"]
    start_label = display_date(period["start"])
    end_label = display_date(period["end"])
    ga = ga4["metrics"]
    ads = google_ads["metrics"]
    me = meta["metrics"]
    gh = ghl["metrics"]
    events = metric_map(key_events)
    rev = revenue["metrics"]
    rev_channels = revenue["channels"]
    google_rev = rev_channels["google_ads"]
    meta_rev = rev_channels["meta"]
    entitymed_rev = rev_channels["entitymed"]
    unattributed_rev = rev_channels["unattributed"]

    organic_values = aggregate_values(organic, "organic_aggregate")
    content_values = aggregate_values(organic, "content_aggregate")
    content_rows = ((organic.get("content_pages") or {}).get("rows") or [])
    top_content = content_rows[0] if content_rows else {}
    top_title = ((top_content.get("dimensionValues") or [{}, {}])[1].get("value") or "Top resource page")
    top_views = float(((top_content.get("metricValues") or [{}])[0].get("value") or 0))

    organic_sessions = organic_values[0] if len(organic_values) > 0 else 0
    organic_users = organic_values[1] if len(organic_values) > 1 else 0
    organic_engagement = organic_values[2] if len(organic_values) > 2 else 0
    organic_key_events = organic_values[3] if len(organic_values) > 3 else 0
    content_views = content_values[0] if len(content_values) > 0 else 0
    content_users = content_values[1] if len(content_values) > 1 else 0

    meta_leads = float(me.get("leads") or 0)
    meta_cpl = float(me.get("spend") or 0) / meta_leads if meta_leads else 0
    facebook = gh.get("facebook_rolling_30") or {}
    pipelines = gh.get("by_pipeline") or {}
    lead_events = events.get("generate_lead", 0)
    purchase_events = events.get("purchase", 0)
    google_roas = float(google_rev["net_sales"]) / float(ads.get("spend") or 1)
    meta_roas = float(meta_rev["net_sales"]) / float(me.get("spend") or 1)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow, noarchive">
  <title>SJAWC Rolling 30-Day Marketing Performance</title>
  <style>
    :root {{ --ink:#17212b; --muted:#62717c; --line:#dce5e7; --soft:#f5f9fa; --aqua:#58bdc7; --aqua-dark:#126a74; --navy:#102331; --green:#0d7b56; font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:#f4f8f9; }}
    * {{ box-sizing:border-box; }} body {{ margin:0; }} .app {{ width:min(1120px,calc(100% - 40px)); margin:auto; padding:26px 0 48px; }}
    .topbar {{ display:flex; justify-content:space-between; align-items:center; gap:20px; margin-bottom:20px; }} .brand {{ display:flex; align-items:center; gap:15px; }}
    .brand img {{ width:78px; height:64px; object-fit:contain; }} .brand strong {{ display:block; font-family:Georgia,serif; font-size:18px; }} .brand small {{ display:block; margin-top:4px; color:var(--muted); font-size:12px; font-weight:800; text-transform:uppercase; }}
    .pill {{ padding:9px 13px; border:1px solid #bfe5e8; border-radius:999px; background:#effbfc; color:var(--aqua-dark); font-size:13px; font-weight:800; white-space:nowrap; }}
    .hero {{ position:relative; overflow:hidden; padding:38px; border-radius:10px; background:linear-gradient(135deg,#102331,#173544 62%,#0d5964); color:white; box-shadow:0 18px 46px rgba(20,54,66,.16); }}
    .hero:after {{ content:""; position:absolute; right:-70px; top:-90px; width:280px; height:280px; border:44px solid rgba(88,189,199,.25); border-radius:50%; }} .hero>* {{ position:relative; z-index:1; }}
    .eyebrow {{ margin:0 0 10px; color:#bcecf1; font-size:13px; font-weight:850; text-transform:uppercase; }} h1,h2,h3,p {{ margin-top:0; }} h1 {{ max-width:850px; margin-bottom:12px; font-family:Georgia,serif; font-size:clamp(38px,5.6vw,60px); line-height:1.03; font-weight:500; }}
    .lede {{ max-width:850px; margin-bottom:26px; color:rgba(255,255,255,.84); font-size:18px; line-height:1.55; }} .metrics {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1px; overflow:hidden; border:1px solid rgba(255,255,255,.17); border-radius:8px; background:rgba(255,255,255,.2); }}
    .metric {{ min-height:126px; padding:17px; background:rgba(255,255,255,.09); }} .metric span {{ display:block; margin-bottom:8px; color:rgba(255,255,255,.68); font-size:12px; font-weight:800; text-transform:uppercase; }} .metric strong {{ display:block; margin-bottom:7px; font-size:28px; }} .metric small {{ color:rgba(255,255,255,.77); line-height:1.4; }}
    main {{ display:grid; gap:18px; margin-top:20px; }} .card {{ padding:27px; border:1px solid var(--line); border-radius:10px; background:white; box-shadow:0 12px 34px rgba(34,74,86,.08); }} .card h2 {{ margin-bottom:8px; font-size:23px; }} .intro {{ margin-bottom:20px; color:var(--muted); line-height:1.6; }}
    .summary {{ color:#3f4c56; font-size:17px; line-height:1.7; }} .grid-2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }} .grid-3 {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }}
    .panel {{ padding:19px; border:1px solid var(--line); border-radius:8px; background:var(--soft); }} .panel h3 {{ margin-bottom:8px; font-size:17px; }} .panel>p {{ color:#43525d; line-height:1.55; }} .panel.aqua {{ border-left:4px solid var(--aqua); }} .panel.green {{ border-left:4px solid var(--green); }}
    .stat-list {{ display:grid; gap:10px; margin-top:14px; }} .stat {{ display:flex; justify-content:space-between; gap:16px; padding-top:10px; border-top:1px solid #dce6e8; }} .stat span {{ color:var(--muted); }} .stat strong {{ text-align:right; }}
    .note {{ margin-top:18px; padding:15px 17px; border-left:4px solid var(--aqua); background:#effbfc; color:#31545a; line-height:1.55; }} .source {{ margin:15px 0 0; color:var(--muted); font-size:12px; line-height:1.5; }}
    @media(max-width:820px) {{ .app {{ width:min(100% - 24px,1120px); }} .topbar {{ align-items:flex-start; flex-direction:column; }} .hero,.card {{ padding:21px; }} .metrics,.grid-2,.grid-3 {{ grid-template-columns:1fr; }} }}
    @media(min-width:821px) and (max-width:1040px) {{ .metrics,.grid-3 {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
  </style>
</head>
<body>
<div class="app">
  <header class="topbar">
    <div class="brand"><img src="/st-johns-aesthetics/assets/sjawc-logo.png" alt="St. Johns Aesthetics and Wellness Center logo"><div><strong>St. Johns Aesthetics &amp; Wellness Center</strong><small>Marketing performance update</small></div></div>
    <div class="pill">{safe(start_label)}–{safe(end_label)}</div>
  </header>

  <section class="hero">
    <p class="eyebrow">Rolling 30-Day Performance</p>
    <h1>Marketing activity is connected to measurable 30-day sales.</h1>
    <p class="lede">The updated sales match connects current paid media activity to client revenue while keeping unattributed sales visible. Connected platforms use the reporting dates shown above; revenue uses the supplied 30-day Client Sales export.</p>
    <div class="metrics">
      <div class="metric"><span>30-day net sales</span><strong>{money(rev.get('net_sales'),2)}</strong><small>{num(rev.get('sales_rows'))} sales rows</small></div>
      <div class="metric"><span>Attributed net sales</span><strong>{money(rev.get('attributed_net_sales'),2)}</strong><small>{percent(rev.get('attribution_coverage'),1,ratio=True)} of net sales</small></div>
      <div class="metric"><span>Google matched return</span><strong>{num(google_roas,2)}x</strong><small>{money(google_rev.get('net_sales'),2)} matched revenue</small></div>
      <div class="metric"><span>Meta matched return</span><strong>{num(meta_roas,2)}x</strong><small>{money(meta_rev.get('net_sales'),2)} matched revenue</small></div>
    </div>
  </section>

  <main>
    <section class="card">
      <h2>Executive Summary</h2>
      <p class="summary">The supplied 30-day sales export recorded <strong>{money(rev.get('net_sales'),2)} in net sales</strong>. The reviewed email-and-tag match connected <strong>{money(rev.get('attributed_net_sales'),2)}</strong>, or {percent(rev.get('attribution_coverage'),1,ratio=True)}, to a marketing source. Google Ads accounts for {money(google_rev.get('net_sales'),2)} across {num(google_rev.get('sales_rows'))} sales rows, and Meta accounts for {money(meta_rev.get('net_sales'),2)} across {num(meta_rev.get('sales_rows'))} sales rows. Another {money(unattributed_rev.get('net_sales'),2)} remains unattributed and is not assigned to any channel.</p>
      <div class="note"><strong>What this means:</strong> paid media is connected to substantial current revenue, and the Google Ads sales-row count closely aligns with the platform’s {num(ads.get('conversions'),1)} reported conversions. Attribution coverage is strong enough to guide decisions, while the unattributed portion remains visible to prevent overstating channel performance.</div>
    </section>

    <section class="card">
      <h2>30-Day Revenue Attribution</h2>
      <p class="intro">Net sales from the updated match file. Facebook and Instagram are combined as Meta, and every sales row is assigned once.</p>
      <div class="grid-2">
        <article class="panel green"><h3>Google Ads</h3><div class="stat-list"><div class="stat"><span>Matched net sales</span><strong>{money(google_rev.get('net_sales'),2)}</strong></div><div class="stat"><span>Matched sales rows</span><strong>{num(google_rev.get('sales_rows'))}</strong></div><div class="stat"><span>Current ad spend</span><strong>{money(ads.get('spend'),2)}</strong></div><div class="stat"><span>Matched return on spend</span><strong>{num(google_roas,2)}x</strong></div></div></article>
        <article class="panel aqua"><h3>Meta</h3><div class="stat-list"><div class="stat"><span>Matched net sales</span><strong>{money(meta_rev.get('net_sales'),2)}</strong></div><div class="stat"><span>Matched sales rows</span><strong>{num(meta_rev.get('sales_rows'))}</strong></div><div class="stat"><span>Current ad spend</span><strong>{money(me.get('spend'),2)}</strong></div><div class="stat"><span>Matched return on spend</span><strong>{num(meta_roas,2)}x</strong></div></div></article>
        <article class="panel"><h3>EntityMed</h3><div class="stat-list"><div class="stat"><span>Matched net sales</span><strong>{money(entitymed_rev.get('net_sales'),2)}</strong></div><div class="stat"><span>Matched sales rows</span><strong>{num(entitymed_rev.get('sales_rows'))}</strong></div></div></article>
        <article class="panel"><h3>Unattributed</h3><div class="stat-list"><div class="stat"><span>Net sales</span><strong>{money(unattributed_rev.get('net_sales'),2)}</strong></div><div class="stat"><span>Sales rows</span><strong>{num(unattributed_rev.get('sales_rows'))}</strong></div></div></article>
      </div>
      <p class="source">Revenue source: user-reviewed 30-day Client Sales match supplied September 16, 2026. Matched return divides channel-assigned net sales by current platform spend; it is not a platform-reported ROAS.</p>
    </section>

    <section class="card">
      <h2>Paid Media Performance</h2>
      <p class="intro">Current delivery and efficiency from Google Ads and Meta for the same 30-day period.</p>
      <div class="grid-2">
        <article class="panel green"><h3>Google Ads</h3><p>Search advertising generated 36 matched sales rows alongside 38.5 platform-reported conversions.</p><div class="stat-list">
          <div class="stat"><span>Spend</span><strong>{money(ads.get('spend'),2)}</strong></div><div class="stat"><span>Impressions</span><strong>{num(ads.get('impressions'))}</strong></div><div class="stat"><span>Clicks</span><strong>{num(ads.get('clicks'))}</strong></div><div class="stat"><span>Average CPC</span><strong>{money(ads.get('average_cpc'),2)}</strong></div><div class="stat"><span>Reported conversions</span><strong>{num(ads.get('conversions'),1)}</strong></div><div class="stat"><span>Cost per conversion</span><strong>{money(ads.get('cost_per_conversion'),2)}</strong></div>
        </div></article>
        <article class="panel aqua"><h3>Meta</h3><p>Facebook and Instagram generated 17 reported leads and 10 matched sales rows.</p><div class="stat-list">
          <div class="stat"><span>Spend</span><strong>{money(me.get('spend'),2)}</strong></div><div class="stat"><span>Reach</span><strong>{num(me.get('reach'))}</strong></div><div class="stat"><span>Impressions</span><strong>{num(me.get('impressions'))}</strong></div><div class="stat"><span>Link clicks</span><strong>{num(me.get('link_clicks'))}</strong></div><div class="stat"><span>Reported leads</span><strong>{num(meta_leads)}</strong></div><div class="stat"><span>Cost per lead</span><strong>{money(meta_cpl,2)}</strong></div>
        </div></article>
      </div>
      <p class="source">Platform conversions and leads reflect each advertising platform’s attribution and may overlap with website events or CRM opportunities.</p>
    </section>

    <section class="card">
      <h2>Website and Organic Performance</h2>
      <p class="intro">GA4 activity for the current rolling 30 days, including the contribution from organic traffic and educational content.</p>
      <div class="grid-3">
        <article class="panel"><h3>Website activity</h3><div class="stat-list"><div class="stat"><span>Sessions</span><strong>{num(ga.get('sessions'))}</strong></div><div class="stat"><span>Active users</span><strong>{num(ga.get('active_users'))}</strong></div><div class="stat"><span>Engagement rate</span><strong>{percent(ga.get('engagement_rate'),1,ratio=True)}</strong></div></div></article>
        <article class="panel"><h3>Organic search</h3><div class="stat-list"><div class="stat"><span>Sessions</span><strong>{num(organic_sessions)}</strong></div><div class="stat"><span>Active users</span><strong>{num(organic_users)}</strong></div><div class="stat"><span>Engagement rate</span><strong>{percent(organic_engagement,1,ratio=True)}</strong></div><div class="stat"><span>Key events</span><strong>{num(organic_key_events)}</strong></div></div></article>
        <article class="panel"><h3>Content engagement</h3><div class="stat-list"><div class="stat"><span>Resource views</span><strong>{num(content_views)}</strong></div><div class="stat"><span>Resource users</span><strong>{num(content_users)}</strong></div><div class="stat"><span>Leading article</span><strong>{safe(top_title)}</strong></div><div class="stat"><span>Article views</span><strong>{num(top_views)}</strong></div></div></article>
      </div>
    </section>

    <section class="card">
      <h2>Rolling 30-Day Lead Flow</h2>
      <p class="intro">New GoHighLevel opportunities created during this reporting window. These counts are operational pipeline records and should not be added to advertising-platform lead totals.</p>
      <div class="grid-3">
        <article class="panel aqua"><h3>All new opportunities</h3><div class="stat-list"><div class="stat"><span>Created</span><strong>{num(gh.get('rolling_30_opportunities'))}</strong></div><div class="stat"><span>Open</span><strong>{num((gh.get('by_status') or {}).get('open'))}</strong></div></div></article>
        <article class="panel"><h3>Facebook pipeline</h3><div class="stat-list"><div class="stat"><span>Opportunities</span><strong>{num(facebook.get('opportunities'))}</strong></div><div class="stat"><span>Booked or showed stage</span><strong>{num(facebook.get('appointment_stage_opportunities'))}</strong></div></div></article>
        <article class="panel"><h3>Owned lead capture</h3><div class="stat-list"><div class="stat"><span>Website contact pipeline</span><strong>{num(pipelines.get('Contact Form ~ New Client'))}</strong></div><div class="stat"><span>EntityMed form pipeline</span><strong>{num(pipelines.get('EntityMed Form Submission'))}</strong></div></div></article>
      </div>
      <p class="source">Report window: {safe(start_label)} through {safe(end_label)}. Sources: Google Ads, Meta Ads, Google Analytics 4, and GoHighLevel.</p>
    </section>
  </main>
</div>
</body>
</html>"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page(), encoding="utf-8")
    data_out = OUT / "data"
    data_out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DATA / "live.json", data_out / "live.json")
    print(f"Built {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
