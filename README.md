# Client Update Portal

Private Firebase-hosted client update portal for Stott Marketing.

Live site:

- `https://clients.stott.marketing`
- SJAWC report: `https://clients.stott.marketing/st-johns-aesthetics/`
- Private owner workspace: `https://clients.stott.marketing/manage/`

## What Is Tracked

This repo tracks the portal source, generated public static files, and build/deploy scripts.

This repo intentionally does **not** track:

- API tokens
- OAuth refresh tokens
- Firebase service account keys
- Firestore recovery exports
- Raw GHL/contact data exports
- Local PDFs
- Large licensed/stock-image backup folders

## Local Build

From the repo root:

```bash
python3 tools/build_firebase_static.py
```

The Firebase public directory is:

```bash
firebase-static/public
```

## Local Preview

```bash
python3 -m http.server 8019 --directory firebase-static/public
```

Then open:

```text
http://localhost:8019/st-johns-aesthetics/
```

## Deploy

Manual deploy from local machine:

```bash
cd firebase-static
firebase deploy --only hosting --project stott-mktg-client-update-data
```

Preferred deploy method is GitHub Actions using a service account stored as a GitHub secret.

Required GitHub secret:

```text
FIREBASE_SERVICE_ACCOUNT_JSON
```

That secret should contain the full JSON for a Firebase/GCP service account with permission to deploy Firebase Hosting for project:

```text
stott-mktg-client-update-data
```

Do not commit the service account JSON file.

## Scheduled Z4B Refresh

The Zincs for Boats report can be refreshed by GitHub Actions with:

```text
.github/workflows/refresh-z4b-data.yml
```

Required GitHub secrets for Shopify refresh:

```text
Z4B_SHOPIFY_SHOP
Z4B_SHOPIFY_ACCESS_TOKEN
```

The workflow runs `tools/refresh_z4b_data.py`, rebuilds the static portal, and commits refreshed cached report JSON plus the generated public HTML when data changes. Pushing that commit to `main` triggers the Firebase Hosting deploy workflow.

Google Analytics, Search Console, Search Atlas, and Google Ads still require local config under `~/.config/stott-marketing` unless matching cloud credentials are added later. Their refresh failures are recorded in `data/z4b/refresh_summary.json`; existing cached files remain in place so unavailable sources do not block a Shopify-only refresh.

## Notes

The SJAWC report currently uses static/generated page output plus local build scripts. Some refreshed reporting inputs are private data exports and are intentionally excluded from Git.

## Facebook Ads API Config

Facebook Ads credentials and account mappings stay outside Git. Add mapped clients at:

```text
~/.config/stott-marketing/meta-data/facebook_ads_clients.json
```

Example:

```json
{
  "clients": [
    {
      "client_slug": "punch-club",
      "client_name": "Punch Club",
      "child_client_slug": "grub-tub-rentals",
      "child_client_name": "Grub Tub Rentals",
      "ad_account_id": "1234567890",
      "token_name": "michaelrstott"
    }
  ]
}
```

The access token is read from `META_ACCESS_TOKEN`, `FACEBOOK_ACCESS_TOKEN`, or:

```text
~/.config/stott-marketing/meta-data/tokens/<token_name>.txt
```

Run:

```bash
python3 tools/refresh_facebook_ads_data.py
```

Outputs are written to `data/facebook_ads/` with one JSON file per mapped client or child client.

For GitHub Actions, the same mapping can be stored as a repository secret instead of a local file:

```text
FACEBOOK_ADS_CLIENTS_JSON
```

For Punch-only mappings, this secret is also supported:

```text
PUNCH_FACEBOOK_ADS_CLIENTS_JSON
```

The Punch workflow filters records to `client_slug: "punch-club"` before refreshing so child account files stay isolated from other clients. If one Meta token is not enough, named token maps can be stored in:

```text
META_ACCESS_TOKENS_JSON
```

## Scheduled SJAWC Refresh

The St. Johns Aesthetics report refreshes through:

```text
.github/workflows/refresh-sjawc-data.yml
```

It refreshes aggregate cached data, rebuilds `firebase-static/public/st-johns-aesthetics/index.html`, and commits the updated report when values change. Supported GitHub secrets are:

```text
SJAWC_GOOGLE_TOKEN_JSON
GOOGLE_OAUTH_CLIENT_JSON
GOOGLE_ADS_CONFIG_JSON
SJAWC_META_ACCESS_TOKEN
SJAWC_GHL_ACCESS_TOKEN
SEARCH_ATLAS_API_KEY
```

The workflow tracks only aggregate report JSON for SJAWC. Raw GHL/contact exports remain ignored.
