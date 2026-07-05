from __future__ import annotations

import html
import re
import urllib.request
from pathlib import Path

from public_update_renderer import add_posted_update_js, public_update_css, public_update_js_helpers


BASE_URL = "https://clients.stott.marketing"
OUT = Path("firebase-static/public")


GA4 = {
    "active_users": "1,004",
    "active_users_change": "-17.7% vs previous",
    "sessions": "902",
    "new_users": "787",
    "engagement": "59.1%",
    "engagement_previous": "57.6%",
    "key_events": "276",
    "key_events_change": "-17.4% vs previous",
    "revenue": "$3.7k",
    "revenue_full": "$3,730",
    "revenue_change": "-45.1% vs previous",
}

ADS = {
    "spend": "$1,610.89",
    "impressions": "9,362",
    "clicks": "421",
    "conversions": "56",
    "avg_cpc": "$3.83",
    "cost_per_conversion": "$28.77",
    "conversion_change": "+30.2% vs previous",
    "cpa_change": "-28.9% vs previous",
}

SEARCH = {
    "clicks": "125",
    "clicks_change": "-26.9%",
    "impressions": "20,218",
    "impressions_change": "-16.6%",
    "ctr": "0.62%",
    "ctr_change": "-12.4%",
    "position": "15.3",
}

META = {
    "spend": "$598.37",
    "impressions": "15,654",
    "reach": "6,267",
    "clicks": "423",
    "cpc": "$1.41",
    "ctr": "2.70%",
    "leads": "28",
    "link_clicks": "168",
    "video_views": "3,851",
    "period": "2026-05-27 to 2026-06-25",
}

GHL = {
    "total_opportunities": "1,326",
    "open": "1,307",
    "won": "13",
    "abandoned": "6",
    "facebook_pipeline": "618",
    "appointment_pipeline": "413",
    "contact_form_pipeline": "290",
    "facebook_follow_up": "385",
    "facebook_showed": "116",
    "facebook_booked": "38",
}

ROAS = {
    "meta_revenue": "$3,012.53",
    "meta_roas": "0.84x",
    "google_revenue": "$64,712.46",
    "google_roas": "7.35x",
    "entity_leads": "31",
    "entity_matched": "10",
    "entity_buyers": "6",
    "entity_revenue": "$11,856.04",
    "entity_spend": "$3,720",
    "entity_roas": "3.19x",
}

SEARCH_ATLAS = {
    "site_health": "91",
    "domain_power": "11",
    "domain_rating": "3",
    "domain_authority": "8",
    "organic_traffic": "196",
    "keyword_count": "148",
    "keyword_change": "-1",
    "keyword_change_percent": "-0.7%",
    "top_3_keywords": "6",
    "refdomain_count": "116",
    "new_refdomains": "0",
    "lost_refdomains": "0",
    "backlinks": "214",
    "spam_score": "1",
    "otto_score": "54",
    "otto_fixes": "684",
    "otto_time_saved": "17 days, 3 hours, 20 minutes",
    "llm_current_mentions": "452",
    "llm_previous_mentions": "270",
    "summary": "Technical issues detected with 1.3K OTTO findings despite stable traffic. Fix technical SEO issues using OTTO.",
}


def fetch(path: str) -> str:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=30) as response:
        body = response.read().decode("utf-8")
    if not body.lower().lstrip().startswith("<!doctype"):
        body = "<!doctype html>\n" + body
    return body


def write_page(path: str, content: str) -> None:
    target = OUT / path.strip("/") / "index.html" if path != "/" else OUT / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(content: str, old: str, new: str) -> str:
    if old not in content:
        raise RuntimeError(f"Expected content not found: {old[:90]}")
    return content.replace(old, new, 1)


def replace_optional(content: str, old: str, new: str) -> str:
    return content.replace(old, new, 1) if old in content else content


