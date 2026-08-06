from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from build_airocide_report import (
    CONTENT_CATEGORIES,
    asset_data_uri,
    money,
    number,
    pct,
    pct_change,
    period_label,
    row_key,
    safe,
    search_rows,
    search_summary,
    trend_value,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "airocide"
LIVE_ASSETS = ROOT / "firebase-static" / "public" / "airocide-systems" / "assets"
OUT = ROOT / "firebase-static" / "public" / "airocide-systems-test"


COMMERCIAL_HOST = "www.airocide.com"
KES_HOSTS = {"shop.airocide.com", "airocide.com"}


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def metric_values(row: dict) -> list[str]:
    return [item.get("value", "0") for item in row.get("metricValues", [])]


def dimension_values(row: dict) -> list[str]:
    return [item.get("value", "") for item in row.get("dimensionValues", [])]


def rows(report: dict) -> list[dict]:
    return report.get("rows") or []


def host_totals(hostname_data: dict, hosts: set[str]) -> dict[str, float]:
    total = {
        "sessions": 0.0,
        "active_users": 0.0,
        "key_events": 0.0,
        "revenue": 0.0,
        "purchases": 0.0,
        "purchasers": 0.0,
    }
    for row in rows(hostname_data["hostname_totals"]):
        host = dimension_values(row)[0]
        if host not in hosts:
            continue
        values = [float(value or 0) for value in metric_values(row)]
        keys = ["sessions", "active_users", "key_events", "revenue", "purchases", "purchasers"]
        for key, value in zip(keys, values):
            total[key] += value
    return total


def event_count(hostname_data: dict, hosts: set[str], event_name: str, metric_index: int = 0) -> float:
    value = 0.0
    for row in rows(hostname_data["hostname_events"]):
        host, event = dimension_values(row)
        if host in hosts and event == event_name:
            values = metric_values(row)
            value += float(values[metric_index] or 0)
    return value


def page_value(hostname_data: dict, hosts: set[str], page_paths: set[str], metric_index: int = 0) -> float:
    value = 0.0
    for row in rows(hostname_data["hostname_pages"]):
        host, page_path = dimension_values(row)
        if host in hosts and page_path in page_paths:
            values = metric_values(row)
            value += float(values[metric_index] or 0)
    return value


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


def search_table(sc: dict, key: str, label: str) -> str:
    body = "\n".join(
        f"""
                <tr>
                  <td>{safe(row_key(row))}</td>
                  <td>{number(row.get("clicks"))}</td>
                  <td>{number(row.get("impressions"))}</td>
                  <td>{float(row.get("ctr") or 0) * 100:.1f}%</td>
                  <td>{float(row.get("position") or 0):.1f}</td>
                </tr>"""
        for row in search_rows(sc, key)[:5]
    )
    return f"""
            <div class="table-wrap">
              <table>
                <thead>
                  <tr><th>{safe(label)}</th><th>Clicks</th><th>Impr.</th><th>CTR</th><th>Position</th></tr>
                </thead>
                <tbody>{body}
                </tbody>
              </table>
            </div>"""


def page() -> str:
    refresh = load("refresh_summary.json")
    ga4 = load("ga4.json")
    hostname = load("ga4_hostname.json")
    sc = load("search_console.json")
    atlas = load("search_atlas.json")

    project = atlas["domain"]
    se = project["metrics"]
    keyword_trend = project.get("organic_keywords_trend") or []
    april_keywords = trend_value(keyword_trend, "2026-04")
    current_keywords = float(se.get("keyword_count") or se.get("organic_keywords") or 0)
    current_llm = float(se.get("llm_current_mentions") or 0)
    previous_llm = float(se.get("llm_previous_mentions") or 0)
    sc_summary = search_summary(sc)
    logo_src = asset_data_uri(LIVE_ASSETS / "airocide-logo-1x.png", "image/png")

    commercial = host_totals(hostname, {COMMERCIAL_HOST})
    kes = host_totals(hostname, KES_HOSTS)

    commercial_form_starts = event_count(hostname, {COMMERCIAL_HOST}, "form_start")
    commercial_form_submits = event_count(hostname, {COMMERCIAL_HOST}, "form_submit")
    commercial_form_users = event_count(hostname, {COMMERCIAL_HOST}, "form_submit", metric_index=1)
    commercial_contact_views = page_value(hostname, {COMMERCIAL_HOST}, {"/contact/"})

    kes_product_views = event_count(hostname, KES_HOSTS, "view_item")
    kes_add_to_carts = event_count(hostname, KES_HOSTS, "add_to_cart")
    kes_checkouts = event_count(hostname, KES_HOSTS, "begin_checkout")
    kes_form_starts = event_count(hostname, KES_HOSTS, "form_start")
    kes_form_submits = event_count(hostname, KES_HOSTS, "form_submit")
    kes_contact_views = page_value(hostname, KES_HOSTS, {"/pages/contact-us"})

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow, noarchive">
    <title>Airocide Systems Commercial + KES Technology Test Report</title>
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
        --green: #0d7b56;
        --gold: #8A5E10;
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
      .test-pill {{ border-color: #f2d49b; background: #fff7e7; color: #6f4a08; }}
      .hero {{ padding: 38px; border-radius: 8px; background: linear-gradient(135deg, #0B1E3C, #005fc2 66%, #2b81d1); color: #fff; box-shadow: 0 18px 46px rgba(11, 30, 60, .2); }}
      .eyebrow {{ margin: 0 0 10px; color: #d8ecff; font-size: 13px; font-weight: 850; text-transform: uppercase; }}
      h1, h2, h3, p {{ margin-top: 0; }}
      h1 {{ max-width: 960px; margin-bottom: 12px; font-size: clamp(36px, 5.6vw, 58px); line-height: 1; font-weight: 720; letter-spacing: 0; }}
      .hero p.lede {{ max-width: 940px; margin-bottom: 26px; color: rgba(255,255,255,.84); font-size: 18px; line-height: 1.58; }}
      .hero-metrics {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; overflow: hidden; border: 1px solid rgba(255,255,255,.16); border-radius: 8px; background: rgba(255,255,255,.18); }}
      .hero-metric {{ min-height: 126px; padding: 17px; background: rgba(255,255,255,.09); }}
      .hero-metric span {{ display: block; margin-bottom: 8px; color: rgba(255,255,255,.7); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .hero-metric strong {{ display: block; margin-bottom: 8px; font-size: 28px; }}
      .hero-metric small {{ color: rgba(255,255,255,.78); line-height: 1.4; }}
      main {{ display: grid; gap: 18px; margin-top: 20px; }}
      .section-label {{ margin: 18px 0 0; padding: 15px 18px; border-radius: 8px; background: #0B1E3C; color: #fff; font-size: 14px; font-weight: 900; letter-spacing: .02em; text-transform: uppercase; }}
      .kes-label {{ background: #8A5E10; }}
      .card {{ padding: 26px; border: 1px solid var(--line); border-radius: 8px; background: var(--white); box-shadow: 0 12px 34px rgba(34, 74, 86, .08); }}
      .card h2 {{ margin-bottom: 14px; font-size: 22px; }}
      .summary {{ color: #3f4c56; font-size: 16px; line-height: 1.68; }}
      .grid-4 {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
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
      .source-note {{ margin-top: 14px; color: var(--muted); font-size: 12px; line-height: 1.5; }}
      table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
      th, td {{ padding: 11px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
      th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
      @media (max-width: 860px) {{
        .app {{ width: min(100% - 24px, 1120px); }}
        .topbar {{ align-items: flex-start; flex-direction: column; }}
        .hero, .card {{ padding: 21px; }}
        .hero-metrics, .grid-4, .grid-3, .grid-2, .content-grid {{ grid-template-columns: 1fr; }}
        .brand-logo {{ width: 176px; }}
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
            <small>Commercial + KES Technology test report</small>
          </div>
        </div>
        <div class="pill test-pill">Test page for review</div>
      </header>

      <section class="hero">
        <p class="eyebrow">Reporting Separation Test</p>
        <h1>Commercial and residential performance are now separated.</h1>
        <p class="lede">This test view separates Airocide Systems commercial reporting from KES Technology residential ecommerce reporting. Airocide.com remains the commercial authority destination, while shop.airocide.com and legacy Shopify paths are grouped under KES Technology.</p>
        <div class="hero-metrics">
          <div class="hero-metric"><span>Commercial Sessions</span><strong>{number(commercial["sessions"])}</strong><small>{COMMERCIAL_HOST}</small></div>
          <div class="hero-metric"><span>Commercial Revenue</span><strong>{money(commercial["revenue"])}</strong><small>Lead-generation site, not ecommerce</small></div>
          <div class="hero-metric"><span>KES Revenue</span><strong>{money(kes["revenue"])}</strong><small>Residential ecommerce activity</small></div>
          <div class="hero-metric"><span>KES Purchases</span><strong>{number(kes["purchases"])}</strong><small>GA4 ecommerce events</small></div>
        </div>
      </section>

      <main>
        <section class="card">
          <h2>Executive Summary</h2>
          <p class="summary">Airocide.com and shop.airocide.com now represent two distinct reporting views. Airocide.com is the commercial SEO and lead-generation property for Airocide Systems. shop.airocide.com supports the residential ecommerce business referred to as KES Technology.</p>
          <p class="summary">This separation matters because commercial performance should be evaluated by qualified lead activity, form submissions, phone-call visibility, search visibility, and content engagement. Residential performance should be evaluated by ecommerce revenue, purchases, product engagement, checkout behavior, and Shopify order data.</p>
          <p class="summary">Historical Shopify paths still appear under the bare domain, airocide.com, because the domain previously served as the Shopify master domain. In this test report, those legacy Shopify paths are grouped with KES Technology so revenue is not mixed into Airocide Systems commercial performance.</p>
        </section>

        <div class="section-label">Airocide Systems Commercial</div>

        <section class="card">
          <h2>Commercial Website Performance</h2>
          <div class="grid-4">
            <article class="panel foundation"><h3>Sessions</h3><p><strong>{number(commercial["sessions"])}</strong><br>Commercial sessions on {COMMERCIAL_HOST}.</p></article>
            <article class="panel foundation"><h3>Active Users</h3><p><strong>{number(commercial["active_users"])}</strong><br>Users on the commercial site.</p></article>
            <article class="panel growth"><h3>Form Starts</h3><p><strong>{number(commercial_form_starts)}</strong><br>Commercial form-start events.</p></article>
            <article class="panel growth"><h3>Form Submissions</h3><p><strong>{number(commercial_form_submits)}</strong><br>Submitted commercial lead forms from {number(commercial_form_users)} users.</p></article>
          </div>
          <p class="source-note">Commercial revenue and purchase counts are intentionally zero in GA4 because Airocide Systems commercial performance is lead-based, not ecommerce-based.</p>
        </section>

        <section class="card">
          <h2>Commercial SEO Progress</h2>
          <div class="grid-3">
            <article class="panel growth">
              <h3>Keyword footprint</h3>
              <p>Airocide.com tracked keywords increased from {number(april_keywords)} in April to {number(current_keywords)} currently.</p>
              <div class="stat-list">
                <div class="stat"><span>Progress</span><strong>{pct_change(april_keywords, current_keywords)}</strong></div>
                <div class="stat"><span>Top-3 keywords</span><strong>{number(se.get("top_3_keywords_count"))}</strong></div>
              </div>
            </article>
            <article class="panel seo">
              <h3>Authority base</h3>
              <p>Authority remains concentrated around Airocide.com as the primary commercial brand destination.</p>
              <div class="stat-list">
                <div class="stat"><span>Referring domains</span><strong>{number(se.get("refdomain_count"))}</strong></div>
                <div class="stat"><span>Backlinks</span><strong>{number(se.get("backlinks"))}</strong></div>
              </div>
            </article>
            <article class="panel foundation">
              <h3>AI/search recognition</h3>
              <p>Search Atlas shows visibility in AI/search recognition signals.</p>
              <div class="stat-list">
                <div class="stat"><span>Current LLM mentions</span><strong>{number(current_llm)}</strong></div>
                <div class="stat"><span>Change</span><strong>{pct_change(previous_llm, current_llm)}</strong></div>
              </div>
            </article>
          </div>
        </section>

        <section class="card">
          <h2>Google Search Console Visibility</h2>
          <div class="grid-4">
            <article class="panel growth"><h3>Clicks</h3><p><strong>{number(sc_summary.get("clicks"))}</strong><br>Verified organic clicks.</p></article>
            <article class="panel growth"><h3>Impressions</h3><p><strong>{number(sc_summary.get("impressions"))}</strong><br>Google search impressions.</p></article>
            <article class="panel foundation"><h3>CTR</h3><p><strong>{float(sc_summary.get("ctr") or 0) * 100:.1f}%</strong><br>Search click-through rate.</p></article>
            <article class="panel foundation"><h3>Position</h3><p><strong>{float(sc_summary.get("position") or 0):.1f}</strong><br>Average organic position.</p></article>
          </div>
          <div class="grid-2">
            {search_table(sc, "queries", "Top Queries")}
            {search_table(sc, "pages", "Top Pages")}
          </div>
        </section>

        <section class="card">
          <h2>SEO Content Expansion</h2>
          <p class="summary">The newly launched pages expand Airocide Systems' search footprint into specific commercial and institutional categories. This is commercial authority content, not residential ecommerce content.</p>
          <div class="content-grid">
            {content_category_cards()}
          </div>
        </section>

        <section class="card">
          <h2>Commercial Lead Visibility</h2>
          <p class="summary">The commercial site recorded {number(commercial_contact_views)} Contact page views, {number(commercial_form_starts)} form starts, and {number(commercial_form_submits)} form submissions from {number(commercial_form_users)} users. WPForms database logging is now in place for future form submissions.</p>
          <p class="summary">Phone-call attribution remains a reporting limitation. Airocide.com displays a direct phone number, but call tracking is not currently active, so phone inquiries may be contributing to lead volume without being connected back to organic search, paid search, or specific landing pages.</p>
        </section>

        <section class="card">
          <h2>Paid Search Launch Readiness</h2>
          <p class="summary">A Google Ads account and launch-ready campaign structure have already been prepared for Airocide Systems. The campaign is ready to move forward once billing is connected, giving the commercial side a paid-search option that can run alongside the SEO foundation work.</p>
        </section>

        <section class="card">
          <h2>Brand Protection Review</h2>
          <p class="summary">Brand protection directly supports the commercial SEO and brand-consolidation work. If users, search engines, or social platforms see multiple unofficial Airocide-branded pages, domains, and regional claims, it weakens the clarity of Airocide.com as the primary authority destination for Airocide Systems.</p>
        </section>

        <div class="section-label kes-label">KES Technology Residential</div>

        <section class="card">
          <h2>Residential Ecommerce Summary</h2>
          <p class="summary">KES Technology residential ecommerce is shown separately because shop.airocide.com supports the residential replacement/product business, while Airocide.com supports the commercial Airocide Systems SEO and lead-generation strategy.</p>
          <div class="grid-4">
            <article class="panel seo"><h3>Revenue</h3><p><strong>{money(kes["revenue"])}</strong><br>GA4 ecommerce revenue grouped under KES Technology.</p></article>
            <article class="panel seo"><h3>Purchases</h3><p><strong>{number(kes["purchases"])}</strong><br>Residential ecommerce purchase events.</p></article>
            <article class="panel foundation"><h3>Sessions</h3><p><strong>{number(kes["sessions"])}</strong><br>Residential sessions across Shopify paths.</p></article>
            <article class="panel foundation"><h3>Active Users</h3><p><strong>{number(kes["active_users"])}</strong><br>Residential users across Shopify paths.</p></article>
          </div>
          <p class="source-note">KES includes shop.airocide.com plus legacy Shopify paths on airocide.com. Shopify should be treated as the final revenue source of truth for orders, refunds, net sales, product mix, and customer details.</p>
        </section>

        <section class="card">
          <h2>Residential Product and Checkout Activity</h2>
          <div class="grid-4">
            <article class="panel growth"><h3>Product Views</h3><p><strong>{number(kes_product_views)}</strong><br>Product detail views.</p></article>
            <article class="panel growth"><h3>Add to Cart</h3><p><strong>{number(kes_add_to_carts)}</strong><br>Add-to-cart events.</p></article>
            <article class="panel seo"><h3>Begin Checkout</h3><p><strong>{number(kes_checkouts)}</strong><br>Checkout-start events.</p></article>
            <article class="panel seo"><h3>Purchase Rate</h3><p><strong>{(kes["purchases"] / kes_checkouts * 100) if kes_checkouts else 0:.1f}%</strong><br>Purchases divided by checkout starts.</p></article>
          </div>
        </section>

        <section class="card">
          <h2>Residential Contact Path</h2>
          <p class="summary">Residential contact behavior should be evaluated separately from the commercial Contact page. KES Technology contact activity appears on the Shopify contact path, including legacy Shopify paths from the prior domain setup.</p>
          <div class="grid-3">
            <article class="panel foundation"><h3>Contact Page Views</h3><p><strong>{number(kes_contact_views)}</strong><br>Views of /pages/contact-us across KES paths.</p></article>
            <article class="panel growth"><h3>Form Starts</h3><p><strong>{number(kes_form_starts)}</strong><br>Residential form-start events.</p></article>
            <article class="panel growth"><h3>Form Submissions</h3><p><strong>{number(kes_form_submits)}</strong><br>Residential form-submit events.</p></article>
          </div>
        </section>

        <section class="card">
          <h2>Data Quality Notes</h2>
          <p class="summary">This test report uses GA4 hostname and page-path separation to avoid mixing commercial lead generation with residential ecommerce. Airocide Systems commercial reporting is based on www.airocide.com. KES Technology residential reporting is based on shop.airocide.com plus legacy Shopify paths on airocide.com.</p>
          <p class="summary">The next quality improvement would be connecting Shopify directly so KES Technology can report confirmed order count, net sales, refunds, product mix, customer count, and replacement-kit sales from the platform that owns ecommerce revenue.</p>
          <p class="source-note">Reporting period: {safe(period_label(refresh["period"]))}. Test page only. Live report remains unchanged until approved.</p>
        </section>
      </main>
    </div>
  </body>
</html>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page(), encoding="utf-8")
    print(f"Wrote Airocide Systems test report to {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
