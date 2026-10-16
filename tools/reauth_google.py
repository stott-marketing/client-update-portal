"""Reconnect the existing SJAWC Google account without logging credentials."""
import argparse
import hashlib
import base64
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
import http.server
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--ads', action='store_true')
parser.add_argument('--email')
args = parser.parse_args()
CONFIG = Path.home() / '.config' / 'stott-marketing'
token_path = CONFIG / 'google-data' / 'tokens' / ('sjawc-ads-michaelrstott.json' if args.ads else 'sjawc-michaelrstott.json')
td = json.loads(token_path.read_text()) if token_path.exists() else {}
client_data = json.loads((CONFIG / 'ga4-oauth-client.json').read_text())
client = client_data.get('installed') or client_data.get('web') or client_data
client_id = td.get('client_id') or client['client_id']
client_secret = td.get('client_secret') or client['client_secret']
scopes = td.get('scopes') or ['https://www.googleapis.com/auth/analytics.readonly', 'https://www.googleapis.com/auth/adwords', 'https://www.googleapis.com/auth/webmasters.readonly']
if args.ads:
    scopes = ['https://www.googleapis.com/auth/adwords']
if isinstance(scopes, str):
    scopes = scopes.split()
state = secrets.token_urlsafe(32)
verifier = secrets.token_urlsafe(64)
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
result = {}

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if qs.get('state', [''])[0] != state:
            self.send_response(400); self.end_headers(); self.wfile.write(b'Invalid authorization state.'); return
        if qs.get('error'):
            result['error'] = qs['error'][0]
        elif qs.get('code'):
            result['code'] = qs['code'][0]
        else:
            self.send_response(400); self.end_headers(); return
        self.send_response(200); self.end_headers()
        self.wfile.write(b'Google authorization received. Return to Codex to check connection status.')
    def log_message(self, *args):
        pass

server = http.server.HTTPServer(('127.0.0.1', 8769), Handler)
server.timeout = 1
redirect = 'http://localhost:8769'
url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({'client_id': client_id, 'redirect_uri': redirect, 'response_type': 'code', 'scope': ' '.join(scopes), 'access_type': 'offline', 'prompt': 'consent', 'login_hint': args.email or '', 'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256'})
print('Authorize the existing SJAWC Google connection at:\n' + url, flush=True)
deadline = time.monotonic() + 1200
while not result and time.monotonic() < deadline:
    server.handle_request()
server.server_close()
if not result.get('code'):
    raise SystemExit('Authorization was cancelled or timed out; credentials unchanged.')
payload = urllib.parse.urlencode({'client_id': client_id, 'client_secret': client_secret, 'code': result['code'], 'grant_type': 'authorization_code', 'redirect_uri': redirect, 'code_verifier': verifier}).encode()
try:
    with urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token', data=payload), timeout=30) as response:
        data = json.load(response)
except urllib.error.HTTPError as exc:
    error = json.load(exc)
    raise SystemExit('Google authorization failed: ' + str(error.get('error', exc.code)))
if not data.get('refresh_token'):
    raise SystemExit('Google returned no refresh token; existing credentials unchanged.')
out = dict(td, token=data['access_token'], refresh_token=data['refresh_token'], token_uri='https://oauth2.googleapis.com/token', client_id=client_id, client_secret=client_secret, scopes=scopes, expiry='')
token_path.parent.mkdir(parents=True, exist_ok=True)
token_path.write_text(json.dumps(out, indent=2))
token_path.chmod(0o600)
print('Saved renewed SJAWC Google credentials securely. No token values were logged.', flush=True)
