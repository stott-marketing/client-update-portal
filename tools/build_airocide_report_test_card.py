from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "firebase-static" / "public" / "airocide-systems-test" / "index.html"
OUT = ROOT / "firebase-static" / "public" / "airocide-systems-test-card"


def commercial_behavior_section() -> str:
    return """
        <section class="card">
          <h2>Website Behavior and Organic Lead Path</h2>
          <div class="grid-3">
            <article class="panel">
              <h3>Commercial Organic Search</h3>
              <p>Organic Search generated 722 sessions and 559 active users on www.airocide.com during the consolidation reporting window. Ecommerce revenue and purchases are excluded here because residential sales belong in the KES Technology section.</p>
            </article>
            <article class="panel">
              <h3>Commercial Contact Path</h3>
              <p>The commercial site recorded 337 Contact page views, 93 form starts, and 31 form submissions on www.airocide.com. This is the cleanest lead-path signal available for the commercial side of the website.</p>
            </article>
            <article class="panel">
              <h3>Direct Brand Demand</h3>
              <p>Direct traffic generated 9,904 sessions and 9,730 active users on www.airocide.com, supporting the brand-recognition side of the consolidation work without mixing in residential ecommerce activity.</p>
            </article>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Channel</th><th>Sessions</th><th>Active Users</th><th>Commercial Read</th></tr>
              </thead>
              <tbody>
                <tr><td>Direct</td><td>9,904</td><td>9,730</td><td>Brand recognition / returning demand</td></tr>
                <tr><td>Organic Search</td><td>722</td><td>559</td><td>Commercial SEO visibility</td></tr>
                <tr><td>Referral</td><td>222</td><td>166</td><td>External site discovery</td></tr>
                <tr><td>Unassigned</td><td>82</td><td>71</td><td>Unclassified GA4 traffic</td></tr>
                <tr><td>Organic Social</td><td>49</td><td>46</td><td>Social visibility</td></tr>
                <tr><td>AI Assistant</td><td>13</td><td>11</td><td>Early AI-driven discovery signal</td></tr>
              </tbody>
            </table>
          </div>
          <p class="source-note">Commercial view uses www.airocide.com only. KES Technology residential revenue, purchases, and Shopify behavior are intentionally separated into the residential section below.</p>
        </section>"""


def commercial_conversion_section() -> str:
    return """
        <section class="card">
          <h2>Conversion Tracking, Leads, and Phone Call Visibility</h2>
          <p class="summary">Commercial conversion tracking has been strengthened on Airocide.com. GA4 is recording meaningful lead-path activity on www.airocide.com, including Contact page views, form starts, and form submissions. Ecommerce purchases and revenue are reported separately under KES Technology because those transactions belong to the residential Shopify experience.</p>
          <p class="summary">One important reporting limitation is phone-call attribution. Airocide.com displays a direct phone number, which is useful for visitors, but call tracking is not currently active. That means phone inquiries may be contributing to lead volume without being connected back to organic search, paid search, specific landing pages, or website content.</p>
          <div class="grid-3">
            <article class="panel growth">
              <h3>Lead activity is measurable</h3>
              <p>The commercial site recorded 337 Contact page views, 93 form starts, and 31 form submissions on www.airocide.com. This confirms measurable inquiry behavior beyond general traffic.</p>
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
          <p class="source-note">WPForms database storage is now active, so new form submissions can be retained for cleaner lead reporting. Historical entry recovery may be available if prior stored submissions are needed.</p>
        </section>"""


def page() -> str:
    html = SOURCE.read_text(encoding="utf-8")
    behavior_pattern = re.compile(
        r"\n        <section class=\"card\">\n          <h2>Website Behavior and Organic Lead Path</h2>.*?\n        </section>\n\n        <section class=\"card\">\n          <h2>Google Search Console Visibility</h2>",
        re.S,
    )
    behavior_replacement = (
        "\n"
        + commercial_behavior_section()
        + "\n\n        <section class=\"card\">\n          <h2>Google Search Console Visibility</h2>"
    )
    html, count = behavior_pattern.subn(behavior_replacement, html, count=1)
    if count != 1:
        raise RuntimeError("Could not replace Website Behavior and Organic Lead Path section.")

    conversion_pattern = re.compile(
        r"\n        <section class=\"card\">\n          <h2>Conversion Tracking, Leads, and Phone Call Visibility</h2>.*?\n        </section>\n\n        <section class=\"card\">\n          <h2>Growth Infrastructure Assessment</h2>",
        re.S,
    )
    conversion_replacement = (
        "\n"
        + commercial_conversion_section()
        + "\n\n        <section class=\"card\">\n          <h2>Growth Infrastructure Assessment</h2>"
    )
    html, count = conversion_pattern.subn(conversion_replacement, html, count=1)
    if count != 1:
        raise RuntimeError("Could not replace Conversion Tracking, Leads, and Phone Call Visibility section.")

    return html.replace(
        "<title>Airocide Systems + KES Technology Test Report | Stott Marketing</title>",
        "<title>Airocide Systems Commercial Card Preview | Stott Marketing</title>",
        1,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page(), encoding="utf-8")
    print(f"Wrote Airocide Systems card preview to {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
