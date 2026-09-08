"""Read mapped Punch Google sources for an explicit, reproducible reporting window."""
import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path.home() / '.config/stott-marketing'
SLUGS = ['punch-transfers', 'chem-nut-supply', 'lc-mechanical', 'phil-medeiros',
         'south-coast-towing', 'tonys-auto', 'punch-creatives', 'dr-kathleen-mackenzie']

def request(url, headers=None, body=None):
    headers = dict(headers or {})
    if isinstance(body, dict):
        body = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers, data=body), timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Never persist request URLs, headers or credential-bearing error bodies.
        try:
            detail = json.load(exc)
            detail = detail[0] if isinstance(detail, list) else detail
            codes = [str(value) for item in detail.get('error', {}).get('details', [])
                     for error in item.get('errors', []) for value in error.get('errorCode', {}).values()]
        except Exception:
            codes = []
        raise RuntimeError(f'HTTP {exc.code}' + (': ' + ', '.join(codes) if codes else '')) from None

def access_token(profile):
    env_name = {'stott-primary': 'STOTT_PRIMARY_GOOGLE_TOKEN_JSON', 'sjawc-michaelrstott': 'SJAWC_GOOGLE_TOKEN_JSON', 'github-default': 'GOOGLE_TOKEN_JSON'}[profile]
    token = json.loads(os.environ[env_name]) if os.getenv(env_name) else json.loads((CONFIG / 'google-data/tokens' / f'{profile}.json').read_text())
    client = json.loads(os.environ['GOOGLE_OAUTH_CLIENT_JSON']) if os.getenv('GOOGLE_OAUTH_CLIENT_JSON') else json.loads((CONFIG / 'ga4-oauth-client.json').read_text())
    client = client.get('installed') or client.get('web') or client
    body = urllib.parse.urlencode({'client_id': token.get('client_id') or client['client_id'],
        'client_secret': token.get('client_secret') or client['client_secret'],
        'refresh_token': token['refresh_token'], 'grant_type': 'refresh_token'}).encode()
    return request('https://oauth2.googleapis.com/token', body=body)['access_token']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--ads-only', action='store_true')
    args = parser.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if end < start:
        parser.error('End must be on or after start')
    length = (end - start).days + 1
    windows = {'current': (str(start), str(end)),
               'previous': (str(start - timedelta(days=length)), str(start - timedelta(days=1)))}
    mapping_path = ROOT / 'data/punch-club/clients.json'
    config = json.loads((mapping_path if mapping_path.exists() else CONFIG / 'google-data/clients.json').read_text())
    ads = json.loads(os.environ['GOOGLE_ADS_CONFIG_JSON']) if os.getenv('GOOGLE_ADS_CONFIG_JSON') else json.loads((CONFIG / 'google-data/google-ads.json').read_text())
    clients = {slug: config['clients'][slug] for slug in SLUGS}
    profiles = {c['google_profile'] for c in clients.values()} | {'sjawc-michaelrstott'}
    if os.getenv('GOOGLE_TOKEN_JSON'): profiles.add('github-default')
    tokens = {}
    for profile in sorted(profiles):
        try: tokens[profile] = access_token(profile)
        except Exception: print(profile, 'authentication unavailable')
    if not tokens: raise RuntimeError('No Google reporting connection available')

    def fetch_client(item):
        slug, client = item
        headers = {'Authorization': 'Bearer ' + tokens.get(client['google_profile'], next(iter(tokens.values())))}
        result = {'name': client['display_name'], 'sources': {}}
        for source, key in [('ga4', 'ga4_property_id'), ('search_console', 'search_console_site_url'), ('google_ads', 'google_ads_customer_id')]:
            if args.ads_only and source != 'google_ads':
                continue
            identifier = client.get(key)
            if not identifier:
                continue
            source_result = {'identifier': identifier}
            for window, (s, e) in windows.items():
                try:
                    if source == 'ga4':
                        raw = request(f'https://analyticsdata.googleapis.com/v1beta/properties/{identifier}:runReport', headers,
                            {'dateRanges': [{'startDate': s, 'endDate': e}], 'metrics': [{'name': m} for m in
                             ['sessions', 'activeUsers', 'keyEvents', 'totalRevenue', 'engagementRate']]})
                        values = (raw.get('rows') or [{'metricValues': [{'value': '0'}] * 5}])[0]['metricValues']
                        metrics = {h['name']: float(v['value']) for h, v in zip(raw['metricHeaders'], values)}
                        metrics['currency'] = raw.get('metadata', {}).get('currencyCode')
                        metrics['timezone'] = raw.get('metadata', {}).get('timeZone')
                    elif source == 'search_console':
                        raw = request('https://www.googleapis.com/webmasters/v3/sites/' + urllib.parse.quote(identifier, safe='') + '/searchAnalytics/query',
                            headers, {'startDate': s, 'endDate': e, 'dataState': 'final'})
                        metrics = (raw.get('rows') or [{'clicks': 0, 'impressions': 0, 'ctr': 0, 'position': None}])[0]
                    else:
                        query = f"SELECT customer.currency_code, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value FROM customer WHERE segments.date BETWEEN '{s}' AND '{e}'"
                        managers = [None, (client.get('google_ads_login_customer_id') or ads['manager_customer_id']).replace('-', '')]
                        if slug == 'south-coast-towing': managers.append('4019090217')
                        raw = None
                        errors = set()
                        for profile, token in tokens.items():
                            for manager in managers:
                                ad_headers = {'Authorization': 'Bearer ' + token, 'developer-token': ads['developer_token']}
                                if manager: ad_headers['login-customer-id'] = manager
                                try:
                                    raw = request('https://googleads.googleapis.com/v22/customers/' + identifier.replace('-', '') + '/googleAds:searchStream', ad_headers, {'query': query})
                                    source_result['connection'] = {'profile': profile, 'manager': manager}
                                    break
                                except RuntimeError as exc: errors.add(str(exc))
                            if raw is not None: break
                        if raw is None: raise RuntimeError('; '.join(sorted(errors)))
                        rows = [r for batch in raw for r in batch.get('results', [])]
                        metrics = {k: sum(float(r.get('metrics', {}).get(k, 0)) for r in rows) for k in
                            ['costMicros', 'impressions', 'clicks', 'conversions', 'conversionsValue']}
                        metrics['spend'] = metrics.pop('costMicros') / 1e6
                        metrics['currency'] = rows[0].get('customer', {}).get('currencyCode') if rows else None
                        metrics['average_cpc'] = metrics['spend'] / metrics['clicks'] if metrics['clicks'] else None
                        metrics['roas'] = metrics['conversionsValue'] / metrics['spend'] if metrics['spend'] else None
                    source_result[window] = {'status': 'ok', 'metrics': metrics}
                except Exception as exc:
                    source_result[window] = {'status': 'error', 'error': str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__}
            result['sources'][source] = source_result
        return slug, result

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(fetch_client, clients.items()))
    output = {'periods': {k: {'start': s, 'end': e} for k, (s, e) in windows.items()},
              'refreshed_at': datetime.now(timezone.utc).isoformat(), 'clients': results}
    target = ROOT / 'data/punch-club/google.json'
    if args.ads_only:
        existing = json.loads(target.read_text())
        if existing['periods'] != output['periods']:
            raise ValueError('Cached periods must match the Ads refresh')
        for slug, client in results.items():
            existing['clients'][slug]['sources'].update(client['sources'])
        output['clients'] = existing['clients']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2))
    for slug, result in results.items():
        print(slug, {source: {w: data[w]['status'] for w in windows} for source, data in result['sources'].items()})

if __name__ == '__main__':
    main()
