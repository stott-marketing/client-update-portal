from __future__ import annotations

import re
import urllib.request
from datetime import date
from pathlib import Path
from punch_analytics_renderer import apply_analytics


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
      .posted-update ul,
      .posted-update ol {
        margin: 0;
        padding-left: 22px;
        line-height: 1.55;
      }
      .posted-update li + li {
        margin-top: 4px;
      }
      .posted-update a {
        color: #1d5f9f;
        overflow-wrap: anywhere;
      }
      .dynamic-child-update {
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid var(--line, #dce3ea);
      }
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
        <section id="posted-updates-section" class="card wide-card">
          <h2>Current Updates</h2>
          <p>No pending updates need attention at this time.</p>
          <div id="posted-updates" class="posted-updates" hidden></div>
          <ul id="dynamic-takeaways" class="dynamic-takeaways" hidden></ul>
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
        renderFormattedUpdate(article, text);
        list.append(article);
        section.hidden = false;
      }

      function punchChildSlugFromText(text) {
        return String(text || "").match(/^\\[\\[punch_child:([a-z0-9-]+)\\]\\]\\s*/)?.[1] || "";
      }

      function stripPunchChildMarker(text) {
        return String(text || "").replace(/^\\[\\[punch_child:[a-z0-9-]+\\]\\]\\s*/, "");
      }

      function appendTextWithLinks(parent, text) {
        const pattern = /(https?:\\/\\/[^\\s]+)/g;
        String(text || "").split(pattern).forEach((part) => {
          if (!part) return;
          if (part.startsWith("http://") || part.startsWith("https://")) {
            const link = document.createElement("a");
            const canonical = part.replace("https://app.gohighlevel.com/v2/location/vO9C8YeZVrdf3NtNu3iZ/dashboard", "https://app.gohighlevel.com/v2/location/ZaraAYF0bT5SscGtjk8j/dashboard");
            link.href = canonical;
            link.textContent = canonical;
            link.rel = "noreferrer";
            link.target = "_blank";
            parent.append(link);
          } else {
            parent.append(document.createTextNode(part));
          }
        });
      }

      function renderFormattedUpdate(container, text) {
        const cleaned = stripPunchChildMarker(text);
        const lines = cleaned.split(/\\n+/).map((line) => line.trim()).filter(Boolean);
        let list = null;

        lines.forEach((line) => {
          const numbered = line.match(/^\\d+\\.\\s+(.+)/);
          const bulleted = line.match(/^[-*]\\s+(.+)/);
          if (numbered || bulleted) {
            if (!list || list.tagName !== (numbered ? "OL" : "UL")) {
              list = document.createElement(numbered ? "ol" : "ul");
              container.append(list);
            }
            const item = document.createElement("li");
            appendTextWithLinks(item, numbered ? numbered[1] : bulleted[1]);
            list.append(item);
            return;
          }

          list = null;
          const paragraph = document.createElement("p");
          appendTextWithLinks(paragraph, line);
          container.append(paragraph);
        });
      }

      function addChildPostedUpdate(childSlug, text) {
        if (childSlug === "phil-medeiros" || childSlug === "punch-transfers" || childSlug === "south-coast-towing" || childSlug === "tonys-auto") return;
        const card = document.querySelector(`[data-punch-child="${childSlug}"]`);
        const update = card?.querySelector(".client-update");
        if (!update) {
          addPostedUpdate(text);
          return;
        }
        update.querySelectorAll(":scope > :not(.section-label)").forEach((element) => element.remove());
        renderFormattedUpdate(update, text);
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
            const markerChildSlug = punchChildSlugFromText(entry.text);
            if (entry.entry_type === "meeting_takeaway") {
              addMeetingTakeaway(entry.text, Boolean(entry.completed));
            } else if (markerChildSlug) {
              addChildPostedUpdate(markerChildSlug, entry.text);
            } else if (entry.target_section === "digital_marketing_update" && entry.child_client_slug) {
              addChildPostedUpdate(entry.child_client_slug, entry.text);
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
    content = replace_optional(
        content,
        '''        <section id="posted-updates-section" class="card wide-card" hidden>
          <h2>Current Updates</h2>
          <div id="posted-updates" class="posted-updates"></div>
          <ul id="dynamic-takeaways" class="dynamic-takeaways"></ul>
        </section>''',
        '''        <section id="posted-updates-section" class="card wide-card">
          <h2>Current Updates</h2>
          <p>No pending updates need attention at this time.</p>
          <div id="posted-updates" class="posted-updates" hidden></div>
          <ul id="dynamic-takeaways" class="dynamic-takeaways" hidden></ul>
        </section>''',
    )
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

      .client-update ul,
      .client-update ol {
        margin: 0;
        padding-left: 22px;
        color: #263240;
        font-size: 15px;
        line-height: 1.55;
      }

      .client-update li + li {
        margin-top: 4px;
      }

      .client-update a {
        color: #1d5f9f;
        overflow-wrap: anywhere;
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

      .portfolio-card.seo-growth-card {
        border-color: #cbdaf7;
        background: linear-gradient(145deg, #ffffff 0%, #f7faff 62%, #f5f0ff 100%);
        box-shadow: 0 16px 34px rgba(40, 79, 147, 0.10);
      }
      .seo-growth-card .client-titleline .tag {
        color: #234e9b;
        background: #e9f1ff;
      }
      .seo-growth-card .performance-line {
        border-left: 5px solid #4285f4;
        background: linear-gradient(90deg, #eaf2ff 0%, #f5efff 100%);
        color: #183765;
      }
      .seo-growth-card .metrics .metric:nth-child(1) { border-top: 4px solid #4285f4; }
      .seo-growth-card .metrics .metric:nth-child(2) { border-top: 4px solid #673ab7; }
      .seo-growth-card .metrics .metric:nth-child(3) { border-top: 4px solid #f9ab00; }
      .seo-growth-card .metrics .metric:nth-child(4) { border-top: 4px solid #34a853; }
      .seo-growth-card .metric strong { color: #142b4a; }

      .portfolio-card.search-opportunity-card {
        border-color: #b9dfd0;
        background: linear-gradient(145deg, #ffffff 0%, #f3fbf7 64%, #eef6ff 100%);
        box-shadow: 0 16px 34px rgba(23, 112, 79, 0.10);
      }
      .search-opportunity-card .client-titleline .tag {
        color: #12603f;
        background: #ddf5e9;
      }
      .search-opportunity-card .performance-line {
        border-left: 5px solid #22a06b;
        background: linear-gradient(90deg, #e5f7ed 0%, #edf5ff 100%);
        color: #174a37;
      }
      .search-opportunity-card .metrics .metric:nth-child(1) { border-top: 4px solid #22a06b; }
      .search-opportunity-card .metrics .metric:nth-child(2) { border-top: 4px solid #4285f4; }
      .search-opportunity-card .metrics .metric:nth-child(3) { border-top: 4px solid #673ab7; }
      .search-opportunity-card .metrics .metric:nth-child(4) { border-top: 4px solid #f9ab00; }
      .search-opportunity-card .metric strong { color: #153f32; }

      .portfolio-card.traffic-momentum-card {
        border-color: #c7dce7;
        background: linear-gradient(145deg, #ffffff 0%, #f4fafc 62%, #f1f8f5 100%);
        box-shadow: 0 16px 34px rgba(31, 91, 115, 0.10);
      }
      .traffic-momentum-card .client-titleline .tag {
        color: #15566f;
        background: #e2f2f7;
      }
      .traffic-momentum-card .performance-line {
        border-left: 5px solid #2387a5;
        background: linear-gradient(90deg, #e7f5f8 0%, #edf8f1 100%);
        color: #184c5c;
      }
      .traffic-momentum-card .metrics .metric:nth-child(1),
      .traffic-momentum-card .metrics .metric:nth-child(2) { border-top: 4px solid #2387a5; }
      .traffic-momentum-card .metrics .metric:nth-child(3) { border-top: 4px solid #34a853; }
      .traffic-momentum-card .metrics .metric:nth-child(4) { border-top: 4px solid #f9ab00; }

      .portfolio-card.quality-momentum-card {
        border-color: #d8ccef;
        background: linear-gradient(145deg, #ffffff 0%, #f8f5fd 62%, #f0f8f6 100%);
        box-shadow: 0 16px 34px rgba(88, 62, 133, 0.10);
      }
      .quality-momentum-card .client-titleline .tag {
        color: #56388b;
        background: #eee7fa;
      }
      .quality-momentum-card .performance-line {
        border-left: 5px solid #7652b8;
        background: linear-gradient(90deg, #f0eafb 0%, #eaf7f1 100%);
        color: #45316c;
      }
      .quality-momentum-card .metrics .metric:nth-child(1) { border-top: 4px solid #7652b8; }
      .quality-momentum-card .metrics .metric:nth-child(2) { border-top: 4px solid #34a853; }
      .quality-momentum-card .metrics .metric:nth-child(3) { border-top: 4px solid #4285f4; }
      .quality-momentum-card .metrics .metric:nth-child(4) { border-top: 4px solid #8da0ad; }

      .executive-brief {
        display: grid;
        gap: 18px;
      }
      .executive-lede {
        margin: 0;
        max-width: 1040px;
        color: #1d2e3c;
        font-size: 1.12rem;
        line-height: 1.65;
      }
      .executive-highlights {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
      }
      .executive-highlight {
        padding: 18px;
        border: 1px solid #d7e3e8;
        border-radius: 10px;
        background: #f8fbfc;
      }
      .executive-highlight strong {
        display: block;
        margin-bottom: 8px;
        color: #163f3c;
        font-size: 1rem;
      }
      .executive-highlight p {
        margin: 0;
        color: #52616b;
        line-height: 1.55;
      }
      .executive-priority {
        margin: 0;
        padding: 16px 18px;
        border-left: 5px solid #3eaaa2;
        border-radius: 8px;
        background: #eaf7f5;
        color: #174b47;
        line-height: 1.6;
      }
      @media (max-width: 800px) {
        .executive-highlights { grid-template-columns: 1fr; }
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
            <article class="card client-card portfolio-card search-opportunity-card" data-punch-child="punch-transfers">
              <div class="client-titleline">
                <div>
                  <h3>Punch Transfers</h3>
                  <p>Organic search visibility, high-performing content, and product discovery.</p>
                </div>
                <span class="tag">Organic visibility expanding</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>Search visibility is expanding. Page-level impressions increased from 1,730 to 3,150 over the last three months, while clicks remained close to the previous period at 31 versus 35.</p>
                <p>The duck-cloth guide is already a page-one asset at position 7.2, generating 12 clicks and 317 impressions. The DTF-by-size product page is also gaining traction: clicks increased from 1 to 4 and its average position improved from 39.0 to 25.0.</p>
              </div>
              <div class="performance-line"><strong>Google is showing Punch Transfers far more often: page-level search impressions increased 82%, with one guide already ranking on page one and the main DTF product page gaining 14 positions.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Punch Transfers performance metrics">
                  <div class="metric"><span>Page impressions</span><strong>3,150</strong><div class="change">+82.1% vs previous</div></div>
                  <div class="metric"><span>Top content position</span><strong>7.2</strong><div class="change">Page one</div></div>
                  <div class="metric"><span>DTF product clicks</span><strong>4</strong><div class="change">Up from 1</div></div>
                  <div class="metric"><span>DTF product position</span><strong>25.0</strong><div class="change">Improved from 39.0</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card" data-punch-child="chem-nut-supply">
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

            <article class="card client-card portfolio-card" data-punch-child="lc-mechanical">
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

            <article class="card client-card portfolio-card seo-growth-card" data-punch-child="phil-medeiros">
              <div class="client-titleline">
                <div>
                  <h3>Phil Medeiros</h3>
                  <p>SEO indexing, website traffic, and organic visibility.</p>
                </div>
                <span class="tag">Search visibility surge</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p><strong>Previous tactic:</strong> We submitted priority site pages for Google indexing and worked within Google’s 10-per-day submission limit to build a stronger searchable page base.</p>
                <p><strong>New update:</strong> Search Console shows a breakout quarter: 90 clicks and 7,380 impressions over the last three months, compared with 40 clicks and 428 impressions previously. Average position improved from 15.6 to 9.2, placing the site on page one on average.</p>
                <p>The lower 1.2% click-through rate reflects the site appearing for a much broader set of searches. The next opportunity is improving titles and descriptions so more of that new visibility becomes website traffic.</p>
              </div>
              <div class="performance-line"><strong>Phil Medeiros has substantially expanded organic visibility: clicks are up 125%, impressions are up 1,624%, and average search position improved by 6.4 positions.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Phil Medeiros performance metrics">
                  <div class="metric"><span>Organic clicks</span><strong>90</strong><div class="change">+125.0% vs previous</div></div>
                  <div class="metric"><span>Search impressions</span><strong>7,380</strong><div class="change">+1,624.3% vs previous</div></div>
                  <div class="metric"><span>Click-through rate</span><strong>1.2%</strong><div class="muted-change">9.3% previously</div></div>
                  <div class="metric"><span>Average position</span><strong>9.2</strong><div class="change">Improved from 15.6</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card traffic-momentum-card" data-punch-child="south-coast-towing">
              <div class="client-titleline">
                <div>
                  <h3>South Coast Towing</h3>
                  <p>Website audience growth, organic rankings, and conversion opportunities.</p>
                </div>
                <span class="tag">Traffic momentum</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>South Coast Towing’s website audience is growing. Sessions increased from 1,224 to 1,326, and active users increased from 870 to 995.</p>
                <p>Average search position improved from 12.5 to 11.3, putting important searches within reach of page one. The next focus is improving near-page-one pages, strengthening search titles, and making calls and quote requests easier to complete and measure.</p>
              </div>
              <div class="performance-line"><strong>Website momentum is positive: sessions increased 8.3%, active users increased 14.4%, and average search position improved to 11.3—just outside page one.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="South Coast Towing performance metrics">
                  <div class="metric"><span>Sessions</span><strong>1,326</strong><div class="change">+8.3% vs previous</div></div>
                  <div class="metric"><span>Active users</span><strong>995</strong><div class="change">+14.4% vs previous</div></div>
                  <div class="metric"><span>Average position</span><strong>11.3</strong><div class="change">Improved from 12.5</div></div>
                  <div class="metric"><span>Recorded key events</span><strong>1</strong><div class="muted-change">Tracking opportunity</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card quality-momentum-card" data-punch-child="tonys-auto">
              <div class="client-titleline">
                <div>
                  <h3>Tony's Auto</h3>
                  <p>Website engagement, organic rankings, and search-result performance.</p>
                </div>
                <span class="tag">Traffic quality improving</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>Tony’s Auto is attracting a more engaged website audience. Engagement rate increased from 42.0% to 55.3%, a gain of 13.3 percentage points.</p>
                <p>Organic search quality also improved: average position moved from 11.2 to 10.6 and click-through rate increased from 0.54% to 0.57%. Organic clicks held nearly steady at 26 versus 27 despite fewer impressions. The next focus is moving priority searches fully onto page one and strengthening calls and estimate requests.</p>
              </div>
              <div class="performance-line"><strong>Traffic quality is moving in the right direction: engagement improved 13.3 percentage points, average position reached 10.6, and organic CTR increased while clicks remained nearly steady.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Tony's Auto performance metrics">
                  <div class="metric"><span>Engagement rate</span><strong>55.3%</strong><div class="change">+13.3 pp vs previous</div></div>
                  <div class="metric"><span>Average position</span><strong>10.6</strong><div class="change">Improved from 11.2</div></div>
                  <div class="metric"><span>Organic CTR</span><strong>0.57%</strong><div class="change">Up from 0.54%</div></div>
                  <div class="metric"><span>Organic clicks</span><strong>26</strong><div class="muted-change">Nearly steady · 27 previously</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card" data-punch-child="punch-creatives">
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

            <article class="card client-card portfolio-card" data-punch-child="grub-tub-rentals">
              <div class="client-titleline">
                <div>
                  <h3>Grub Tub Boat Rentals</h3>
                  <p>Facebook Ads delivery, landing page activity, and GA4 recorded revenue.</p>
                </div>
                <span class="tag">Meta connected</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>Facebook Ads reporting is now connected for Grub Tub Boat Rentals. The account generated 50,835 impressions, 3,577 clicks, 2,234 link clicks, and 1,868 landing page views from August 8 through September 6, with $298.41 in spend.</p>
                <p>The supplied GA4 export records $4,642.84 in total revenue across all channels for August 8 through September 6, 2026. Paid Facebook and Instagram generated 1,956 sessions with $0 recorded revenue. GA4 attributes $1,873.91 to grubtubrentals.com / referral, so booking attribution needs review before drawing conclusions about ad-driven revenue.</p>
              </div>
              <div class="performance-line"><strong>GA4 recorded revenue: $4,642.84 across all channels, August 8–September 6, 2026. Revenue is from a supplied export; automated GA4 access is still pending.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Grub Tub Boat Rentals performance metrics">
                  <div class="metric"><span>Impressions</span><strong>50,835</strong><div class="change">Meta Ads connected</div></div>
                  <div class="metric"><span>Clicks</span><strong>3,577</strong><div class="change">7.04% CTR</div></div>
                  <div class="metric"><span>Landing views</span><strong>1,868</strong><div class="muted-change">Post-click traffic</div></div>
                  <div class="metric"><span>Spend</span><strong>$298.41</strong><div class="muted-change">$0.08 CPC</div></div>
                  <div class="metric"><span>GA4 recorded revenue</span><strong>$4,642.84</strong><div class="muted-change">All channels · USD</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card" data-punch-child="dr-mackenzie">
              <div class="client-titleline">
                <div>
                  <h3>Kathy Mackenzie</h3>
                  <p>Exit Plan campaign performance, store-click tracking, and conversion visibility.</p>
                </div>
                <span class="tag">Supplied update</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>The Exit Plan campaign is gaining reach and engagement. The latest supplied Google Ads update reports 19,855 impressions, 764 ad clicks, and a 3.85% click-through rate on a $7.50/day budget. Reported Google conversions remain at 0 because the current call to action sends visitors to third-party purchase destinations such as Amazon, Apple Books, and Kobo, where the purchase occurs outside grtevolve.com.</p>
                <p>The tracking fix is already in motion for the /book/ page. Each Buy button will be tracked as a generate_lead conversion event so Google Ads can optimize toward high-intent store clicks instead of only impressions and clicks.</p>
              </div>
              <div class="performance-line"><strong>Latest supplied figures: 19,855 impressions, 764 clicks, 3.85% CTR, $231.89 spend and 0 reported conversions. Exact dates were not supplied; these figures are excluded from the report’s August 8–September 6 totals.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Kathy Mackenzie performance metrics">
                  <div class="metric"><span>Impressions</span><strong>19,855</strong><div class="change">+350.6% vs previous week</div></div>
                  <div class="metric"><span>Ad clicks</span><strong>764</strong><div class="muted-change">Supplied update</div></div>
                  <div class="metric"><span>CTR</span><strong>3.85%</strong><div class="change">Strong engagement</div></div>
                  <div class="metric"><span>Spend</span><strong>$231.89</strong><div class="muted-change">$7.50/day budget</div></div>
                  <div class="metric"><span>Conversions</span><strong>0</strong><div class="risk-change">Store-click gap</div></div>
                </div>
              </div>
            </article>

            <article class="card client-card portfolio-card" data-punch-child="modern-auto-body">
              <div class="client-titleline">
                <div>
                  <h3>Modern Auto Body</h3>
                  <p>Facebook Instant Form lead generation and campaign performance.</p>
                </div>
                <span class="tag">Manual update</span>
              </div>
              <div class="client-update">
                <p class="section-label">Digital Marketing Update</p>
                <p>The supplied Meta Ads performance overview shows 5 Instant Form leads at $25.98 per lead, with $129.90 spent for the August 8–September 6 reporting window. These figures were updated manually from the supplied screenshot; automated Meta reporting access is pending. The next step is to follow up with these leads and track how many become estimates or booked repairs.</p>
              </div>
              <div class="performance-line"><strong>Facebook Instant Forms generated 5 leads at $25.98 per lead on $129.90 in spend.</strong></div>
              <div class="metric-group">
                <h4>Performance Metrics</h4>
                <div class="metrics" aria-label="Modern Auto Body performance metrics">
                  <div class="metric"><span>Instant Form leads</span><strong>5</strong><div class="muted-change">Meta reported</div></div>
                  <div class="metric"><span>Cost per lead</span><strong>$25.98</strong><div class="muted-change">Instant Forms</div></div>
                  <div class="metric"><span>Spend</span><strong>$129.90</strong><div class="muted-change">Aug 8–Sep 6</div></div>
                  <div class="metric"><span>Reporting</span><strong>Manual</strong><div class="muted-change">Supplied screenshot</div></div>
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
    if ".metric-group h4::after" not in content:
        metric_period_css = """
      .metric-group h4::after {
        content: "Source dates and comparisons noted in each card";
        display: block;
        margin-top: 3px;
        color: var(--muted);
        font-size: 11px;
        font-weight: 720;
        letter-spacing: 0;
        text-transform: none;
      }
"""
        content = replace_once(content, "</style>", metric_period_css + "\n    </style>")
    if ".dynamic-child-update" not in content:
        child_update_css = """
      .dynamic-child-update {
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid var(--line, #dce3ea);
      }
"""
        content = replace_once(content, "</style>", child_update_css + "\n    </style>")
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
    if "function addChildPostedUpdate" not in content:
        child_update_script = """
      function punchChildSlugFromText(text) {
        return String(text || "").match(/^\\[\\[punch_child:([a-z0-9-]+)\\]\\]\\s*/)?.[1] || "";
      }

      function stripPunchChildMarker(text) {
        return String(text || "").replace(/^\\[\\[punch_child:[a-z0-9-]+\\]\\]\\s*/, "");
      }

      function appendTextWithLinks(parent, text) {
        const pattern = /(https?:\\/\\/[^\\s]+)/g;
        String(text || "").split(pattern).forEach((part) => {
          if (!part) return;
          if (part.startsWith("http://") || part.startsWith("https://")) {
            const link = document.createElement("a");
            const canonical = part.replace("https://app.gohighlevel.com/v2/location/vO9C8YeZVrdf3NtNu3iZ/dashboard", "https://app.gohighlevel.com/v2/location/ZaraAYF0bT5SscGtjk8j/dashboard");
            link.href = canonical;
            link.textContent = canonical;
            link.rel = "noreferrer";
            link.target = "_blank";
            parent.append(link);
          } else {
            parent.append(document.createTextNode(part));
          }
        });
      }

      function renderFormattedUpdate(container, text) {
        const cleaned = stripPunchChildMarker(text);
        const lines = cleaned.split(/\\n+/).map((line) => line.trim()).filter(Boolean);
        let list = null;

        lines.forEach((line) => {
          const numbered = line.match(/^\\d+\\.\\s+(.+)/);
          const bulleted = line.match(/^[-*]\\s+(.+)/);
          if (numbered || bulleted) {
            if (!list || list.tagName !== (numbered ? "OL" : "UL")) {
              list = document.createElement(numbered ? "ol" : "ul");
              container.append(list);
            }
            const item = document.createElement("li");
            appendTextWithLinks(item, numbered ? numbered[1] : bulleted[1]);
            list.append(item);
            return;
          }

          list = null;
          const paragraph = document.createElement("p");
          appendTextWithLinks(paragraph, line);
          container.append(paragraph);
        });
      }

      function addChildPostedUpdate(childSlug, text) {
        if (childSlug === "phil-medeiros" || childSlug === "punch-transfers" || childSlug === "south-coast-towing" || childSlug === "tonys-auto") return;
        const card = document.querySelector(`[data-punch-child="${childSlug}"]`);
        const update = card?.querySelector(".client-update");
        if (!update) {
          addPostedUpdate(text);
          return;
        }
        update.querySelectorAll(":scope > :not(.section-label)").forEach((element) => element.remove());
        renderFormattedUpdate(update, text);
      }

"""
        content = replace_once(content, "      function addMeetingTakeaway", child_update_script + "      function addMeetingTakeaway")
        content = replace_once(
            content,
            """            if (entry.entry_type === "meeting_takeaway") {
              addMeetingTakeaway(entry.text, Boolean(entry.completed));
            } else {
              addPostedUpdate(entry.text);
            }""",
            """            if (entry.entry_type === "meeting_takeaway") {
              addMeetingTakeaway(entry.text, Boolean(entry.completed));
            } else if (punchChildSlugFromText(entry.text)) {
              addChildPostedUpdate(punchChildSlugFromText(entry.text), entry.text);
            } else if (entry.target_section === "digital_marketing_update" && entry.child_client_slug) {
              addChildPostedUpdate(entry.child_client_slug, entry.text);
            } else {
              addPostedUpdate(entry.text);
            }""",
        )
    if "function punchChildSlugFromText" not in content:
        marker_helpers = """
      function punchChildSlugFromText(text) {
        return String(text || "").match(/^\\[\\[punch_child:([a-z0-9-]+)\\]\\]\\s*/)?.[1] || "";
      }

      function stripPunchChildMarker(text) {
        return String(text || "").replace(/^\\[\\[punch_child:[a-z0-9-]+\\]\\]\\s*/, "");
      }

"""
        content = replace_once(content, "      function addChildPostedUpdate", marker_helpers + "      function addChildPostedUpdate")
    if "function renderFormattedUpdate" not in content:
        formatting_helpers = """
      function appendTextWithLinks(parent, text) {
        const pattern = /(https?:\\/\\/[^\\s]+)/g;
        String(text || "").split(pattern).forEach((part) => {
          if (!part) return;
          if (part.startsWith("http://") || part.startsWith("https://")) {
            const link = document.createElement("a");
            const canonical = part.replace("https://app.gohighlevel.com/v2/location/vO9C8YeZVrdf3NtNu3iZ/dashboard", "https://app.gohighlevel.com/v2/location/ZaraAYF0bT5SscGtjk8j/dashboard");
            link.href = canonical;
            link.textContent = canonical;
            link.rel = "noreferrer";
            link.target = "_blank";
            parent.append(link);
          } else {
            parent.append(document.createTextNode(part));
          }
        });
      }

      function renderFormattedUpdate(container, text) {
        const cleaned = stripPunchChildMarker(text);
        const lines = cleaned.split(/\\n+/).map((line) => line.trim()).filter(Boolean);
        let list = null;

        lines.forEach((line) => {
          const numbered = line.match(/^\\d+\\.\\s+(.+)/);
          const bulleted = line.match(/^[-*]\\s+(.+)/);
          if (numbered || bulleted) {
            if (!list || list.tagName !== (numbered ? "OL" : "UL")) {
              list = document.createElement(numbered ? "ol" : "ul");
              container.append(list);
            }
            const item = document.createElement("li");
            appendTextWithLinks(item, numbered ? numbered[1] : bulleted[1]);
            list.append(item);
            return;
          }

          list = null;
          const paragraph = document.createElement("p");
          appendTextWithLinks(paragraph, line);
          container.append(paragraph);
        });
      }

"""
        content = replace_once(content, "      function addChildPostedUpdate", formatting_helpers + "      function addChildPostedUpdate")
    content = replace_optional(
        content,
        """        const paragraph = document.createElement("p");
        paragraph.textContent = stripPunchChildMarker(text);
        article.append(paragraph);""",
        """        renderFormattedUpdate(article, text);""",
    )
    content = replace_optional(
        content,
        """        const paragraph = document.createElement("p");
        paragraph.textContent = text || "";
        article.append(paragraph);""",
        """        renderFormattedUpdate(article, text);""",
    )
    content = replace_optional(content, "paragraph.textContent = text || \"\";\n        update.append(paragraph);", "paragraph.textContent = stripPunchChildMarker(text);\n        if (!paragraph.parentElement) update.append(paragraph);")
    content = replace_optional(
        content,
        """        const paragraph = document.createElement("p");
        paragraph.className = "dynamic-child-update";
        paragraph.textContent = stripPunchChildMarker(text);
        update.append(paragraph);""",
        """        const paragraph = update.querySelector("p:not(.section-label)") || document.createElement("p");
        paragraph.textContent = stripPunchChildMarker(text);
        if (!paragraph.parentElement) update.append(paragraph);""",
    )
    content = replace_optional(
        content,
        """        const paragraph = update.querySelector("p:not(.section-label)") || document.createElement("p");
        paragraph.textContent = stripPunchChildMarker(text);
        if (!paragraph.parentElement) update.append(paragraph);""",
        """        update.querySelectorAll(":scope > :not(.section-label)").forEach((element) => element.remove());
        renderFormattedUpdate(update, text);""",
    )
    content = replace_optional(
        content,
        """            if (entry.entry_type === "meeting_takeaway") {
              addMeetingTakeaway(entry.text, Boolean(entry.completed));
            } else if (entry.target_section === "digital_marketing_update" && entry.child_client_slug) {
              addChildPostedUpdate(entry.child_client_slug, entry.text);
            } else {
              addPostedUpdate(entry.text);
            }""",
        """            if (entry.entry_type === "meeting_takeaway") {
              addMeetingTakeaway(entry.text, Boolean(entry.completed));
            } else if (punchChildSlugFromText(entry.text)) {
              addChildPostedUpdate(punchChildSlugFromText(entry.text), entry.text);
            } else if (entry.target_section === "digital_marketing_update" && entry.child_client_slug) {
              addChildPostedUpdate(entry.child_client_slug, entry.text);
            } else {
              addPostedUpdate(entry.text);
            }""",
    )

    if "portfolio-stack" not in content:
        content = replace_once(content, "</style>", portfolio_css() + "\n    </style>")
    if ".posted-update ul" not in content:
        posted_update_css = """
      .posted-update ul,
      .posted-update ol {
        margin: 0;
        padding-left: 22px;
        line-height: 1.55;
      }

      .posted-update li + li {
        margin-top: 4px;
      }

      .posted-update a {
        color: #1d5f9f;
        overflow-wrap: anywhere;
      }
"""
        content = replace_once(content, "</style>", posted_update_css + "\n    </style>")
    if ".client-update ul" not in content:
        formatted_update_css = """
      .client-update ul,
      .client-update ol {
        margin: 0;
        padding-left: 22px;
        color: #263240;
        font-size: 15px;
        line-height: 1.55;
      }

      .client-update li + li {
        margin-top: 4px;
      }

      .client-update a {
        color: #1d5f9f;
        overflow-wrap: anywhere;
      }
"""
        content = replace_once(content, "</style>", formatted_update_css + "\n    </style>")
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
    content = replace_optional(
        content,
        '''        <section id="posted-updates-section" class="card wide-card" hidden>
          <h2>Current Updates</h2>
          <div id="posted-updates" class="posted-updates"></div>
          <ul id="dynamic-takeaways" class="dynamic-takeaways"></ul>
        </section>''',
        '''        <section id="posted-updates-section" class="card wide-card">
          <h2>Current Updates</h2>
          <p>No pending updates need attention at this time.</p>
          <div id="posted-updates" class="posted-updates" hidden></div>
          <ul id="dynamic-takeaways" class="dynamic-takeaways" hidden></ul>
        </section>''',
    )
    content = re.sub(r"(?m)^[ \t]+$", "", content)
    return content


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    content = apply_analytics(enhance_punch_club(inject_public_updates(fetch("/punch-club"))))
    OUT.write_text(content, encoding="utf-8")
    print(f"Wrote Punch Club report to {OUT}")


if __name__ == "__main__":
    main()