def replace_section(content: str, start: str, end: str, replacement: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    updated, count = pattern.subn(replacement, content, count=1)
    if count != 1:
        raise RuntimeError(f"Expected exactly one section from {start!r} to {end!r}; found {count}")
    return updated


def replace_platform_card(content: str, heading: str, replacement: str) -> str:
    pattern = re.compile(
        r'<article class="platform">\s*'
        r'<div class="platform-head"><div><h3>'
        + re.escape(heading)
        + r'</h3>.*?</article>',
        re.S,
    )
    updated, count = pattern.subn(replacement, content, count=1)
    if count != 1:
        raise RuntimeError(f"Expected one platform card for {heading!r}; found {count}")
    return updated


def replace_card_body(content: str, heading: str, replacement_inner: str) -> str:
    pattern = re.compile(
        r'(<section class="card">\s*<h2>'
        + re.escape(heading)
        + r'</h2>\s*).*?(</section>)',
        re.S,
    )
    updated, count = pattern.subn(r"\1" + replacement_inner + r"\2", content, count=1)
    if count != 1:
        raise RuntimeError(f"Expected one card for {heading!r}; found {count}")
    return updated


def inject_public_updates(content: str, client_slug: str) -> str:
    if "clientPublicUpdates" in content:
        return content

    styles = public_update_css(text_color="inherit")
    section = """
        <section id="posted-updates-section" class="card wide-card" hidden>
          <h2>Current Updates</h2>
          <div id="posted-updates" class="posted-updates"></div>
          <ul id="dynamic-takeaways" class="dynamic-takeaways"></ul>
        </section>
"""
    script = f"""
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

{public_update_js_helpers()}
{add_posted_update_js(show_section_call='document.querySelector("#posted-updates-section").hidden = false;')}

      function addMeetingTakeaway(text, completed) {{
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
      }}

      async function loadPostedUpdates() {{
        try {{
          const snapshot = await getDocs(query(
            collection(db, "clientPublicUpdates", "{client_slug}", "items"),
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
"""
    content = replace_once(content, "</style>", styles + "\n    </style>")
    content = replace_once(content, "      </main>", section + "\n      </main>")
    content = replace_once(content, "  </body>", script + "\n  </body>")
    return content


def update_sjawc(content: str) -> str:
    content = replace_optional(
        content,
        '<div class="metric"><span>Active users</span><strong>992</strong><small class="down">-22.3% vs previous</small></div>',
        f'<div class="metric"><span>Active users</span><strong>{GA4["active_users"]}</strong><small class="down">{GA4["active_users_change"]}</small></div>',
    )
    content = replace_optional(
        content,
        '<div class="metric"><span>Key events</span><strong>274</strong><small class="down">-19.4% vs previous</small></div>',
        f'<div class="metric"><span>Key events</span><strong>{GA4["key_events"]}</strong><small class="down">{GA4["key_events_change"]}</small></div>',
    )
    content = replace_optional(
        content,
        '<div class="metric"><span>Engagement</span><strong>60.7%</strong><small class="up">Improved from 56.7%</small></div>',
        f'<div class="metric"><span>Engagement</span><strong>{GA4["engagement"]}</strong><small class="up">Improved from {GA4["engagement_previous"]}</small></div>',
    )
    content = replace_optional(
        content,
        '<div class="metric"><span>Tracked revenue</span><strong>$4.8k</strong><small class="down">-9.5% vs previous</small></div>',
        f'<div class="metric"><span>Tracked revenue</span><strong>{GA4["revenue"]}</strong><small class="down">{GA4["revenue_change"]}</small></div>',
    )

    old_summary = (
        "St. Johns Aesthetics now has verified GA4 performance available for the last 30 complete days. "
        "The website generated 992 active users, 882 sessions, 274 key events, and $4,795 in tracked revenue. "
        "Traffic and tracked outcomes are below the previous 30-day period, but engagement improved from 56.7% to 60.7%, "
        "indicating that the audience reaching the site is interacting more deeply."
    )
    new_summary = (
        "St. Johns Aesthetics now has verified GA4, Google Ads, Meta Ads, and Search Console performance available. "
        f"The website generated {GA4['active_users']} active users, {GA4['sessions']} sessions, "
        f"{GA4['key_events']} key events, and {GA4['revenue_full']} in tracked revenue over the last 30 complete days. "
        f"Google Ads delivered {ADS['impressions']} impressions, {ADS['clicks']} clicks, and {ADS['conversions']} conversions "
        f"at a {ADS['cost_per_conversion']} cost per conversion. Meta Ads added {META['leads']} leads from "
        f"{META['spend']} in spend. Organic search remains an area to watch: Search Console shows "
        f"{SEARCH['clicks']} clicks from {SEARCH['impressions']} impressions, with CTR down 12.4%."
    )
    content = replace_optional(content, html.escape(old_summary), html.escape(new_summary))
    current_summary = (
        "St. Johns Aesthetics now has verified GA4, Google Ads, and Search Console performance available. "
        f"The website generated {GA4['active_users']} active users, {GA4['sessions']} sessions, "
        f"{GA4['key_events']} key events, and {GA4['revenue_full']} in tracked revenue over the last 30 complete days. "
        f"Google Ads delivered {ADS['impressions']} impressions, {ADS['clicks']} clicks, and {ADS['conversions']} conversions "
        f"at a {ADS['cost_per_conversion']} cost per conversion. Organic search remains an area to watch: Search Console shows "
        f"{SEARCH['clicks']} clicks from {SEARCH['impressions']} impressions, with CTR down 12.4%."
    )
    content = replace_optional(content, html.escape(current_summary), html.escape(new_summary))

    old_ga4 = """<article class="platform">
              <div class="platform-head"><div><h3>Google Analytics 4</h3><p>Website behavior and tracked outcomes.</p></div><span class="tag">Live</span></div>
              <ul>
                <li>882 sessions and 777 new users</li>
                <li>60.7% engagement rate</li>
                <li>274 tracked key events</li>
                <li>$4,795 tracked revenue</li>
              </ul>
            </article>"""
    new_ga4 = f"""<article class="platform">
              <div class="platform-head"><div><h3>Google Analytics 4</h3><p>Website behavior and tracked outcomes.</p></div><span class="tag">Live</span></div>
              <ul>
                <li>{GA4['sessions']} sessions and {GA4['new_users']} new users</li>
                <li>{GA4['engagement']} engagement rate</li>
                <li>{GA4['key_events']} tracked key events</li>
                <li>{GA4['revenue_full']} tracked revenue</li>
              </ul>
            </article>"""
    content = replace_optional(content, old_ga4, new_ga4)

    old_ads = """<article class="platform">
              <div class="platform-head"><div><h3>Google Ads</h3><p>Search and paid campaign delivery.</p></div><span class="tag blocked">Approval blocked</span></div>
              <ul>
                <li>Account access requested</li>
                <li>Google requires multi-party approval</li>
                <li>No St. Johns customer ID is visible yet</li>
                <li>Ads metrics will populate after approval</li>
              </ul>
            </article>"""
    new_ads = f"""<article class="platform">
              <div class="platform-head"><div><h3>Google Ads</h3><p>Search and paid campaign delivery.</p></div><span class="tag">Live</span></div>
              <ul>
                <li>{ADS['spend']} spend with {ADS['impressions']} impressions</li>
                <li>{ADS['clicks']} clicks at {ADS['avg_cpc']} average CPC</li>
                <li>{ADS['conversions']} conversions, {ADS['conversion_change']}</li>
                <li>{ADS['cost_per_conversion']} cost per conversion, {ADS['cpa_change']}</li>
              </ul>
            </article>"""
    content = replace_optional(content, old_ads, new_ads)

    old_meta = """<article class="platform">
              <div class="platform-head"><div><h3>Facebook & Instagram Ads</h3><p>Paid social awareness and lead generation.</p></div><span class="tag pending">Connect</span></div>
              <ul>
                <li>Spend, reach, impressions, and frequency</li>
                <li>Link clicks and landing-page views</li>
                <li>Leads and cost per lead</li>
                <li>Campaign and creative performance</li>
              </ul>
            </article>"""
    new_meta = f"""<article class="platform">
              <div class="platform-head"><div><h3>Facebook &amp; Instagram Ads</h3><p>Paid social awareness and lead generation.</p></div><span class="tag">Live</span></div>
              <ul>
                <li>{META['spend']} spend with {META['impressions']} impressions</li>
                <li>{META['reach']} reach and {META['clicks']} clicks</li>
                <li>{META['leads']} leads and {META['link_clicks']} link clicks</li>
                <li>{META['video_views']} video views; {META['ctr']} CTR</li>
              </ul>
            </article>"""
    content = replace_optional(content, old_meta, new_meta)

    old_search = """<article class="platform">
              <div class="platform-head"><div><h3>Google Search Console</h3><p>Organic visibility and search demand.</p></div><span class="tag">Live</span></div>
              <ul>
                <li>127 organic clicks, down 29.8%</li>
                <li>20,066 search impressions, down 18.4%</li>
                <li>0.63% CTR, down 14.0%</li>
                <li>Average position 15.1, down about one position</li>
              </ul>
            </article>"""
    new_search = f"""<article class="platform">
              <div class="platform-head"><div><h3>Google Search Console</h3><p>Organic visibility and search demand.</p></div><span class="tag">Live</span></div>
              <ul>
                <li>{SEARCH['clicks']} organic clicks, {SEARCH['clicks_change']} vs previous</li>
                <li>{SEARCH['impressions']} search impressions, {SEARCH['impressions_change']} vs previous</li>
                <li>{SEARCH['ctr']} CTR, {SEARCH['ctr_change']} vs previous</li>
                <li>Average position {SEARCH['position']}, down about one position</li>
              </ul>
            </article>"""
    content = replace_optional(content, old_search, new_search)

    old_plan = (
        "The immediate digital opportunity is recovery: engagement quality improved, but website traffic, tracked outcomes, "
        "organic visibility, and organic click-through declined. Once paid media and CRM data are connected, this page will "
        "report the full marketing path: total spend → website visits → leads → appointments → show rate → booked revenue."
    )
    new_plan = (
        f"The immediate digital opportunity is efficiency and attribution clarity: paid search conversion volume is up while cost per conversion is down, "
        f"and Meta Ads is now reporting lead volume. Website traffic, tracked revenue, and organic click-through are still below the previous period. "
        f"The next reporting focus is connecting lead and appointment outcomes so spend, website visits, leads, appointments, and booked revenue can be reviewed together."
    )
    content = replace_optional(content, html.escape(old_plan), html.escape(new_plan))
    current_plan = (
        f"The immediate digital opportunity is efficiency: paid search conversion volume is up while cost per conversion is down, "
        f"but website traffic, tracked revenue, and organic click-through are still below the previous period. The next reporting focus "
        f"is connecting lead and appointment outcomes so spend, website visits, leads, appointments, and booked revenue can be reviewed together."
    )
    content = replace_optional(content, html.escape(current_plan), html.escape(new_plan))

    old_actions = """<li>Complete Google's multi-party approval for the St. Johns Google Ads account when the second approver is available.</li>
            <li>Review declining organic queries and landing pages to identify ranking and click-through recovery opportunities.</li>
            <li>Connect the Meta ad account using a read-only Marketing API credential.</li>"""
    new_actions = """<li>Review the Google Ads campaigns driving the 56 reported conversions and confirm which conversion actions represent qualified leads.</li>
            <li>Review declining organic queries and landing pages to identify ranking and click-through recovery opportunities.</li>
            <li>Review Meta lead quality against booked appointments so reported lead volume can be tied to actual patient outcomes.</li>"""
    content = replace_optional(content, old_actions, new_actions)
    content = replace_optional(
        content,
        "<li>Connect the Meta ad account using a read-only Marketing API credential.</li>",
        "<li>Review Meta lead quality against booked appointments so reported lead volume can be tied to actual patient outcomes.</li>",
    )

    summary = (
        "<p>St. Johns Aesthetics now has verified GA4, Google Ads, Meta Ads, GoHighLevel, Search Console, Search Atlas, "
        "and YTD Boulevard revenue matching available. "
        f"The website generated {GA4['active_users']} active users, {GA4['sessions']} sessions, "
        f"{GA4['key_events']} key events, and {GA4['revenue_full']} in tracked revenue over the last 30 complete days. "
        f"Google Ads delivered {ADS['impressions']} impressions, {ADS['clicks']} clicks, and {ADS['conversions']} conversions "
        f"at a {ADS['cost_per_conversion']} cost per conversion. Meta Ads added {META['leads']} leads from {META['spend']} in spend. "
        f"GoHighLevel shows {GHL['total_opportunities']} total opportunities, including {GHL['facebook_pipeline']} Facebook pipeline opportunities. "
        f"Search Atlas shows site health at {SEARCH_ATLAS['site_health']}, {SEARCH_ATLAS['keyword_count']} tracked organic keywords, "
        f"{SEARCH_ATLAS['refdomain_count']} referring domains, and an OTTO optimization score of {SEARCH_ATLAS['otto_score']}. "
        f"The YTD revenue-match workbook shows Google Ads as the strongest confirmed revenue channel at {ROAS['google_roas']} ROAS, "
        f"EntityMed as positive at {ROAS['entity_roas']} ROAS, and Meta still below breakeven at {ROAS['meta_roas']} ROAS.</p>"
        '<div class="status-row"><span class="dot"></span><span>Connected performance data is presented from the most recently verified reporting period. Revenue attribution uses aggregate Boulevard revenue matching and excludes individual client details.</span></div>'
    )
    content = replace_card_body(content, "Executive Summary", summary)

    google_ads_card = f"""<article class="platform">
              <div class="platform-head"><div><h3>Google Ads</h3><p>Search and paid campaign delivery.</p></div><span class="tag">Live</span></div>
              <ul>
                <li>{ADS['spend']} spend with {ADS['impressions']} impressions</li>
                <li>{ADS['clicks']} clicks at {ADS['avg_cpc']} average CPC</li>
                <li>{ADS['conversions']} conversions, {ADS['conversion_change']}</li>
                <li>{ROAS['google_revenue']} YTD matched revenue; {ROAS['google_roas']} ROAS</li>
              </ul>
            </article>"""
    content = replace_platform_card(content, "Google Ads", google_ads_card)

    meta_card = f"""<article class="platform">
              <div class="platform-head"><div><h3>Facebook &amp; Instagram Ads</h3><p>Paid social awareness and lead generation.</p></div><span class="tag">Live</span></div>
              <ul>
                <li>{META['spend']} spend with {META['impressions']} impressions</li>
                <li>{META['reach']} reach and {META['clicks']} clicks</li>
                <li>{META['leads']} leads and {META['link_clicks']} link clicks</li>
                <li>{ROAS['meta_revenue']} YTD matched revenue; {ROAS['meta_roas']} ROAS</li>
              </ul>
            </article>"""
    content = replace_platform_card(content, "Facebook &amp; Instagram Ads", meta_card)

    ghl_card = f"""<article class="platform">
              <div class="platform-head"><div><h3>GoHighLevel</h3><p>Lead, appointment, and pipeline outcomes.</p></div><span class="tag">Live</span></div>
              <ul>
                <li>{GHL['total_opportunities']} total opportunities; {GHL['open']} open</li>
                <li>{GHL['facebook_pipeline']} Facebook form opportunities</li>
                <li>{GHL['appointment_pipeline']} appointment pipeline records</li>
                <li>{GHL['facebook_showed']} showed and {GHL['facebook_booked']} booked in Facebook pipeline</li>
              </ul>
            </article>"""
    content = replace_platform_card(content, "GoHighLevel", ghl_card)

    entity_card = f"""<article class="platform">
              <div class="platform-head"><div><h3>EntityMed</h3><p>Aggregate appointment and revenue outcomes.</p></div><span class="tag">Revenue matched</span></div>
              <ul>
                <li>{ROAS['entity_leads']} EntityMed leads; {ROAS['entity_matched']} matched contacts</li>
                <li>{ROAS['entity_buyers']} purchasing clients</li>
                <li>{ROAS['entity_revenue']} confirmed Boulevard revenue</li>
                <li>{ROAS['entity_roas']} ROAS against {ROAS['entity_spend']} estimated spend</li>
              </ul>
            </article>"""
    content = replace_platform_card(content, "EntityMed", entity_card)

    search_atlas_card = f"""<article class="platform">
              <div class="platform-head"><div><h3>Search Atlas</h3><p>SEO health, authority, backlinks, and OTTO findings.</p></div><span class="tag">Live</span></div>
              <ul>
                <li>Site health {SEARCH_ATLAS['site_health']}; OTTO score {SEARCH_ATLAS['otto_score']}</li>
                <li>{SEARCH_ATLAS['keyword_count']} keywords; {SEARCH_ATLAS['top_3_keywords']} in top 3 positions</li>
                <li>{SEARCH_ATLAS['refdomain_count']} referring domains and {SEARCH_ATLAS['backlinks']} backlinks</li>
                <li>{SEARCH_ATLAS['llm_current_mentions']} LLM mentions, up from {SEARCH_ATLAS['llm_previous_mentions']}</li>
              </ul>
            </article>"""
    if "<h3>Search Atlas</h3>" in content:
        content = replace_platform_card(content, "Search Atlas", search_atlas_card)
    else:
        content = replace_once(content, new_search, new_search + "\n            " + search_atlas_card)

    plan = (
        '<div class="callout">The immediate digital opportunity is attribution clarity: Google Ads is producing the strongest confirmed revenue return in the YTD match, '
        'EntityMed is profitable on matched revenue, and Meta is generating lead volume but needs lead-quality and appointment conversion review. '
        f"Search Atlas adds an SEO operations layer: {SEARCH_ATLAS['summary']} "
        'The next reporting focus is tying GoHighLevel pipeline stages to booked and completed appointments so spend, leads, appointments, Boulevard revenue, and organic visibility can be reviewed together.</div>'
    )
    content = replace_card_body(content, "Executive Measurement Plan", plan)

    actions = """<ul class="next">
            <li>Review the Google Ads campaigns driving the 56 reported conversions and confirm which conversion actions represent qualified leads.</li>
            <li>Map GoHighLevel Facebook pipeline outcomes to Boulevard booked revenue so lead volume can be judged by patient value.</li>
            <li>Review Meta lead quality against booked appointments so reported lead volume can be tied to actual patient outcomes.</li>
            <li>Use Search Console and Search Atlas together to review declining organic queries, technical SEO findings, and landing-page recovery opportunities.</li>
            <li>Continue using aggregate EntityMed revenue matching unless a privacy-safe API/export becomes available.</li>
          </ul>"""
    content = replace_card_body(content, "Next Connection Actions", actions)

    return content


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = {
        "/": fetch("/"),
    }
    for path, content in pages.items():
        write_page(path, content)

    print(f"Wrote {len(pages)} pages to {OUT}")


if __name__ == "__main__":
    main()
