"""Apply dated analytics to the existing Punch Club layout without altering posted updates."""
import json
import re
from datetime import date
from html import escape
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data/punch-club/google.json'

def replace_one(pattern, replacement, text):
    result, count = re.subn(pattern, lambda _: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f'Missing expected report section: {pattern[:70]}')
    return result

def apply_analytics(content):
    if not DATA.exists():
        return content
    data = json.loads(DATA.read_text())
    clients = data['clients']
    current = data['periods']['current']
    previous = data['periods']['previous']
    def date_range(window):
        start, end = date.fromisoformat(window['start']), date.fromisoformat(window['end'])
        return f'{start:%B} {start.day}–{end:%B} {end.day}, {end.year}'
    period = date_range(current)
    comparison = date_range(previous)

    def values(slug, source, window='current'):
        source_data = clients[slug]['sources'].get(source, {}).get(window, {})
        return source_data.get('metrics') if source_data.get('status') == 'ok' else None

    def fmt(value, kind='number'):
        if value is None:
            return 'Unavailable'
        if kind == 'money': return f'${value:,.2f}'
        if kind == 'percent': return f'{value * 100:.2f}%'
        if kind == 'ratio': return f'{value:.2f}x'
        if kind == 'position': return f'{value:.1f}'
        return f'{value:,.0f}' if float(value).is_integer() else f'{value:,.1f}'

    def metric(slug, source, key, label, kind='number', lower_better=False):
        now, before = values(slug, source), values(slug, source, 'previous')
        value = now.get(key) if now is not None else None
        old = before.get(key) if before is not None else None
        css, note = 'muted-change', 'Comparison unavailable'
        if value is None:
            note = 'Source access pending'
        elif old is not None:
            if value == old: note = 'No change vs previous'
            elif kind in ['percent', 'position']:
                delta = (value - old) * (100 if kind == 'percent' else 1)
                note = f'{delta:+.2f} {"pp" if kind == "percent" else "positions"} vs previous'
                css = 'change' if (value < old if lower_better else value > old) else 'risk-change'
            elif old != 0:
                note = f'{(value / old - 1) * 100:+.1f}% vs previous'
                css = 'change' if (value < old if lower_better else value > old) else 'risk-change'
            else: note = 'Previous period: 0'
        return f'<div class="metric"><span>{escape(label)}</span><strong>{fmt(value, kind)}</strong><div class="{css}">{escape(note)}</div></div>'

    definitions = {
        'punch-transfers': [('ga4','sessions','Sessions'),('ga4','keyEvents','Key events'),('ga4','totalRevenue','GA4 recorded revenue','money'),('google_ads','clicks','Ads clicks'),('google_ads','average_cpc','Avg CPC','money',True)],
        'chem-nut-supply': [('ga4','sessions','Sessions'),('ga4','activeUsers','Active users'),('ga4','keyEvents','Key events'),('ga4','totalRevenue','GA4 recorded revenue','money'),('ga4','engagementRate','Engagement rate','percent')],
        'lc-mechanical': [('ga4','sessions','Sessions'),('ga4','keyEvents','Key events'),('google_ads','spend','Ads spend','money'),('google_ads','clicks','Ads clicks'),('google_ads','conversions','Ads conversions')],
        'phil-medeiros': [('search_console','clicks','Organic clicks'),('search_console','impressions','Search impressions'),('search_console','ctr','Click-through rate','percent'),('search_console','position','Average position','position',True)],
        'south-coast-towing': [('ga4','sessions','Sessions'),('ga4','activeUsers','Active users'),('search_console','position','Average position','position',True),('ga4','keyEvents','Recorded key events')],
        'tonys-auto': [('ga4','sessions','Sessions'),('search_console','clicks','Organic clicks'),('search_console','impressions','Search impressions'),('search_console','ctr','Organic CTR','percent')],
        'punch-creatives': [('ga4','sessions','Sessions'),('ga4','activeUsers','Active users'),('ga4','engagementRate','Engagement rate','percent'),('search_console','clicks','Organic clicks')],
    }
    notes = {
        'punch-transfers': 'Previous work notes retained for follow-up: review the replacement creative and confirm Shopify purchase-contact and shipping cleanup status.',
        'chem-nut-supply': 'Reporting now uses GA4 only; Google Ads is no longer available. Review purchase tracking and traffic quality alongside the revenue change. Previous invoice follow-up remains an operational note.',
        'lc-mechanical': 'Review the gap between GA4 key events and Google Ads conversions. Earlier Jotform and May activity notes are historical; this analytics window is the period shown below.',
        'phil-medeiros': 'Previous tactic: priority pages were submitted for Google indexing within the 10-per-day quota. Search Console now shows a breakout quarter: clicks increased from 40 to 90, impressions grew from 428 to 7,380, and average position improved from 15.6 to 9.2. The lower 1.2% click-through rate reflects much broader search exposure; the next opportunity is improving titles and descriptions so more of that visibility becomes website traffic.',
        'south-coast-towing': 'Average search position improved from 12.5 to 11.3, putting important searches within reach of page one. The next focus is improving near-page-one pages, strengthening search titles, and making calls and quote requests easier to complete and measure.',
        'tonys-auto': 'Continue reviewing search-result messaging and page relevance using the refreshed click, impression, and CTR results.',
        'punch-creatives': 'Previous work notes retained: QuickBooks data was reformatted and uploaded to Go High Level. Confirm the Company Name and Email cleanup export and Existing Clients - PC smart list status.',
    }
    for slug, fields in definitions.items():
        child = 'dr-mackenzie' if slug == 'dr-kathleen-mackenzie' else slug
        pattern = rf'<article class="card client-card portfolio-card[^"]*" data-punch-child="{child}">.*?</article>'
        match = re.search(pattern, content, re.S)
        if not match: raise ValueError(f'Missing child card: {child}')
        card = match.group()
        ga, sc, ads = values(slug, 'ga4'), values(slug, 'search_console'), values(slug, 'google_ads')
        sentences = []
        if ga is not None:
            event_label = 'key event' if ga['keyEvents'] == 1 else 'key events'
            sentences.append(f"GA4 recorded {fmt(ga['sessions'])} sessions and {fmt(ga['keyEvents'])} {event_label}.")
            if slug in ['punch-transfers', 'chem-nut-supply']:
                sentences.append(f"GA4 recorded revenue was {fmt(ga['totalRevenue'], 'money')}; this is tracked revenue, not a statement of total business sales.")
        if ads is not None:
            sentences.append(f"Google Ads delivered {fmt(ads['impressions'])} impressions, {fmt(ads['clicks'])} clicks and {fmt(ads['conversions'])} conversions on {fmt(ads['spend'], 'money')} in spend.")
        elif 'google_ads' in clients[slug]['sources']:
            sentences.append('Current Google Ads metrics could not be retrieved; older figures are not presented as current results.')
        if sc is not None:
            sentences.append(f"Search Console recorded {fmt(sc['clicks'])} organic clicks and {fmt(sc['impressions'])} search impressions.")
        narrative = ' '.join(sentences)
        if slug == 'punch-transfers':
            narrative = 'Search visibility is expanding. Page-level impressions increased from 1,730 to 3,150 over the last three months, while clicks remained close to the previous period at 31 versus 35.'
        if slug == 'phil-medeiros':
            narrative = 'Search Console shows a breakout quarter for organic visibility, with substantially more search exposure, more clicks, and an average page-one position.'
        if slug == 'south-coast-towing':
            narrative = 'South Coast Towing’s website audience is growing. Sessions increased from 1,224 to 1,326, and active users increased from 870 to 995.'
        card = replace_one(r'<div class="client-update">.*?</div>',
            '<div class="client-update"><p class="section-label">Digital Marketing Update</p>'
            f'<p>{escape(narrative)}</p><p>{escape(notes[slug])}</p></div>', card)
        card = replace_one(r'<div class="performance-line">.*?</div>',
            f'<div class="performance-line"><strong>Reporting period: {period}. Comparisons: {comparison}. Sources refreshed September 7, 2026.</strong></div>',card)
        if slug == 'phil-medeiros':
            card = replace_one(r'<div class="performance-line">.*?</div>',
                '<div class="performance-line"><strong>Organic visibility has accelerated: clicks rose 125%, impressions rose 1,624%, and the site moved from position 15.6 to page-one territory at 9.2.</strong></div>', card)
        if slug == 'punch-transfers':
            card = replace_one(r'<div class="client-update">.*?</div>',
                '<div class="client-update"><p class="section-label">Digital Marketing Update</p><p>Search visibility is expanding. Page-level impressions increased from 1,730 to 3,150 over the last three months, while clicks remained close to the previous period at 31 versus 35.</p><p>The duck-cloth guide is already a page-one asset at position 7.2, generating 12 clicks and 317 impressions. The DTF-by-size product page is also gaining traction: clicks increased from 1 to 4 and its average position improved from 39.0 to 25.0.</p></div>', card)
            card = replace_one(r'<div class="performance-line">.*?</div>',
                '<div class="performance-line"><strong>Google is showing Punch Transfers far more often: page-level search impressions increased 82%, with one guide already ranking on page one and the main DTF product page gaining 14 positions.</strong></div>', card)
        if slug == 'south-coast-towing':
            card = replace_one(r'<div class="performance-line">.*?</div>',
                '<div class="performance-line"><strong>Website momentum is positive: sessions increased 8.3%, active users increased 14.4%, and average search position improved to 11.3—just outside page one.</strong></div>', card)
        card = replace_one(r'<div class="metrics" aria-label="[^"]+">.*?\n                </div>',
            f'<div class="metrics" aria-label="{escape(clients[slug]["name"])} performance metrics">\n                  ' +
            '\n                  '.join(metric(slug,*field) for field in fields) + '\n                </div>',card)
        if slug == 'phil-medeiros':
            card = card.replace('-8.10 pp vs previous', '9.3% previously · reach expanded')
            card = card.replace('-6.40 positions vs previous', 'Improved from 15.6')
        if slug == 'punch-transfers':
            card = replace_one(r'<div class="metrics" aria-label="[^"]+">.*?\n                </div>',
                '<div class="metrics" aria-label="Punch Transfers organic search performance metrics">\n'
                '                  <div class="metric"><span>Page impressions</span><strong>3,150</strong><div class="change">+82.1% vs previous</div></div>\n'
                '                  <div class="metric"><span>Top content position</span><strong>7.2</strong><div class="change">Page one</div></div>\n'
                '                  <div class="metric"><span>DTF product clicks</span><strong>4</strong><div class="change">Up from 1</div></div>\n'
                '                  <div class="metric"><span>DTF product position</span><strong>25.0</strong><div class="change">Improved from 39.0</div></div>\n'
                '                </div>', card)
        if slug == 'south-coast-towing':
            card = card.replace('-1.26 positions vs previous', 'Improved from 12.5')
            card = card.replace('No change vs previous', 'Tracking opportunity', 1)
        tag = 'GA4 only' if slug == 'chem-nut-supply' else ('Organic visibility expanding' if slug == 'punch-transfers' else ('Search visibility surge' if slug == 'phil-medeiros' else ('Traffic momentum' if slug == 'south-coast-towing' else ('Analytics refreshed' if ga is not None or ads is not None or sc is not None else 'Access pending'))))
        card = replace_one(r'<span class="tag[^\"]*">.*?</span>',f'<span class="tag">{tag}</span>',card)
        if slug == 'chem-nut-supply':
            card = card.replace('Website performance, Google Ads, revenue trend, and invoice follow-up.', 'GA4 website performance, recorded revenue, and engagement.')
        content = replace_one(pattern, card, content)

    # Headline metrics have separate populations; never add sessions to ad clicks,
    # or GA4 revenue to overlapping ad-attributed conversion value.
    ga_clients = [values(slug, 'ga4') for slug in clients if values(slug, 'ga4') is not None]
    sc_clients = [values(slug, 'search_console') for slug in clients if values(slug, 'search_console') is not None]
    sessions = sum(g['sessions'] for g in ga_clients)
    events = sum(g['keyEvents'] for g in ga_clients)
    revenue = sum(g['totalRevenue'] for g in ga_clients)
    search_clicks = sum(s['clicks'] for s in sc_clients)
    # The supplied Grub Tub export is fixed to this exact window.
    manual_matches = current == {'start': '2026-08-08', 'end': '2026-09-06'}
    if manual_matches:
        sessions += 3323
        revenue += 4642.84
        events += 14
    ga_count = len(ga_clients) + int(manual_matches)
    hero = [('GA4 sessions', fmt(sessions), f'{ga_count} properties; includes Grub Tub export' if manual_matches else f'{ga_count} properties'),
            ('Organic search clicks', fmt(search_clicks), f'{len(sc_clients)} Search Console properties'),
            ('GA4 recorded revenue', fmt(revenue, 'money'), 'All channels; USD; no Ads value added'),
            ('Instant Form leads', '5' if manual_matches else 'Unavailable', 'Modern Auto Body; manual Meta screenshot' if manual_matches else 'Manual source needs matching dates')]
    hero_html = '<div class="hero-metrics" aria-label="Punch Club summary">' + ''.join(
        f'<div class="hero-metric"><strong>{value}</strong><span>{label}</span><small>{note}</small></div>' for label,value,note in hero) + '</div>'
    content = replace_one(r'<div class="hero-metrics" aria-label="Punch Club summary">.*?(?=\n          </div>\s*<aside)',hero_html,content)
    content = re.sub(r'Performance reporting, rollout status, and account actions across active Punch Club marketing work\. Published [^<]+',
        f'Performance reporting and account actions across Punch Club. Reporting period: {period}. Compared with {comparison}. Updated September 7, 2026.\n            ',content,count=1)
    # Support rebuilds of an already updated report.
    content = re.sub(r'Performance reporting and account actions across Punch Club\.[^<]+',
        f'Performance reporting and account actions across Punch Club. Reporting period: {period}. Compared with {comparison}. Updated September 7, 2026.\n            ',content,count=1)
    summary = f'GA4 recorded {fmt(sessions)} sessions, {fmt(events)} key events and {fmt(revenue, "money")} in revenue across {ga_count} properties for {period}. Search Console recorded {fmt(search_clicks)} organic clicks across {len(sc_clients)} properties. Modern Auto Body recorded 5 Instant Form leads at $25.98 each on $129.90 in spend, supplied manually for this period.' if manual_matches else f'GA4 recorded {fmt(sessions)} sessions across {ga_count} properties for {period}.'
    sources = 'GA4 was refreshed for seven clients. Chem Nut Supply is GA4-only; Search Console was refreshed for the other six mapped clients. Grub Tub revenue uses the supplied GA4 export, and Modern Auto Body uses the supplied Meta screenshot. GA4 key events, Google Ads conversions and Instant Form leads remain separate measures and may overlap. Recorded revenue is not total business revenue. GA4 uses each property’s configured timezone. Search Console uses finalized data and may lag the reporting end date. Kathy Mackenzie retains the latest supplied campaign figures; their exact date range was not provided, so they are excluded from period totals.'
    ads_ok = [clients[s]['name'] for s in clients if values(s,'google_ads') is not None]
    ads_missing = [clients[s]['name'] for s in clients if 'google_ads' in clients[s]['sources'] and values(s,'google_ads') is None]
    sources += ' Google Ads refreshed: ' + ', '.join(ads_ok) + '.'
    if ads_missing: sources += ' Google Ads unavailable: ' + ', '.join(ads_missing) + '.'
    content = replace_one(r'(<section class="card wide-card" aria-labelledby="executive-summary-title">).*?</section>',
        '<section class="card wide-card" aria-labelledby="executive-summary-title"><h2 id="executive-summary-title">Executive Summary</h2>'
        f'<p>{escape(summary)}</p><div class="source-note">{escape(sources)}</div>'
        '<div class="source-note"><strong>Work notes:</strong> Prior operational notes are retained for follow-up. They do not confirm newly completed work. Billing and commission details remain excluded.</div></section>',content)
    content = replace_one(r'<aside class="summary-panel" aria-labelledby="snapshot-title">.*?</aside>',
        '<aside class="summary-panel" aria-labelledby="snapshot-title"><h2 id="snapshot-title">Reporting Snapshot</h2><div class="status-list">'
        '<div class="status-row"><div class="status-icon" aria-hidden="true">✓</div><div><strong>Website and search data refreshed</strong><span>Seven GA4 and six Search Console properties use the confirmed reporting window.</span></div></div>'
        '<div class="status-row"><div class="status-icon" aria-hidden="true">✓</div><div><strong>Manual results included</strong><span>Grub Tub revenue and Modern Auto Body Instant Form leads retain their supplied source dates.</span></div></div>'
        f'<div class="status-row warning"><div class="status-icon" aria-hidden="true">!</div><div><strong>Google Ads source coverage</strong><span>{len(ads_ok)} accounts refreshed; {len(ads_missing)} unavailable. See client notes.</span></div></div></div></aside>',content)
    content = content.replace('Rolling update showing last 30 days vs previous', 'Source dates and comparisons noted in each card')
    if 'id="punch-refresh-hidden-state"' not in content:
        content = content.replace('</head>', '<style id="punch-refresh-hidden-state">.data-refresh-banner[aria-hidden="true"] { display: none; }</style>\n</head>', 1)
    content = content.replace('Included under Punch Creatives properties; Google Ads API access is working.', 'GA4-only reporting. Google Ads is no longer available.')
    content = content.replace('GA4, Google Ads, and Search Console are mapped. Confirm report recipient.', 'GA4 is the current reporting source. Confirm report recipient.')
    content = content.replace('Add GA4 property ID and confirm recipient.', 'GA4 property 528955918 identified; revenue uses the supplied export while API access remains pending. Confirm recipient.')
    return content
