# Report Automation Notes

This file tracks how the client reporting automation is configured. Do not add API keys, OAuth refresh tokens, service account JSON, downloaded client exports, or other credentials to this file.

## Live Hosting

- Production domain: `https://clients.stott.marketing`
- Firebase project: `stott-mktg-client-update-data`
- Public hosting directory: `firebase-static/public`
- Deploy workflow: `.github/workflows/deploy-firebase-hosting.yml`
- Required GitHub secret: `FIREBASE_SERVICE_ACCOUNT_JSON`

Deploys can be run manually from GitHub Actions. Pushes to `main` also trigger the deploy workflow.

Important: commits created by GitHub Actions with the default `GITHUB_TOKEN` may not trigger a second workflow automatically. If a refresh workflow commits updated report data and the live site does not change, run the Firebase deploy workflow manually.

## Client Reports

### St. Johns Aesthetics

- Live URL: `https://clients.stott.marketing/st-johns-aesthetics/`
- Refresh workflow: `.github/workflows/refresh-sjawc-data.yml`
- Build script: `tools/build_sjawc_meeting_report.py`
- Refresh script: `tools/refresh_sjawc_data.py`
- Cached data directory: `data/sjawc/`
- Generated report directory: `firebase-static/public/st-johns-aesthetics/`

Primary data sources:

- GA4
- Google Ads
- Go High Level
- Meta Ads
- Search Atlas, where available
- Boulevard revenue workbook or exported sales file for confirmed revenue matching

Required or supported GitHub secrets by name:

- `SJAWC_GOOGLE_TOKEN_JSON`
- `GOOGLE_OAUTH_CLIENT_JSON`
- `GOOGLE_ADS_CONFIG_JSON`
- `SJAWC_META_TOKEN`
- `SJAWC_GHL_TOKEN`
- `SEARCH_ATLAS_API_KEY`

Operational notes:

- The report format should stay stable unless the client-facing layout is intentionally changed.
- Performance labels were added for last 30 days compared with previous 30 days.
- Boulevard revenue is the most trusted revenue source, but it is not automatically attributable to the original channel without matching against GHL, GA4, Google Ads, or other source fields.
- GHL is the best source for lead/contact source context.
- Google Ads appointment qualification is currently represented through Zapier-driven GHL tags. The tag logic discussed was that Google Ads-qualified contacts contain Zapier-related tags, including patterns such as `new_appointment_zap`, `new_appointment_staff_zap`, and `client_updated_zap`.
- Zapier has sent Boulevard appointment data into Google Ads as offline conversions. Google Ads may show imported conversions, but order-level matching can still be limited depending on what identifiers are stored and exposed.
- The imported Boulevard Appointment conversion action observed in Google Ads was removed at one point, so verify the active conversion action before relying on that metric.

Manual inputs:

- Confirmed Boulevard revenue may need to be supplied or uploaded from an export.
- Boulevard/GHL matching is sensitive and should stay in local exports or secure workflow inputs, not committed raw.

### Airocide Systems

- Live URL: `https://clients.stott.marketing/airocide-systems/`
- Test URL used during build review: `https://clients.stott.marketing/airocide-systems-test/`
- Refresh workflow: `.github/workflows/refresh-airocide-data.yml`
- Build script: `tools/build_airocide_report.py`
- Refresh script: `tools/refresh_airocide_data.py`
- Cached data directory: `data/airocide/`
- Generated report directory: `firebase-static/public/airocide-systems/`

Primary data sources:

- GA4
- Google Search Console
- Search Atlas, read-only where available
- Meta Ads is available but not used for this report
- Google Ads is noted as not configured for the Airocide report

Reporting rules:

- Brand consolidation start date: April 1, 2026
- Main commercial domain focus: `www.airocide.com`
- Residential/KES Technology reporting should be separated from commercial reporting.
- KES Technology revenue belongs to `shop.airocide.com` / Shopify and should not be blended into commercial Airocide Systems performance.
- Commercial performance should focus on SEO, visibility, form/contact path, Search Console, content growth, brand protection, and commercial lead behavior.

Important completed work:

- Airocide refresh failed because the Google token secret was being injected directly into the shell script. The workflow now writes secrets through environment variables with `printf`.
- Airocide refresh then succeeded but did not save data because the commit step referenced an optional missing path. The workflow now checks whether each file exists before adding it.
- Successful Airocide refresh run wrote data through September 6, 2026 and committed refreshed report data.
- Firebase deploy was manually triggered after the successful refresh so the live report was updated.

Required or supported GitHub secrets by name:

- `GOOGLE_TOKEN_JSON`
- `STOTT_PRIMARY_GOOGLE_TOKEN_JSON`
- `GOOGLE_OAUTH_CLIENT_JSON`
- `SEARCH_ATLAS_API_KEY`

Manual inputs:

- Brand protection document links are hosted outside the repo.
- Client-facing report text should not expose sensitive evidence or internal working files.

### Punch Club

