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


def kes_section(hostname: dict, refresh: dict) -> str:
    kes = host_totals(hostname, KES_HOSTS)
    kes_product_views = event_count(hostname, KES_HOSTS, "view_item")
    kes_add_to_carts = event_count(hostname, KES_HOSTS, "add_to_cart")
    kes_checkouts = event_count(hostname, KES_HOSTS, "begin_checkout")
    kes_form_starts = event_count(hostname, KES_HOSTS, "form_start")
    kes_form_submits = event_count(hostname, KES_HOSTS, "form_submit")
    kes_contact_views = page_value(hostname, KES_HOSTS, {"/pages/contact-us"})
    purchase_rate = (kes["purchases"] / kes_checkouts * 100) if kes_checkouts else 0

    return f"""
        <div class="section-label">KES Technology Residential</div>

        <section class="card">
          <h2>KES Technology Residential Executive Summary</h2>
          <p class="summary">KES Technology is shown as a separate residential ecommerce view because shop.airocide.com supports the replacement/product business, while Airocide.com remains focused on the commercial Airocide Systems SEO and lead-generation strategy.</p>
          <p class="summary">Residential performance should be evaluated by ecommerce activity: revenue, purchases, product views, add-to-cart behavior, checkout activity, and Shopify order data. This keeps the residential business visible without blending it into the commercial Airocide Systems growth story.</p>
          <div class="grid-3">
            <article class="panel seo"><h3>Revenue</h3><p><strong>{money(kes["revenue"])}</strong><br>GA4 ecommerce revenue grouped under KES Technology.</p></article>
            <article class="panel seo"><h3>Purchases</h3><p><strong>{number(kes["purchases"])}</strong><br>Residential ecommerce purchase events.</p></article>
            <article class="panel foundation"><h3>Sessions</h3><p><strong>{number(kes["sessions"])}</strong><br>Residential sessions across Shopify paths.</p></article>
          </div>
          <p class="source-note">KES includes shop.airocide.com plus legacy Shopify paths on airocide.com. Shopify should be treated as the final revenue source of truth for orders, refunds, net sales, product mix, and customer details.</p>
        </section>

        <section class="card">
          <h2>Residential Product and Checkout Activity</h2>
          <div class="grid-3">
            <article class="panel growth"><h3>Product Views</h3><p><strong>{number(kes_product_views)}</strong><br>Product detail views.</p></article>
            <article class="panel growth"><h3>Add to Cart</h3><p><strong>{number(kes_add_to_carts)}</strong><br>Add-to-cart events.</p></article>
            <article class="panel seo"><h3>Checkout to Purchase</h3><p><strong>{purchase_rate:.1f}%</strong><br>{number(kes["purchases"])} purchases from {number(kes_checkouts)} checkout-start events.</p></article>
          </div>
        </section>

        <section class="card">
          <h2>Residential Contact Path</h2>
          <p class="summary">Residential contact behavior is evaluated separately from the commercial Contact page. KES Technology contact activity appears on the Shopify contact path, including legacy Shopify paths from the prior domain setup.</p>
          <div class="grid-3">
            <article class="panel foundation"><h3>Contact Page Views</h3><p><strong>{number(kes_contact_views)}</strong><br>Views of /pages/contact-us across KES paths.</p></article>
            <article class="panel growth"><h3>Form Starts</h3><p><strong>{number(kes_form_starts)}</strong><br>Residential form-start events.</p></article>
            <article class="panel growth"><h3>Form Submissions</h3><p><strong>{number(kes_form_submits)}</strong><br>Residential form-submit events.</p></article>
          </div>
          <p class="source-note">The Shopify source confirms the KES contact page uses Shopify's native contact form. Shopify should be checked to confirm where submissions are delivered and whether they are stored or only emailed.</p>
        </section>

        <section class="card">
          <h2>Residential Reporting Notes</h2>
          <p class="summary">This residential section uses GA4 hostname and page-path separation to avoid mixing commercial lead generation with residential ecommerce. KES Technology residential reporting is based on shop.airocide.com plus legacy Shopify paths on airocide.com.</p>
          <p class="summary">Shopify remains the source of truth for confirmed order count, net sales, refunds, product mix, customer count, and replacement-kit sales because that platform owns the residential ecommerce transaction data.</p>
          <p class="source-note">Reporting period: {safe(period_label(refresh["period"]))}.</p>
        </section>
"""


def page() -> str:
    refresh = load("refresh_summary.json")
    hostname = load("ga4_hostname.json")
    master_path = ROOT / "firebase-static" / "public" / "airocide-systems" / "index.html"
    html_text = master_path.read_text(encoding="utf-8")

    css = """
      .section-label { margin: 18px 0 0; padding: 15px 18px; border-radius: 8px; background: #0B1E3C; color: #fff; font-size: 14px; font-weight: 900; letter-spacing: .02em; text-transform: uppercase; }
"""
    html_text = html_text.replace("\n      @media (max-width: 820px)", css + "\n      @media (max-width: 820px)", 1)
    html_text = html_text.replace(
        "<title>Airocide Systems SEO Update | Stott Marketing</title>",
        "<title>Airocide Systems + KES Technology Test Report | Stott Marketing</title>",
        1,
    )
    insertion = kes_section(hostname, refresh)
    marker = '\n        <section id="posted-updates-section" class="card" hidden>'
    if marker not in html_text:
        raise RuntimeError("Could not find insertion point for KES section.")
    return html_text.replace(marker, insertion + marker, 1)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page(), encoding="utf-8")
    print(f"Wrote Airocide Systems test report to {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
