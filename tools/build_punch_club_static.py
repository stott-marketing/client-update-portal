from __future__ import annotations

import re
import urllib.request
from datetime import date
from pathlib import Path


BASE_URL = "https://clients.stott.marketing"
OUT = Path("firebase-static/public/punch-club/index.html")


def fetch(path: str) -> str:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=30) as response:
        body = response.read().decode("utf-8")
    if not body.lower().lstrip().startswith("<!doctype"):
        body = "<!doctype html>\n" + body
    return body


def replace_once(content: str, old: str, new: str) -> str:
    if old not in content:
        raise RuntimeError(f"Expected Punch Club content not found: {old[:90]}")
    return content.replace(old, new, 1)


def replace_optional(content: str, old: str, new: str) -> str:
    return content.replace(old, new, 1) if old in content else content


def replace_between(content: str, start: str, end: str, replacement: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    updated, count = pattern.subn(replacement + "\n\n        " + end, content, count=1)
    if count != 1:
        raise RuntimeError(f"Expected one Punch Club section between {start[:60]!r} and {end[:60]!r}; found {count}")
    return updated


def replace_portfolio_area(content: str, replacement: str) -> str:
    end = '<section class="card wide-card" aria-labelledby="reporting-title">'
    starts = [
        '<section class="card wide-card" aria-labelledby="approval-title">',
        '<section class="card wide-card" aria-labelledby="portfolio-title">',
    ]
    for start in starts:
        pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
        updated, count = pattern.subn(replacement + "\n\n        " + end, content, count=1)
        if count == 1:
            return updated
    raise RuntimeError("Expected old Punch dashboard or existing Punch portfolio section before Agency Reporting Tool.")


def inject_public_updates(content: str) -> str:
    if "clientPublicUpdates" in content:
        return content

    styles = """
      .posted-updates {
        display: grid;
        gap: 12px;
      }
      .posted-update {
        padding: 15px 0;
        border-top: 1px solid var(--line, #dce3ea);
      }
      .posted-update:first-child { border-top: 0; padding-top: 0; }
      .posted-update p { margin: 0; line-height: 1.6; }
      .dynamic-takeaways {
        display: grid;
        gap: 10px;
        margin: 0;
        padding: 0;
        list-style: none;
      }
      .dynamic-takeaways li {
        display: grid;
        grid-template-columns: 22px 1fr;
        gap: 10px;
        align-items: start;
        padding: 10px 0;
        border-top: 1px solid var(--line, #dce3ea);
      }
      .dynamic-takeaways .box {
        width: 17px;
        height: 17px;
        margin-top: 3px;
        border: 2px solid #95a8b3;
        border-radius: 4px;
        background: #fff;
      }
"""
    section = """
        <section id="posted-updates-section" class="card wide-card" hidden>
          <h2>Current Updates</h2>
          <div id="posted-updates" class="posted-updates"></div>
          <ul id="dynamic-takeaways" class="dynamic-takeaways"></ul>
        </section>
"""
    script = """
    <script type="module">
      import { initializeApp } from "https://www.gstatic.com/firebasejs/12.6.0/firebase-app.js";
      import {
        collection,
        getDocs,
        getFirestore,
        orderBy,
        query
      } from "https://www.gstatic.com/firebasejs/12.6.0/firebase-firestore.js";

      const firebaseConfig = {
        apiKey: "AIzaSyDRpeu3P6qrbHQ69PsPjOdUZw0slbxTbsA",
        authDomain: "clients.stott.marketing",
        projectId: "stott-mktg-client-update-data",
        storageBucket: "stott-mktg-client-update-data.firebasestorage.app",
        messagingSenderId: "446049206946",
        appId: "1:446049206946:web:bab80b19302e5d03a58dfb",
        measurementId: "G-PFDY1X5S54"
      };

      const app = initializeApp(firebaseConfig);
      const db = getFirestore(app);

      function addPostedUpdate(text) {
        const section = document.querySelector("#posted-updates-section");
        const list = document.querySelector("#posted-updates");
        const article = document.createElement("article");
        article.className = "posted-update";
        const paragraph = document.createElement("p");
        paragraph.textContent = text || "";
        article.append(paragraph);
        list.append(article);
        section.hidden = false;
      }

      function addMeetingTakeaway(text, completed) {
        const section = document.querySelector("#posted-updates-section");
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
        section.hidden = false;
      }

      async function loadPostedUpdates() {
        try {
          const snapshot = await getDocs(query(
            collection(db, "clientPublicUpdates", "punch-club", "items"),
            orderBy("posted_at", "asc")
          ));
          snapshot.forEach((documentSnapshot) => {
            const entry = documentSnapshot.data();
            if (!entry.text) return;
            if (entry.entry_type === "meeting_takeaway") {
              addMeetingTakeaway(entry.text, Boolean(entry.completed));
            } else {
              addPostedUpdate(entry.text);
            }
          });
        } catch (error) {
          console.error("Could not load posted client updates", error);
        }
      }

      loadPostedUpdates();
    </script>
"""
    content = replace_once(content, "</style>", styles + "\n    </style>")
    content = replace_once(content, "      </main>", section + "\n      </main>")
    content = replace_once(content, "  </body>", script + "\n  </body>")
    return content


def portfolio_css() -> str:
    return """
      .portfolio-stack {
        display: grid;
        gap: 14px;
      }

      .portfolio-card {
        display: grid;
        gap: 14px;
        padding: 24px;
      }

      .client-titleline {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 20px;
        border-bottom: 1px solid var(--line);
        padding-bottom: 14px;
      }

      .client-titleline h3 {
        margin: 0 0 7px;
        font-size: 22px;
        line-height: 1.12;
      }

      .client-titleline p {
        margin: 0;
        color: var(--muted);
        line-height: 1.45;
      }

      .client-titleline .tag {
        align-self: flex-start;
        margin-top: 2px;
        flex: 0 0 auto;
      }

      .client-update {
        display: grid;
        gap: 6px;
      }

      .section-label {
        margin: 0;
        color: #516070;
        font-size: 12px;
        font-weight: 850;
        letter-spacing: .04em;
        text-transform: uppercase;
      }

      .client-update p {
        margin: 0;
        color: #263240;
        font-size: 15px;
        line-height: 1.58;
      }

      .performance-line {
        display: grid;
        grid-template-columns: 22px 1fr;
        gap: 10px;
        align-items: start;
        padding: 12px 14px;
        border: 1px solid #cfe8d9;
        border-radius: 8px;
        background: #f1fbf5;
        color: #173f28;
        line-height: 1.5;
      }

      .performance-line::before {
        content: "";
        width: 11px;
        height: 11px;
        margin-top: 6px;
        border-radius: 999px;
        background: #24a15a;
      }

      .metric-group {
        display: grid;
        gap: 8px;
      }

      .metric-group h4 {
        margin: 0;
        color: #273545;
        font-size: 15px;
      }

      .portfolio-card .metrics {
        display: flex;
        flex-wrap: wrap;
        gap: 0;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: transparent;
      }

      .portfolio-card .metric {
        flex: 1 1 165px;
        min-height: 104px;
        border-right: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
        background: #fff;
      }

"""


def portfolio_polish_css() -> str:
    return """
      .portfolio-polish-v2 { display: none; }

      .portfolio-card.client-card {
        padding: 24px !important;
        gap: 14px;
      }

      .portfolio-card .client-titleline {
        gap: 20px;
        padding-bottom: 14px;
      }

      .portfolio-card .client-titleline h3 {
        margin-bottom: 7px;
        line-height: 1.12;
      }

      .portfolio-card .client-titleline p {
        line-height: 1.45;
      }

      .portfolio-card .client-titleline .tag {
        align-self: flex-start;
        flex: 0 0 auto;
        margin-top: 2px;
      }

      .portfolio-card .metrics {
        display: flex !important;
        flex-wrap: wrap;
        gap: 0;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: transparent !important;
      }

      .portfolio-card .metric {
        flex: 1 1 165px;
        min-height: 104px;
        border-right: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
        background: #fff;
      }
"""


def portfolio_section() -> str:
    return """
        <section class="card wide-card" aria-labelledby="portfolio-title">
          <h2 id="portfolio-title">Punch Club Client Portfolio</h2>
          <p>
            Punch Club is the parent account. The client updates below are organized by child account so each business has its own narrative, source-specific performance summary, and metrics.
          </p>
          <div class="portfolio-stack">
            <article class="card client-card portfolio-card">
              <div class="client-titleline">
                <div>
                  <h3>Punch Transfers</h3>
                  <p>Website performance, Google Ads delivery, creative review, Shopify, and shipping logic.</p>
                </div>
                <span class="tag warning">Creative review</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>Punch Transfers has strong traffic momentum, but the immediate blocker is creative quality. Beth's submitted image did not meet Google Ads criteria, so the next move is to revisit the sample creative set and create a stronger ad direction before pushing spend harder. At the same time, Shopify purchase contacts and shipping logic still need cleanup so the store workflow is easier to report and manage.</p>
              </div>
              <div class="performance-line"><strong>Punch Transfers has strong reach and traffic growth: paid impressions are up 1371.3%, paid clicks are up 197.8%, and average CPC is down 62.8%. The immediate blocker is creative quality, because the latest image did not meet Google Ads criteria.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Punch Transfers performance metrics">
                  <div class="metric"><span>Sessions</span><strong>657</strong><div class="change">+88.3% vs previous</div></div>
                  <div class="metric"><span>Key events</span><strong>22</strong><div class="change">+37.5% vs previous</div></div>
                  <div class="metric"><span>GA4 revenue</span><strong>$2.4k</strong><div class="change">+66.4% vs previous</div></div>
                  <div class="metric"><span>Ads clicks</span><strong>542</strong><div class="change">+197.8% vs previous</div></div>
                  <div class="metric"><span>Avg CPC</span><strong>$0.47</strong><div class="change">-62.8% vs previous</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card">
              <div class="client-titleline">
                <div>
                  <h3>Chem Nut Supply</h3>
                  <p>Website performance, Google Ads, revenue trend, and invoice follow-up.</p>
                </div>
                <span class="tag">Ads live</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>Chem Nut Supply is the strongest performance story in the current portfolio. Website sessions, GA4 revenue, Ads conversions, conversion value, clicks, impressions, and ROAS all improved versus the prior 30 days. The next step is to continue optimization while confirming invoice receipt and payment.</p>
              </div>
              <div class="performance-line"><strong>Chem Nut Supply is the most positive performance story this week: website sessions, revenue, conversions, conversion value, ROAS, clicks, and impressions all improved versus the prior 30-day period.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Chem Nut Supply performance metrics">
                  <div class="metric"><span>Sessions</span><strong>2,374</strong><div class="change">+56.8% vs previous</div></div>
                  <div class="metric"><span>Key events</span><strong>35</strong><div class="change">+45.8% vs previous</div></div>
                  <div class="metric"><span>GA4 revenue</span><strong>$1.4k</strong><div class="change">+27.7% vs previous</div></div>
                  <div class="metric"><span>Ads conversions</span><strong>36.0</strong><div class="change">+111.2% vs previous</div></div>
                  <div class="metric"><span>ROAS</span><strong>1.03x</strong><div class="change">+58.9% vs previous</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card">
              <div class="client-titleline">
                <div>
                  <h3>LC Mechanical</h3>
                  <p>Google Ads delivery, website performance, corrected activity period, and Jotform access.</p>
                </div>
                <span class="tag risk">Review delivery</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>LC Mechanical now has Google Ads data connected, but performance needs review. Spend is lower, clicks are sharply lower, and conversions moved from 10 to 0, so campaign delivery and conversion tracking should be reviewed. The activity period is May, not April. Jotform access can wait until Aaron is available.</p>
              </div>
              <div class="performance-line"><strong>LC Mechanical now has Google Ads data connected. Delivery is softer than the previous 30 days: spend is down 38.4%, impressions are down 32.0%, clicks are down 82.0%, and conversions moved from 10 to 0.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="LC Mechanical performance metrics">
                  <div class="metric"><span>Sessions</span><strong>598</strong><div class="risk-change">-68.4% vs previous</div></div>
                  <div class="metric"><span>Key events</span><strong>3</strong><div class="risk-change">-25.0% vs previous</div></div>
                  <div class="metric"><span>Ads spend</span><strong>$179</strong><div class="change">-38.4% vs previous</div></div>
                  <div class="metric"><span>Ads clicks</span><strong>450</strong><div class="risk-change">-82.0% vs previous</div></div>
                  <div class="metric"><span>Conversions</span><strong>0</strong><div class="risk-change">Down from 10</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card">
              <div class="client-titleline">
                <div>
                  <h3>Phil Medeiros</h3>
                  <p>SEO indexing, website traffic, and organic visibility.</p>
                </div>
                <span class="tag">SEO</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>SEO indexing work is progressing. Twenty-one pages have been submitted, with indexing limited by the 10-per-day submission quota. The next step is to continue URL submissions and evaluate whether a bulk indexing service is worth testing.</p>
              </div>
              <div class="performance-line"><strong>Phil Medeiros is showing strong organic growth: sessions are up 502.1%, organic clicks are up 93.3%, and search impressions are up 274.8%.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Phil Medeiros performance metrics">
                  <div class="metric"><span>Sessions</span><strong>1,752</strong><div class="change">+502.1% vs previous</div></div>
                  <div class="metric"><span>Active users</span><strong>1,630</strong><div class="change">+554.6% vs previous</div></div>
                  <div class="metric"><span>Organic clicks</span><strong>29</strong><div class="change">+93.3% vs previous</div></div>
                  <div class="metric"><span>Search impressions</span><strong>757</strong><div class="change">+274.8% vs previous</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card">
              <div class="client-titleline">
                <div>
                  <h3>South Coast Towing</h3>
                  <p>Website traffic and organic search visibility.</p>
                </div>
                <span class="tag">Tracked</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>South Coast Towing has live website and Search Console data. Traffic is stable to improving, and organic visibility is moving in the right direction. The next step is to keep monitoring the organic lift and prepare to add Ads data when active reporting is ready.</p>
              </div>
              <div class="performance-line"><strong>South Coast Towing is trending up organically: sessions are up 8.5%, organic clicks are up 21.6%, impressions are up 9.5%, and average position improved by 1.6 spots.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="South Coast Towing performance metrics">
                  <div class="metric"><span>Sessions</span><strong>1,730</strong><div class="change">+8.5% vs previous</div></div>
                  <div class="metric"><span>Organic clicks</span><strong>169</strong><div class="change">+21.6% vs previous</div></div>
                  <div class="metric"><span>Search impressions</span><strong>6,812</strong><div class="change">+9.5% vs previous</div></div>
                  <div class="metric"><span>Avg position</span><strong>10.3</strong><div class="change">Improved 1.6 spots</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card">
              <div class="client-titleline">
                <div>
                  <h3>Tony's Auto</h3>
                  <p>Website traffic and organic search visibility.</p>
                </div>
                <span class="tag">Tracked</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>Tony's Auto has live website and organic search reporting. Sessions and impressions improved, but organic CTR and clicks need attention. The next focus is improving search-result messaging and page alignment to recover organic CTR.</p>
              </div>
              <div class="performance-line"><strong>Tony's Auto has modest traffic growth with a search-message opportunity: sessions are up 7.6% and impressions are up 16.1%, but organic clicks are down 5.1% and CTR is down 18.3%.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Tony's Auto performance metrics">
                  <div class="metric"><span>Sessions</span><strong>241</strong><div class="change">+7.6% vs previous</div></div>
                  <div class="metric"><span>Organic clicks</span><strong>37</strong><div class="risk-change">-5.1% vs previous</div></div>
                  <div class="metric"><span>Search impressions</span><strong>5,819</strong><div class="change">+16.1% vs previous</div></div>
                  <div class="metric"><span>Organic CTR</span><strong>0.64%</strong><div class="risk-change">-18.3% vs previous</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card">
              <div class="client-titleline">
                <div>
                  <h3>Punch Creatives</h3>
                  <p>Parent account website activity, creative support, and CRM cleanup.</p>
                </div>
                <span class="tag">Tracked</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>Punch Creatives remains the parent operating account and creative support layer. QuickBooks data was reformatted and uploaded into Go High Level. The next cleanup export should include Company Name and Email only, then the Existing Clients - PC smart list should be created.</p>
              </div>
              <div class="performance-line"><strong>QuickBooks data was received, reformatted, and uploaded into Go High Level; the next database cleanup export should include Company Name and Email only.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Punch Creatives performance metrics">
                  <div class="metric"><span>Sessions</span><strong>205</strong><div class="muted-change">Flat vs previous</div></div>
                  <div class="metric"><span>Active users</span><strong>114</strong><div class="risk-change">-3.4% vs previous</div></div>
                  <div class="metric"><span>Engagement rate</span><strong>42.9%</strong><div class="risk-change">Down from 48.3%</div></div>
                  <div class="metric"><span>CRM</span><strong>Updated</strong><div class="change">QuickBooks to GHL</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card">
              <div class="client-titleline">
                <div>
                  <h3>Grub Tub Rentals</h3>
                  <p>Facebook launch and short-form video adjustment.</p>
                </div>
                <span class="tag">Facebook only</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>Facebook marketing has launched, but the submitted video needs to be shortened to 15 seconds for the selected ad placement. Once the creative issue is resolved, reporting sources should be mapped so launch metrics can be added to the portfolio view.</p>
              </div>
              <div class="performance-line"><strong>Grub Tub's Facebook marketing has launched, but the submitted video needs to be reduced to 15 seconds for the selected advertising channel.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Grub Tub Rentals performance metrics">
                  <div class="metric"><span>Facebook Ads</span><strong>Launched</strong><div class="muted-change">Creative adjustment</div></div>
                  <div class="metric"><span>Video</span><strong>Revise</strong><div class="muted-change">15-second limit</div></div>
                  <div class="metric"><span>GA4</span><strong>Pending</strong><div class="muted-change">Property ID needed</div></div>
                  <div class="metric"><span>Leads/actions</span><strong>Pending</strong><div class="muted-change">Define key events</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card">
              <div class="client-titleline">
                <div>
                  <h3>Dr. Mackenzie</h3>
                  <p>Google Ads billing verification and approval blocker.</p>
                </div>
                <span class="tag risk">Needs approval</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>Google Ads support is requiring card verification. The next decision is whether to approve the temporary Punch card verification path or use the invoice-first fallback. With approval, the Punch card can be added temporarily and removed after verification, then Dr. Mackenzie's card can be set as the primary payment method.</p>
              </div>
              <div class="performance-line"><strong>Dr. Mackenzie still needs a billing verification decision before the account can move forward cleanly.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Dr. Mackenzie performance metrics">
                  <div class="metric"><span>Google Ads</span><strong>Blocked</strong><div class="risk-change">Billing verification</div></div>
                  <div class="metric"><span>Approval</span><strong>Needed</strong><div class="risk-change">Temporary card add</div></div>
                  <div class="metric"><span>Campaigns</span><strong>Pending</strong><div class="muted-change">After verification</div></div>
                </div>
              </div>
            </article>
          </div>
        </section>

        """


def enhance_punch_club(content: str) -> str:
    published = date.today().strftime("%B %-d, %Y")
    content = re.sub(
        r"\n\s*\.action-register \{.*?\.action-row small \{.*?\n\s*\}",
        "",
        content,
        count=1,
        flags=re.S,
    )
    if "data-refresh-action" not in content:
        button_css = """
      .topbar-actions {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 10px;
        flex-wrap: wrap;
      }

      .update-data-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 38px;
        padding: 8px 14px;
        border: 1px solid #1d3557;
        border-radius: 8px;
        background: #1d3557;
        color: #fff;
        font-size: 12px;
        font-weight: 850;
        letter-spacing: .03em;
        text-decoration: none;
        text-transform: uppercase;
        box-shadow: 0 8px 18px rgba(29, 53, 87, .18);
        cursor: pointer;
      }

      .update-data-button:hover {
        background: #12243d;
      }

      .data-refresh-banner {
        display: none;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        margin: 0 0 16px;
        padding: 13px 15px;
        border: 1px solid #c8e1ee;
        border-radius: 8px;
        background: #f2f9fd;
        color: #25495f;
        line-height: 1.45;
      }

      .data-refresh-banner[aria-hidden="false"] {
        display: flex;
      }

      .refresh-spinner {
        width: 18px;
        height: 18px;
        flex: 0 0 auto;
        border: 3px solid #c8e1ee;
        border-top-color: #1d3557;
        border-radius: 999px;
        animation: refreshSpin .8s linear infinite;
      }

      .data-refresh-banner.done .refresh-spinner,
      .data-refresh-banner.pending .refresh-spinner {
        animation: none;
        border-color: #2eb872;
        background: #2eb872;
      }

      .data-refresh-copy {
        display: grid;
        gap: 2px;
      }

      .data-refresh-copy strong {
        color: #17354a;
      }

      .data-refresh-copy span {
        color: #416174;
        font-size: 13px;
      }

      @keyframes refreshSpin {
        to { transform: rotate(360deg); }
      }

      .metric-group h4::after {
        content: "Rolling update showing last 30 days vs previous";
        display: block;
        margin-top: 3px;
        color: var(--muted);
        font-size: 11px;
        font-weight: 720;
        letter-spacing: 0;
        text-transform: none;
      }
"""
        content = replace_once(content, "</style>", button_css + "\n    </style>")
        content = replace_once(
            content,
            '<span class="pill"><span class="dot" aria-hidden="true"></span> Private client update</span>',
            """<div class="topbar-actions">
          <button class="update-data-button" data-refresh-action data-refresh-endpoint="" data-refresh-fallback-url="https://github.com/stott-marketing/client-update-portal/actions/workflows/deploy-firebase-hosting.yml" type="button" title="Open the secure server-side refresh and deploy workflow">UPDATE DATA</button>
          <span class="pill"><span class="dot" aria-hidden="true"></span> Private client update</span>
        </div>""",
        )
    content = replace_optional(
        content,
        '<a class="update-data-button" data-refresh-action href="https://github.com/stott-marketing/client-update-portal/actions/workflows/deploy-firebase-hosting.yml" target="_blank" rel="noreferrer" title="Open the secure server-side refresh and deploy workflow">UPDATE DATA</a>',
        '<button class="update-data-button" data-refresh-action data-refresh-endpoint="" data-refresh-fallback-url="https://github.com/stott-marketing/client-update-portal/actions/workflows/deploy-firebase-hosting.yml" type="button" title="Open the secure server-side refresh and deploy workflow">UPDATE DATA</button>',
    )
    content = replace_optional(
        content,
        '<a class="update-data-button" data-refresh-action data-refresh-endpoint="" href="https://github.com/stott-marketing/client-update-portal/actions/workflows/deploy-firebase-hosting.yml" target="_blank" rel="noreferrer" title="Open the secure server-side refresh and deploy workflow">UPDATE DATA</a>',
        '<button class="update-data-button" data-refresh-action data-refresh-endpoint="" data-refresh-fallback-url="https://github.com/stott-marketing/client-update-portal/actions/workflows/deploy-firebase-hosting.yml" type="button" title="Open the secure server-side refresh and deploy workflow">UPDATE DATA</button>',
    )
    if "data-refresh-banner" not in content:
        content = replace_once(
            content,
            "      <main>",
            """      <main>
        <div id="data-refresh-banner" class="data-refresh-banner" aria-hidden="true" aria-live="polite">
          <span class="refresh-spinner" aria-hidden="true"></span>
          <div class="data-refresh-copy">
            <strong id="data-refresh-title">Obtaining updated client data</strong>
            <span id="data-refresh-detail">Rolling last-30-day performance is being refreshed against the previous period.</span>
          </div>
        </div>""",
        )
    if "data-refresh-script" not in content:
        refresh_script = """
    <script data-refresh-script>
      (() => {
        const banner = document.querySelector("#data-refresh-banner");
        const title = document.querySelector("#data-refresh-title");
        const detail = document.querySelector("#data-refresh-detail");
        const button = document.querySelector("[data-refresh-action]");
        const params = new URLSearchParams(window.location.search);

        function showBanner(state, heading, message) {
          if (!banner || !title || !detail) return;
          banner.classList.remove("done", "pending", "loading");
          banner.classList.add(state);
          banner.setAttribute("aria-hidden", "false");
          title.textContent = heading;
          detail.textContent = message;
        }

        if (params.get("refreshed") === "1") {
          showBanner(
            "done",
            "Data refreshed",
            "This report is showing the latest available rolling last 30 days vs previous period metrics."
          );
        }

        if (!button) return;
        button.addEventListener("click", async (event) => {
          event.preventDefault();
          const endpoint = button.getAttribute("data-refresh-endpoint") || "";

          showBanner(
            "loading",
            "Obtaining updated client data",
            "Refreshing connected sources for each Punch Club child account using rolling last 30 days vs previous period."
          );

          if (!endpoint) {
            window.setTimeout(() => {
              showBanner(
                "pending",
                "Secure refresh runner needed",
                "Private API credentials cannot run in this public page. Connect a secure refresh endpoint to run the API pull, then this button will refresh the report automatically."
              );
            }, 650);
            return;
          }

          try {
            const response = await fetch(endpoint, { method: "POST", credentials: "include" });
            if (!response.ok) throw new Error(`Refresh failed with status ${response.status}`);
            showBanner(
              "done",
              "Data refreshed",
              "Reloading the report with rolling last 30 days vs previous period metrics."
            );
            window.setTimeout(() => {
              const next = new URL(window.location.href);
              next.searchParams.set("refreshed", "1");
              window.location.href = next.toString();
            }, 900);
          } catch (error) {
            showBanner(
              "pending",
              "Refresh could not complete",
              "The secure refresh endpoint did not respond. Please run the server-side workflow, then reload this report."
            );
          }
        });
      })();
    </script>
"""
        content = replace_once(content, "  </body>", refresh_script + "\n  </body>")

    if "portfolio-stack" not in content:
        content = replace_once(content, "</style>", portfolio_css() + "\n    </style>")
    if "portfolio-polish-v2" not in content:
        content = replace_once(content, "</style>", portfolio_polish_css() + "\n    </style>")

    content = replace_optional(
        content,
        "<h1 id=\"page-title\">Punch Club</h1>",
        "<h1 id=\"page-title\">Punch Club Portfolio Performance</h1>",
    )
    content = replace_optional(
        content,
        "May activity, June progress, reporting rollout, and account actions\n              across active Punch Club marketing work. Prepared by Stott Marketing\n              with updates through June 22, 2026.",
        "Performance reporting, rollout status, and account actions across active Punch Club marketing work. "
        f"Published {published}; source data dates vary by connected account.",
    )
    content = replace_optional(
        content,
        '<span class="pill">Updated June 23, 2026</span>',
        '<span class="pill">Source notes from June 23, 2026</span>',
    )
    content = replace_optional(
        content,
        "<span>Paid impressions from connected Ads accounts</span>",
        "<span>Paid impressions across connected Ads accounts</span>",
    )
    content = replace_optional(
        content,
        "<span>Tracked visits and paid clicks</span>",
        "<span>Tracked visits and paid clicks across clients</span>",
    )
    content = replace_optional(
        content,
        "<span>Tracked leads/actions</span>",
        "<span>Tracked leads and key actions</span>",
    )
    content = replace_optional(
        content,
        "<span>Tracked revenue/value</span>",
        "<span>Tracked revenue and conversion value</span>",
    )
    content = re.sub(
        r'\s*<ul class="summary-list">\s*'
        r"<li>Punch Transfers has strong reach.*?</li>\s*"
        r"<li>Chem Nut Supply is the most positive.*?</li>\s*"
        r"<li>LC Mechanical now has Google Ads.*?</li>\s*"
        r"<li>Grub Tub.*?</li>\s*"
        r"<li>Dr\. Mackenzie still needs.*?</li>\s*"
        r"<li>QuickBooks data was received.*?</li>\s*"
        r"</ul>",
        "",
        content,
        count=1,
        flags=re.S,
    )
    content = replace_portfolio_area(content, portfolio_section())
    return content


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    content = enhance_punch_club(inject_public_updates(fetch("/punch-club")))
    OUT.write_text(content, encoding="utf-8")
    print(f"Wrote Punch Club report to {OUT}")


if __name__ == "__main__":
    main()