- Live URL: `https://clients.stott.marketing/punch-club/`
- Refresh workflow: `.github/workflows/refresh-punch-club-data.yml`
- Build script: `tools/build_punch_club_static.py`
- Refresh script: `tools/refresh_facebook_ads_data.py`
- Cached Meta Ads data directory: `data/facebook_ads/`
- Generated report file: `firebase-static/public/punch-club/index.html`

Primary data sources:

- Meta Ads / Facebook Ads account mappings

Required or supported GitHub secrets by name:

- `FACEBOOK_ADS_CLIENTS_JSON`
- `PUNCH_FACEBOOK_ADS_CLIENTS_JSON`
- `META_ACCESS_TOKEN`
- `FACEBOOK_ACCESS_TOKEN`
- `META_ACCESS_TOKENS_JSON`
- `FACEBOOK_ACCESS_TOKENS_JSON`

Operational notes:

- The Punch workflow filters Facebook Ads mappings to `client_slug: "punch-club"`.
- Child client/ad account files should remain isolated from other clients.
- Kathy Mackenzie is tracked as Punch child slug `dr-mackenzie`; the current card summarizes Exit Plan Google Ads performance and the third-party store-click conversion tracking gap.
- Modern Auto Body was added as Punch child slug `modern-auto-body` for portfolio reporting setup.

Punch Club analytics update, September 7, 2026:
- The confirmed report window is August 8–September 6, compared with July 9–August 7.
- `tools/refresh_punch_google_data.py` reads aggregate Google metrics using explicit `--start` and `--end` dates. It uses local credentials or the existing Google GitHub environment secrets and never saves raw API responses or credentials in its output.
- `data/punch-club/clients.json` contains non-secret reporting mappings and source scope. Chem Nut Supply now uses GA4 only. Kathy Mackenzie retains the latest user-supplied campaign figures, with no asserted exact period or verified API connection.
- `data/punch-club/google.json` stores the dated aggregate source results. `tools/punch_analytics_renderer.py` applies those results to the existing layout on rebuild. This Google refresh is not added to the existing daily Meta workflow; rebuilding alone retains the dated Google snapshot.
- Punch Transfers and LC Mechanical Ads were retrieved through direct account access. South Coast Towing Ads returned `CUSTOMER_NOT_ENABLED`; its GA4 and Search Console data remain available.
- Grub Tub uses its supplied GA4 export and cached Meta figures. Modern Auto Body uses the supplied Instant Form screenshot. Neither manual source is relabeled as a new API refresh.
- Summary totals keep GA4 sessions, Search Console clicks, GA4 revenue and Modern Auto Body Instant Form leads separate, avoiding overlaps between platforms.

### Zincs for Boats

- Live URL: `https://clients.stott.marketing/zincs-for-boats/`
- Refresh workflow: `.github/workflows/refresh-z4b-data.yml`
- Build script: `tools/build_z4b_report.py`
- Refresh script: `tools/refresh_z4b_data.py`
- Cached data directory: `data/z4b/`
- Generated live data file: `firebase-static/public/zincs-for-boats/data/live.json`

Primary data sources:

- Shopify
- GA4, where credentials are available
- Search Console, where credentials are available
- Search Atlas, where available
- Google Ads, where configured

Required Shopify GitHub secrets by name:

- `Z4B_SHOPIFY_SHOP`
- `Z4B_SHOPIFY_ACCESS_TOKEN`

Other supported shared secrets by name:

- `GOOGLE_TOKEN_JSON`
- `GOOGLE_OAUTH_CLIENT_JSON`
- `SEARCH_ATLAS_API_KEY`

Operational notes:

- Z4B refresh succeeded after Shopify secrets were added.
- The workflow writes last 30 vs previous 30, last month, last quarter, and YTD cached windows.
- If non-Shopify sources are unavailable, failures should be captured in refresh summaries while cached data remains usable.

## Common Workflow Commands

Run these from GitHub Actions or through GitHub CLI:

- `refresh-sjawc-data.yml`
- `refresh-airocide-data.yml`
- `refresh-punch-club-data.yml`
- `refresh-z4b-data.yml`
- `deploy-firebase-hosting.yml`

Recommended order when forcing a full refresh:

1. Run each client refresh workflow.
2. Confirm each refresh workflow completed successfully.
3. Check whether refreshed data was committed to `main`.
4. If needed, run `deploy-firebase-hosting.yml`.
5. Verify the live client URL.

## Troubleshooting

- If a workflow fails in the first few seconds, check secret formatting and whether multi-line JSON is being injected safely.
- If a workflow succeeds but the live page does not change, check whether the refresh created a commit and whether Firebase deploy ran afterward.
- If a workflow says there are no changes, the refreshed data may match the existing cached data.
- If Google data fails, reauthorize the local Google token and update the matching GitHub secret.
- If Shopify data fails, verify the shop domain and access token secret names.
- If Meta data fails, verify the client mapping JSON, token name, and ad account access.
- Do not commit raw exports from Boulevard, GHL, Shopify, Meta, GA4, or Search Console unless they are intentionally aggregated and scrubbed.
