import json, urllib.parse, urllib.request, webbrowser, http.server, socket
from pathlib import Path

CONFIG = Path.home() / ".config" / "stott-marketing"
profile = "sjawc-michaelrstott"
token_path = CONFIG / "google-data" / "tokens" / f"{profile}.json"
client_path = CONFIG / "ga4-oauth-client.json"

# Use client from existing token file if present
if token_path.exists():
    td = json.loads(token_path.read_text())
    client_id = td.get("client_id")
    client_secret = td.get("client_secret")
else:
    cd = json.loads(client_path.read_text())
    c = cd.get("installed") or cd.get("web") or cd
    client_id = c["client_id"]; client_secret = c["client_secret"]

print(f"Client ID: {client_id}")

# Start local callback server
PORT = 8765
code_holder = {}

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if "code" in qs:
            code_holder["code"] = qs["code"][0]
            self.send_response(200); self.end_headers()
            self.wfile.write(b"<h1>Auth OK! You can close this window and return to terminal.</h1>")
        else:
            self.send_response(400); self.end_headers()
            self.wfile.write(b"Missing code")
    def log_message(self, *a): pass

server = http.server.HTTPServer(("localhost", PORT), Handler)
print(f"Starting callback server on http://localhost:{PORT}")

scopes = ["https://www.googleapis.com/auth/analytics.readonly","https://www.googleapis.com/auth/adwords","https://www.googleapis.com/auth/webmasters.readonly"]
auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": client_id,
    "redirect_uri": f"http://localhost:{PORT}",
    "response_type": "code",
    "scope": " ".join(scopes),
    "access_type": "offline",
    "prompt": "consent"
})
print(f"\nOpening browser to:\n{auth_url}\n")
webbrowser.open(auth_url)
print("Waiting for callback...")
server.handle_request()

if "code" not in code_holder:
    print("No code received"); exit(1)

code = code_holder["code"]
print(f"Got code {code[:20]}...")

# Exchange code for tokens
payload = urllib.parse.urlencode({
    "client_id": client_id,
    "client_secret": client_secret,
    "code": code,
    "grant_type": "authorization_code",
    "redirect_uri": f"http://localhost:{PORT}"
}).encode()
req = urllib.request.Request("https://oauth2.googleapis.com/token", data=payload, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
with urllib.request.urlopen(req, timeout=30) as r:
    data = json.loads(r.read().decode())
    print(f"Token response: {json.dumps(data, indent=2)[:1000]}")
    if "refresh_token" not in data:
        print("WARNING: No refresh_token returned! You may need to revoke access at https://myaccount.google.com/permissions and try again")
    # Save
    out = {
        "token": data["access_token"],
        "refresh_token": data.get("refresh_token") or td.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": scopes,
        "expiry": ""
    }
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved new token to {token_path}")
    print("Now run: python3 tools/refresh_sjawc_data.py")
