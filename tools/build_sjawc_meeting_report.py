from __future__ import annotations

import hashlib
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


def marketing_progress() -> str:
    path = DATA / "marketing_progress.json"
    tasks = json.loads(path.read_text()).get("tasks", []) if path.exists() else []
    months: dict[str, list] = {}
    for task in sorted(tasks, key=lambda t: t["updated"], reverse=True):
        months.setdefault(task["updated"][:7], []).append(task)
    sections = []
    for month, items in months.items():
        rows = []
        for task in sorted(items, key=lambda t: not bool(t.get("question"))):
            def bullets(key):
                return "<ul>" + "".join(f"<li>{safe(x)}</li>" for x in task.get(key, [])) + "</ul>"
            attention = safe(task.get("attention", "Input needed"))
            flag = f'<span class="progress-flag">⚑ {attention}</span>' if task.get("question") else '<span class="progress-clear">No input needed</span>'
            question_html = f'<div class="progress-question"><strong>⚑ {attention}</strong><p>{safe(task["question"])}</p></div>' if task.get("question") else ""
            preview_html = ""
            if task.get("preview_url"):
                url = safe(task["preview_url"])
                preview_html = f'<figure class="task-preview"><a href="{url}" target="_blank" rel="noopener noreferrer">{safe(task.get("preview_label", "View preview"))}<img src="{url}" alt="{safe(task.get("preview_image_alt", "Page preview"))}" loading="lazy"></a><figcaption>Open the image for the full-size preview.</figcaption></figure>'
            completed_html = '<h4>Work completed</h4>' + bullets('completed') if task.get('completed') else ''
            next_html = '<h4>Next steps</h4>' + bullets('next') if task.get('next') else ''
            recommendation_html = f'<h4>Recommendation to consider</h4><p>{safe(task["recommendation"])}</p>' if task.get('recommendation') else ''
            history = "".join(f'<li><time datetime="{safe(h["date"])}">{display_date(h["date"])}</time> — {safe(h["text"])}</li>' for h in task.get("history", []))
            if task.get("document_blocks"):
                document_parts = []
                for block in task["document_blocks"]:
                    if block["type"] == "table":
                        table_rows = []
                        for index, cells in enumerate(block["rows"]):
                            cell_tag = "th" if index == 0 else "td"
                            table_rows.append("<tr>" + "".join(f"<{cell_tag}>{safe(cell).replace(chr(10), '<br>')}</{cell_tag}>" for cell in cells) + "</tr>")
                        document_parts.append('<div class="document-table"><table>' + "".join(table_rows) + '</table></div>')
                    else:
                        tag = "h3" if block.get("style") == "Title" else ("h4" if block.get("style", "").startswith("Heading") else "p")
                        document_parts.append(f'<{tag} class="document-text">{safe(block["text"]).replace(chr(10), "<br>")}</{tag}>')
                document_html = "".join(document_parts)
                rows.append(f'''<details class="progress-task"><summary><span class="progress-title">{safe(task['title'])}</span><span class="progress-status">{safe(task['status'])}</span>{flag}<span class="progress-action"><span class="when-closed">View details</span><span class="when-open">Hide details</span></span><span class="progress-date">Entry updated <time datetime="{safe(task['updated'])}">{display_date(task['updated'])}</time></span></summary><div class="progress-body">{document_html}</div></details>''')
                continue
            rows.append(f'''<details class="progress-task"><summary><span class="progress-title">{safe(task['title'])}</span><span class="progress-status">{safe(task['status'])}</span>{flag}<span class="progress-action"><span class="when-closed">View details</span><span class="when-open">Hide details</span></span><span class="progress-date">Entry updated <time datetime="{safe(task['updated'])}">{display_date(task['updated'])}</time></span></summary>
            <div class="progress-body"><p>{safe(task['summary'])}</p>{preview_html}{completed_html}{next_html}<p class="source">{safe(task.get('limitations', ''))}</p>
            {question_html}{recommendation_html}<h4>Update history</h4><ul>{history}</ul></div></details>''')
        label = date.fromisoformat(month + "-01").strftime("%B %Y")
        sections.append(f'<div class="progress-month"><h3>{label}</h3>{"".join(rows)}</div>')
    return '<section class="card" id="marketing-progress" aria-labelledby="progress-heading"><h2 id="progress-heading">Marketing Progress</h2><p class="intro">Updates, current stopping points, and next steps. Expand a task for details; flagged items need team input.</p>' + "".join(sections) + '</section>'



