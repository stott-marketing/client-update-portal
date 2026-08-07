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


def nonbranded_demand_section() -> str:
    return """
        <section class="card">
          <h2>Non-Branded Commercial Search Demand</h2>
          <p class="summary">Branded and misspelled searches confirm recognition for Airocide, but the stronger content signal is non-branded commercial demand. These queries show the topics buyers and researchers are searching before they already know Airocide Systems by name.</p>
          <p class="summary">The current query footprint supports the case-study and vertical-content strategy: stadiums and public spaces, cannabis grow rooms, ethylene and cold storage, postharvest produce, Far-UVC, sports facilities, and commercial air disinfection are already appearing in Google Search Console.</p>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Non-Branded Query</th><th>Impr.</th><th>Clicks</th><th>CTR</th><th>Position</th><th>Content Support</th></tr>
              </thead>
              <tbody>
                <tr><td>air quality solutions stadiums</td><td>116</td><td>0</td><td>0.0%</td><td>5.8</td><td>Public spaces / sports venues content path</td></tr>
                <tr><td>cannabis grow room air purification</td><td>73</td><td>0</td><td>0.0%</td><td>19.5</td><td>Cannabis vertical content path</td></tr>
                <tr><td>air disinfection system</td><td>72</td><td>0</td><td>0.0%</td><td>20.1</td><td>Commercial air disinfection category</td></tr>
                <tr><td>ethylene gas removal</td><td>59</td><td>0</td><td>0.0%</td><td>12.0</td><td>Del Monte / food safety case-study support</td></tr>
                <tr><td>postharvest air purification produce</td><td>40</td><td>0</td><td>0.0%</td><td>5.0</td><td>Postharvest and produce preservation content</td></tr>
                <tr><td>air disinfection solutions</td><td>38</td><td>0</td><td>0.0%</td><td>11.5</td><td>Core commercial disinfection content</td></tr>
                <tr><td>commercial air disinfection system</td><td>37</td><td>0</td><td>0.0%</td><td>19.7</td><td>Commercial facilities / HVAC content path</td></tr>
                <tr><td>public space air disinfection</td><td>36</td><td>0</td><td>0.0%</td><td>15.6</td><td>Public spaces and occupied buildings content</td></tr>
                <tr><td>ethylene gas removal cold storage</td><td>33</td><td>0</td><td>0.0%</td><td>4.1</td><td>Cold storage / shelf-life case-study support</td></tr>
                <tr><td>sports facility air purification systems</td><td>33</td><td>0</td><td>0.0%</td><td>4.6</td><td>Sports venues / public facility content path</td></tr>
                <tr><td>far-uvc 222nm safe occupied spaces</td><td>29</td><td>0</td><td>0.0%</td><td>6.1</td><td>Roger Williams / Far-UVC case-study support</td></tr>
                <tr><td>cannabis cultivation air disinfection</td><td>27</td><td>0</td><td>0.0%</td><td>7.0</td><td>Cannabis cultivation content path</td></tr>
              </tbody>
            </table>
          </div>
          <p class="source-note">Source: Google Search Console, Apr 1 - Aug 5, 2026. Branded and Airocide-misspelling queries were excluded so this table reflects non-branded commercial demand.</p>
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

    conversion_marker = '\n        <section class="card">\n          <h2>Conversion Tracking, Leads, and Phone Call Visibility</h2>'
    if conversion_marker not in html:
        raise RuntimeError("Could not insert Non-Branded Commercial Search Demand section.")
    html = html.replace(
        conversion_marker,
        "\n" + nonbranded_demand_section() + "\n" + conversion_marker,
        1,
    )

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
