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

## Notes

The SJAWC report currently uses static/generated page output plus local build scripts. Some refreshed reporting inputs are private data exports and are intentionally excluded from Git.