def pending_tasks() -> str:
    path = DATA / "marketing_progress.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    items = data.get("pending_tasks", [])
    if not items:
        return ""
    rows = "".join(f'<li><span class="pending-checkbox" aria-hidden="true"></span><span><span class="sr-only">Pending: </span>{safe(item)}</span></li>' for item in items)
    return f'<section class="card" id="pending-tasks" aria-labelledby="pending-heading"><h2 id="pending-heading">Pending Tasks</h2><ul class="pending-list">{rows}</ul></section>'


def executive_summary_html() -> str:
    editorial = load("executive_summary.json")
    approved = editorial["approved"]
    payload = json.dumps({"period": approved["period"], "paragraphs": approved["paragraphs"]}, sort_keys=True, ensure_ascii=False).encode()
    if approved.get("status") != "approved" or hashlib.sha256(payload).hexdigest() != approved.get("content_sha256"):
        raise ValueError("Executive Summary changed without recorded user approval. Present the draft to the user before publishing.")
    period = approved["period"]
    label = f"Summary for {display_date(period['start'])}–{display_date(period['end'])}"
    return '<p class="source">' + safe(label) + '</p>' + ''.join('<p class="summary">' + safe(text) + '</p>' for text in approved['paragraphs'])


def aeo_performance_html() -> str:
    path = DATA / "search_atlas.json"
    if not path.exists():
        return ""
    atlas = json.loads(path.read_text())
    metrics = atlas.get("metrics", {})
    current = metrics.get("llm_current_mentions")
    previous = metrics.get("llm_previous_mentions")
    if current is None:
        return ""
    snapshot = atlas.get("retrieved_at", "")[:10]
    date_label = display_date(snapshot) if snapshot else "Date unavailable"
    previous_card = f'<article class="panel"><h3>Previous comparison</h3><div class="stat-list"><div class="stat"><span>AI mentions</span><strong>{num(previous)}</strong></div></div></article>' if previous is not None else ''
    return f'<section class="card" id="aeo-performance"><h2>AEO Performance</h2><p class="intro">Visibility in AI-generated answers, tracked by Search Atlas.</p><div class="grid-2"><article class="panel aqua"><h3>Current visibility</h3><div class="stat-list"><div class="stat"><span>AI mentions</span><strong>{num(current)}</strong></div></div></article>{previous_card}</div><p class="source">Search Atlas snapshot retrieved {date_label}. Comparison periods are not supplied by the source. Mentions measure tracked AI visibility, not website visits or leads.</p></section>'


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
    source_dates = {"Google Ads": google_ads["period"]["end"], "Meta": meta["period"]["end"], "Website analytics": ga4["period"]["end"], "Lead flow": ghl["period"]["end"]}
    common_end = min(source_dates.values())
    freshness = "Performance updated through " + display_date(common_end)
    behind = [name + " through " + display_date(end) for name, end in source_dates.items() if end != period["end"]]
    if behind:
        freshness += ". Some sources are behind: " + "; ".join(behind) + "."
    sales_period = revenue.get("period")
    revenue_dates = f"{display_date(sales_period['start'])}–{display_date(sales_period['end'])}" if sales_period else "the separately supplied sales export"
    freshness += " Weekly update: Mondays at 3 a.m. Eastern. Sales period: " + revenue_dates + "."

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
    blog_sessions = content_values[3] if len(content_values) > 3 else None

    meta_leads = float(me.get("leads") or 0)
    meta_cpl = float(me.get("spend") or 0) / meta_leads if meta_leads else 0
    facebook = gh.get("facebook_rolling_30") or {}
    pipelines = gh.get("by_pipeline") or {}
    lead_events = events.get("generate_lead", 0)
    purchase_events = events.get("purchase", 0)
    sales_amount_label = {"net_sales": "Net sales", "gross_sales": "Gross sales"}.get(revenue.get("amount_basis"), "Reported sales")
    platform_path = DATA / "lead_platforms.json"
    platforms = json.loads(platform_path.read_text()).get("platforms", {}) if platform_path.exists() else {}
    platform_cards = []
    for key in ["ageless"]:
        platform = platforms.get(key)
        if not platform:
            continue
        pp = platform["period"]
        fee = money(platform["monthly_fee"], 2) if platform.get("monthly_fee") is not None else "Not supplied"
        cpl = money(platform["estimated_cost_per_lead"], 2) if platform.get("estimated_cost_per_lead") is not None else "Unavailable"
        platform_cards.append(f'''<article class="panel aqua"><h3>{safe(platform['name'])}</h3><p>Reporting window: {display_date(pp['start'])}–{display_date(pp['end'])}.</p><div class="stat-list"><div class="stat"><span>Monthly platform fee</span><strong>{fee}</strong></div><div class="stat"><span>New tagged contacts</span><strong>{num(platform['new_tagged_contacts'])}</strong></div><div class="stat"><span>Estimated cost per lead</span><strong>{cpl}</strong></div></div></article>''')
    platform_cards_html = "".join(platform_cards)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow, noarchive">
  <title>Marketing and Sales Performance Report</title>
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
    .progress-month h3 {{ margin:24px 0 12px; color:var(--aqua-dark); font-size:17px; }}
    .progress-task {{ border:1px solid var(--line); border-radius:8px; margin-bottom:12px; overflow:hidden; }}
    .progress-task summary {{ padding:20px; cursor:pointer; display:flex; align-items:center; flex-wrap:wrap; gap:10px; background:var(--soft); list-style:none; }}
    .progress-task summary::-webkit-details-marker {{ display:none; }}
    .progress-task summary::before {{ content:"›"; font-size:25px; color:var(--aqua-dark); transition:transform .15s; }}
    .progress-task[open] summary::before {{ transform:rotate(90deg); }}
    .progress-task summary:focus-visible {{ outline:3px solid var(--aqua-dark); outline-offset:-3px; }}
    .progress-title {{ font-weight:750; flex:1 1 280px; }}
    .progress-status,.progress-flag,.progress-clear {{ padding:5px 9px; border-radius:5px; font-size:12px; font-weight:750; }}
    .progress-status {{ background:#e2f4f6; color:#12616b; }} .progress-flag {{ background:#fff0cb; color:#775000; }}
    .progress-clear {{ background:#e7f5ed; color:#12643e; }}
    .progress-action {{ color:var(--aqua-dark); font-size:13px; font-weight:750; text-decoration:underline; text-underline-offset:3px; }}
    .when-open {{ display:none; }} .progress-task[open] .when-open {{ display:inline; }} .progress-task[open] .when-closed {{ display:none; }}
    .progress-date {{ flex-basis:100%; margin-left:24px; font-size:12px; color:var(--muted); }}
    .progress-body {{ padding:22px; line-height:1.65; color:#3f4c56; }} .progress-body h4 {{ margin:22px 0 8px; color:var(--ink); }}
    .progress-body li {{ margin-bottom:8px; }} .progress-body ul {{ padding-left:22px; }}
    .progress-question {{ margin-top:20px; padding:16px; border-left:4px solid #c48a19; background:#fff8e8; color:#674a12; }} .progress-question p {{ margin:8px 0 0; }}
    .document-text {{ white-space:pre-wrap; overflow-wrap:anywhere; }} .document-table {{ overflow-x:auto; }} .document-table table {{ width:100%; border-collapse:collapse; margin:16px 0; }} .document-table th,.document-table td {{ border:1px solid var(--line); padding:12px; text-align:left; vertical-align:top; min-width:140px; }} .document-table th {{ background:var(--soft); }}
    .task-preview {{ margin:18px 0; }} .task-preview a {{ color:var(--aqua-dark); font-weight:700; }} .task-preview img {{ display:block; width:100%; max-width:420px; max-height:480px; object-fit:contain; object-position:left top; margin-top:12px; border:1px solid var(--line); border-radius:6px; }} .task-preview figcaption {{ color:var(--muted); font-size:12px; margin-top:8px; }}
    .pending-list {{ list-style:none; padding:0; margin:18px 0 0; }}
    .pending-list li {{ display:flex; align-items:flex-start; gap:13px; padding:17px 0; border-top:1px solid var(--line); line-height:1.6; }}
    .pending-checkbox {{ flex:0 0 19px; height:19px; margin-top:3px; border:2px solid #81969e; border-radius:3px; background:white; }}
    .sr-only {{ position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }}
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
  <p class="source" style="margin:0 0 18px">{safe(freshness)}</p>

  <section class="hero">
    <p class="eyebrow">Rolling 30-Day Performance</p>
    <h1>Marketing and Sales Performance Report</h1>
    <p class="lede">Digital Marketing and sales performance activity using a rolling 30-day window. Sales metrics are a blend from LeadAR and Boulevard matching criteria on email address. Performance tags within LeadAR drive visibility into the digital marketing efforts for the source summaries.</p>
    <div class="metrics" style="grid-template-columns:1fr;max-width:420px">
      <div class="metric"><span>{safe(sales_amount_label)}</span><strong>{money(rev.get('sales_amount'),2)}</strong><small>{safe(revenue_dates)} · {num(rev.get('order_count'))} orders</small></div>
    </div>
  </section>

  <main>
    <section class="card">
      <h2>Executive Summary</h2>
      {executive_summary_html()}
    </section>

    <section class="card" id="paid-media">
      <h2>Paid Media Performance</h2>
      <p class="intro">Advertising and lead-platform performance. Each source’s reporting window is shown below.</p>
      <div class="grid-2">
        <article class="panel green"><h3>Google Ads</h3><p>Reporting window: {display_date(google_ads["period"]["start"])}–{display_date(google_ads["period"]["end"])}.</p><div class="stat-list">
          <div class="stat"><span>Spend</span><strong>{money(ads.get('spend'),2)}</strong></div><div class="stat"><span>Impressions</span><strong>{num(ads.get('impressions'))}</strong></div><div class="stat"><span>Clicks</span><strong>{num(ads.get('clicks'))}</strong></div><div class="stat"><span>Average CPC</span><strong>{money(ads.get('average_cpc'),2)}</strong></div><div class="stat"><span>Reported lead actions</span><strong>{num(ads.get('leads'),1) if ads.get('leads') is not None else 'Pending refresh'}</strong></div><div class="stat"><span>Cost per lead</span><strong>{money(ads.get('cost_per_lead'),2) if ads.get('cost_per_lead') is not None else 'Pending refresh'}</strong></div>
        </div></article>
        <article class="panel aqua"><h3>Meta</h3><p>Reporting window: {display_date(meta["period"]["start"])}–{display_date(meta["period"]["end"])}.</p><div class="stat-list">
          <div class="stat"><span>Spend</span><strong>{money(me.get('spend'),2)}</strong></div><div class="stat"><span>Reach</span><strong>{num(me.get('reach'))}</strong></div><div class="stat"><span>Impressions</span><strong>{num(me.get('impressions'))}</strong></div><div class="stat"><span>Link clicks</span><strong>{num(me.get('link_clicks'))}</strong></div><div class="stat"><span>Reported leads</span><strong>{num(meta_leads)}</strong></div><div class="stat"><span>Cost per lead</span><strong>{money(meta_cpl,2)}</strong></div>
        </div></article>
        {platform_cards_html}
      </div>

    </section>

    <section class="card">
      <h2>Website and Organic Performance</h2>
      <p class="intro">GA4 activity for the current rolling 30 days, including the contribution from organic traffic and educational content.</p>
      <div class="grid-3">
        <article class="panel"><h3>Website activity</h3><div class="stat-list"><div class="stat"><span>Sessions</span><strong>{num(ga.get('sessions'))}</strong></div><div class="stat"><span>Active users</span><strong>{num(ga.get('active_users'))}</strong></div><div class="stat"><span>Engagement rate</span><strong>{percent(ga.get('engagement_rate'),1,ratio=True)}</strong></div></div></article>
        <article class="panel"><h3>Organic search</h3><div class="stat-list"><div class="stat"><span>Sessions</span><strong>{num(organic_sessions)}</strong></div><div class="stat"><span>Active users</span><strong>{num(organic_users)}</strong></div><div class="stat"><span>Engagement rate</span><strong>{percent(organic_engagement,1,ratio=True)}</strong></div><div class="stat"><span>Key events</span><strong>{num(organic_key_events)}</strong></div></div></article>
        <article class="panel"><h3>Article engagement</h3><div class="stat-list"><div class="stat"><span>Article Views</span><strong>{num(content_views)}</strong></div><div class="stat"><span>Blog Visits</span><strong>{num(blog_sessions) if blog_sessions is not None else 'Unavailable'}</strong></div><div class="stat"><span>Leading Article</span><strong>{safe(top_title)}</strong></div><div class="stat"><span>Article Users</span><strong>{num(content_users)}</strong></div></div></article>
      </div>
    </section>

    {aeo_performance_html()}

    {marketing_progress()}
    {pending_tasks()}
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
