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
                <tr><th>Channel</th><th>Sessions</th><th>Active Users</th><th>Key Events</th><th>Commercial Read</th></tr>
              </thead>
              <tbody>
                <tr><td>Direct</td><td>9,904</td><td>9,730</td><td>0</td><td>Brand recognition / returning demand</td></tr>
                <tr><td>Organic Search</td><td>722</td><td>559</td><td>0</td><td>Commercial SEO visibility</td></tr>
                <tr><td>Referral</td><td>222</td><td>166</td><td>0</td><td>External site discovery</td></tr>
                <tr><td>Unassigned</td><td>82</td><td>71</td><td>0</td><td>Unclassified GA4 traffic</td></tr>
                <tr><td>Organic Social</td><td>49</td><td>46</td><td>0</td><td>Social visibility</td></tr>
                <tr><td>AI Assistant</td><td>13</td><td>11</td><td>0</td><td>Early AI-driven discovery signal</td></tr>
              </tbody>
            </table>
          </div>
          <p class="source-note">Commercial view uses www.airocide.com only. KES Technology residential revenue, purchases, and Shopify behavior are intentionally separated into the residential section below.</p>
        </section>"""


def page() -> str:
    html = SOURCE.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\n        <section class=\"card\">\n          <h2>Website Behavior and Organic Lead Path</h2>.*?\n        </section>\n\n        <section class=\"card\">\n          <h2>Google Search Console Visibility</h2>",
        re.S,
    )
    replacement = (
        "\n"
        + commercial_behavior_section()
        + "\n\n        <section class=\"card\">\n          <h2>Google Search Console Visibility</h2>"
    )
    html, count = pattern.subn(replacement, html, count=1)
    if count != 1:
        raise RuntimeError("Could not replace Website Behavior and Organic Lead Path section.")
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
