# PATCH: Real MoM = last 30 days vs prev 30 days, plus Apr1->Today total
from __future__ import annotations
import json, subprocess, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "airocide"
CONFIG = Path.home() / ".config" / "stott-marketing"
CONSOLIDATION_START = date(2026, 4, 1)
LIVE_TARGETS = [
    ROOT / "firebase-static" / "public" / "airocide-systems" / "data" / "live.json",
    ROOT / "client-update-portal" / "public" / "airocide-systems" / "data" / "live.json",
]
AIROCIDE = {
    "display_name": "Airocide Systems",
    "google_profile": "stott-primary",
    "ga4_property_id": "534063449",
    "additional_ga4_properties": {"corporate_or_legacy": "529871368","dealer_portal": "533070374"},
    "search_atlas_domain": "airocide.com",
    "search_console_site_url": "https://www.airocide.com/",
}
def request_json(url, *, method="GET", headers=None, body=None):
    data=None; request_headers=dict(headers or {})
    if body is not None: data=json.dumps(body).encode("utf-8"); request_headers["Content-Type"]="application/json"
    req=urllib.request.Request(url, data=data, method=method, headers=request_headers)
    with urllib.request.urlopen(req, timeout=60) as response: return json.loads(response.read().decode("utf-8"))
def request_json_curl(url, *, headers=None):
    cmd=["curl","-sS"]; [cmd.extend(["-H", f"{k}: {v}"]) for k,v in (headers or {}).items()]; cmd.append(url)
    result=subprocess.run(cmd, check=True, capture_output=True, text=True); return json.loads(result.stdout or "{}")
def save(name, data): OUT.mkdir(parents=True, exist_ok=True); (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
def read_text(path): return path.read_text(encoding="utf-8").strip()
def google_access_token(profile):
    token_path=CONFIG / "google-data" / "tokens" / f"{profile}.json"; client_path=CONFIG / "ga4-oauth-client.json"
    env_token=Path("/tmp/google_token.json"); env_client=Path("/tmp/google_oauth_client.json")
    if env_token.exists(): token_path=env_token
    if env_client.exists(): client_path=env_client
    token=json.loads(token_path.read_text(encoding="utf-8")); client=json.loads(client_path.read_text(encoding="utf-8"))
    client_data=client.get("installed") or client.get("web") or client
    payload=urllib.parse.urlencode({"client_id": client_data["client_id"],"client_secret": client_data["client_secret"],"refresh_token": token["refresh_token"],"grant_type": "refresh_token"}).encode("utf-8")
    req=urllib.request.Request("https://oauth2.googleapis.com/token", data=payload, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as response: data=json.loads(response.read().decode("utf-8"))
    return data["access_token"]
def refresh_ga4_property(access_token, property_id, start, end):
    url=f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    body={"dateRanges": [{"startDate": start, "endDate": end}],"metrics": [{"name": "activeUsers"},{"name": "sessions"},{"name": "newUsers"},{"name": "engagementRate"},{"name": "keyEvents"},{"name": "totalRevenue"},{"name": "ecommercePurchases"},{"name": "totalPurchasers"}]}
    raw=request_json(url, method="POST", headers={"Authorization": f"Bearer {access_token}"}, body=body)
    values=[v.get("value") for v in raw.get("rows", [{}])[0].get("metricValues", [])]
    keys=["active_users","sessions","new_users","engagement_rate","key_events","total_revenue","ecommerce_purchases","total_purchasers"]
    return {"property_id": property_id, "period": {"start": start, "end": end}, "metrics": dict(zip(keys, values)), "raw": raw}
def refresh_ga4_channels(access_token, property_id, start, end):
    url=f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    body={"dateRanges": [{"startDate": start, "endDate": end}],"dimensions": [{"name": "sessionDefaultChannelGroup"}],"metrics": [{"name": "sessions"},{"name": "activeUsers"},{"name": "keyEvents"},{"name": "totalRevenue"},{"name": "ecommercePurchases"}],"orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],"limit": 12}
    return request_json(url, method="POST", headers={"Authorization": f"Bearer {access_token}"}, body=body)
def refresh_ga4_report(access_token, property_id, start, end, *, dimensions, metrics, limit=100, order_metric=None):
    url=f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    body={"dateRanges": [{"startDate": start, "endDate": end}],"dimensions": [{"name": d} for d in dimensions],"metrics": [{"name": m} for m in metrics],"limit": limit}
    if order_metric: body["orderBys"]=[{"metric": {"metricName": order_metric}, "desc": True}]
    return request_json(url, method="POST", headers={"Authorization": f"Bearer {access_token}"}, body=body)
def refresh_ga4_hostname_breakout(access_token, property_id, start, end):
    return {"period": {"start": start, "end": end},"property_id": property_id,"hostname_totals": refresh_ga4_report(access_token, property_id, start, end, dimensions=["hostName"], metrics=["sessions","activeUsers","keyEvents","totalRevenue","ecommercePurchases","totalPurchasers"], limit=50, order_metric="sessions"),"hostname_events": refresh_ga4_report(access_token, property_id, start, end, dimensions=["hostName","eventName"], metrics=["eventCount","totalUsers","totalRevenue"], limit=200, order_metric="eventCount"),"hostname_pages": refresh_ga4_report(access_token, property_id, start, end, dimensions=["hostName","pagePath"], metrics=["screenPageViews","activeUsers","keyEvents","totalRevenue"], limit=300, order_metric="screenPageViews")}
def refresh_search_console(access_token, start, end):
    base="https://www.googleapis.com/webmasters/v3/sites/"; site=urllib.parse.quote(AIROCIDE["search_console_site_url"], safe=""); url=f"{base}{site}/searchAnalytics/query"; headers={"Authorization": f"Bearer {access_token}"}; common={"startDate": start, "endDate": end}
    summary=request_json(url, method="POST", headers=headers, body={**common, "rowLimit": 1}); queries=request_json(url, method="POST", headers=headers, body={**common, "dimensions": ["query"], "rowLimit": 10, "orderBy": [{"fieldName": "clicks", "sortOrder": "descending"}]}); pages=request_json(url, method="POST", headers=headers, body={**common, "dimensions": ["page"], "rowLimit": 10, "orderBy": [{"fieldName": "clicks", "sortOrder": "descending"}]})
    return {"period": {"start": start, "end": end}, "site_url": AIROCIDE["search_console_site_url"], "summary": summary, "queries": queries, "pages": pages}
def extract_search_atlas_project(project):
    se=((project.get("data_v2") or {}).get("se") or {}); legacy_se=((project.get("data") or {}).get("se") or {}); sa=((project.get("data_v2") or {}).get("sa") or {}); otto=((project.get("data_v2") or {}).get("otto_v2") or {}); llm=((project.get("data_v2") or {}).get("llmv") or {})
    keyword_trend=se.get("organic_keywords_trend") or legacy_se.get("organic_keywords_trend") or []; traffic_trend=se.get("organic_traffic_trend") or legacy_se.get("organic_traffic_trend") or []
    return {"project_id": project.get("id"),"domain": project.get("domain_url"),"ai_summary": project.get("ai_summary"),"organic_keywords_trend": keyword_trend,"organic_traffic_trend": traffic_trend,"metrics": {"site_health": sa.get("health"),"domain_power": se.get("domain_power"),"domain_rating": se.get("domain_rating"),"domain_authority": se.get("domain_authority"),"organic_traffic": se.get("organic_traffic") or se.get("traffic"),"traffic_change": se.get("traffic_change"),"traffic_change_percent": se.get("traffic_change_percent"),"keyword_count": se.get("keyword_count") or se.get("organic_keywords"),"keyword_count_change": se.get("keyword_count_change"),"keyword_count_change_percent": se.get("keyword_count_change_percent"),"top_3_keywords_count": se.get("top_3_keywords_count"),"refdomain_count": se.get("refdomain_count") or se.get("refdomains"),"refdomain_new_count": se.get("refdomain_new_count"),"refdomain_lost_count": se.get("refdomain_lost_count"),"backlinks": se.get("backlinks"),"spam_score": se.get("spam_score"),"otto_score": otto.get("seo_optimization_score"),"otto_total_deployed_fixes": otto.get("total_deployed_fixes"),"otto_total_time_saved": otto.get("total_time_saved"),"llm_current_mentions": llm.get("current_mentions"),"llm_previous_mentions": llm.get("previous_mentions")}}
def refresh_search_atlas():
    key_path=CONFIG / "search-atlas" / "tokens" / "search-atlas-key.txt"; env_key=Path("/tmp/search_atlas_key.txt")
    if env_key.exists(): key_path=env_key
    key=read_text(key_path); data=request_json_curl("https://api.searchatlas.com/api/customer/projects/projects/", headers={"X-API-Key": key}); projects=data.get("results") or data.get("data") or []; by_domain={p.get("domain_url"): p for p in projects}; domain=AIROCIDE["search_atlas_domain"]
    if domain not in by_domain: raise RuntimeError(f"Search Atlas project not found for {domain}")
    return {"source": "search_atlas_api", "domain": extract_search_atlas_project(by_domain[domain])}
def calc_mom(c,p):
    try: c=float(c or 0); p=float(p or 0); return None if p==0 else round(((c-p)/p)*100,1)
    except: return None
def build_live_json(main_ga4, last30, prev30, ga4_channels, search_console, atlas, period, mom_period):
    curr_m=main_ga4.get("metrics", {}); l30_m=last30.get("metrics", {}); p30_m=prev30.get("metrics", {})
    mom={k: calc_mom(l30_m.get(k), p30_m.get(k)) for k in l30_m.keys()}
    channel_rows=[]
    for row in (ga4_channels.get("rows") or []):
        dim=(row.get("dimensionValues") or [{}])[0].get("value") or "Unknown"; vals=[v.get("value") for v in row.get("metricValues", [])]
        channel_rows.append({"channel": dim,"sessions": vals[0] if len(vals)>0 else "0","active_users": vals[1] if len(vals)>1 else "0","key_events": vals[2] if len(vals)>2 else "0"})
    live={"client_slug": "airocide-systems","updatedAt": datetime.now(timezone.utc).isoformat(),"window": {"start": period["start"],"end": period["end"],"label": f"Apr 1 -> {period['end']} (Live)","mom_label": f"MoM: Last 30 vs Prev 30"},"period": period,"mom_period": mom_period,"ga4_property_id": AIROCIDE["ga4_property_id"],"metrics_total_apr1_to_today": curr_m,"metrics_last30": l30_m,"metrics_prev30": p30_m,"mom_percent_last30_vs_prev30": mom,"channels": channel_rows,"search_console": {"clicks": ((search_console.get("summary", {}).get("rows") or [{}])[0].get("clicks") or 0),"impressions": ((search_console.get("summary", {}).get("rows") or [{}])[0].get("impressions") or 0)},"search_atlas": atlas.get("domain", {}).get("metrics", {}),"cards": {"sessions": {"total_apr1_today": curr_m.get("sessions"),"last30": l30_m.get("sessions"),"prev30": p30_m.get("sessions"),"mom": mom.get("sessions")},"active_users": {"total_apr1_today": curr_m.get("active_users"),"last30": l30_m.get("active_users"),"prev30": p30_m.get("active_users"),"mom": mom.get("active_users")},"key_events": {"total_apr1_today": curr_m.get("key_events"),"last30": l30_m.get("key_events"),"prev30": p30_m.get("key_events"),"mom": mom.get("key_events")},"engagement_rate": {"total_apr1_today": curr_m.get("engagement_rate"),"last30": l30_m.get("engagement_rate"),"prev30": p30_m.get("engagement_rate"),"mom": mom.get("engagement_rate")}}}
    return live
def main():
    today=date.today(); end=today - timedelta(days=1); start=CONSOLIDATION_START
    last30_start=end - timedelta(days=29); prev30_end=last30_start - timedelta(days=1); prev30_start=prev30_end - timedelta(days=29)
    ytd_start=date(today.year,1,1)
    access_token=google_access_token(AIROCIDE["google_profile"])
    print(f"TOTAL: {start}->{end} | MoM: {last30_start}->{end} vs {prev30_start}->{prev30_end}")
    refresh_summary={"client_slug": "airocide-systems","client_name": AIROCIDE["display_name"],"domain": AIROCIDE["search_atlas_domain"],"brand_consolidation_start": CONSOLIDATION_START.isoformat(),"refreshed_at": datetime.now(timezone.utc).isoformat(),"period": {"start": start.isoformat(), "end": end.isoformat()},"mom_period": {"last30": {"start": last30_start.isoformat(), "end": end.isoformat()},"prev30": {"start": prev30_start.isoformat(), "end": prev30_end.isoformat()}},"ytd_period": {"start": ytd_start.isoformat(), "end": end.isoformat()},"sources": {"ga4": "connected","meta_ads": "available_but_not_used","search_atlas": "connected_read_only","google_ads": "not_configured","search_console": "connected"}}
    main_ga4=refresh_ga4_property(access_token, AIROCIDE["ga4_property_id"], start.isoformat(), end.isoformat())
    last30=refresh_ga4_property(access_token, AIROCIDE["ga4_property_id"], last30_start.isoformat(), end.isoformat())
    prev30=refresh_ga4_property(access_token, AIROCIDE["ga4_property_id"], prev30_start.isoformat(), prev30_end.isoformat())
    main_ga4_ytd=refresh_ga4_property(access_token, AIROCIDE["ga4_property_id"], ytd_start.isoformat(), end.isoformat())
    ga4_channels=refresh_ga4_channels(access_token, AIROCIDE["ga4_property_id"], start.isoformat(), end.isoformat())
    ga4_hostname=refresh_ga4_hostname_breakout(access_token, AIROCIDE["ga4_property_id"], start.isoformat(), end.isoformat())
    additional={name: refresh_ga4_property(access_token, pid, start.isoformat(), end.isoformat()) for name,pid in AIROCIDE["additional_ga4_properties"].items()}
    search_console=refresh_search_console(access_token, start.isoformat(), end.isoformat()); atlas=refresh_search_atlas()
    save("refresh_summary.json", refresh_summary); save("ga4.json", main_ga4); save("ga4_last30.json", last30); save("ga4_prev30.json", prev30); save("ga4_ytd.json", main_ga4_ytd); save("ga4_channels.json", {"period": refresh_summary["period"], "rows": ga4_channels.get("rows") or [], "raw": ga4_channels}); save("ga4_hostname.json", ga4_hostname); save("ga4_additional.json", additional); save("search_console.json", search_console); save("search_atlas.json", atlas)
    live=build_live_json(main_ga4, last30, prev30, ga4_channels, search_console, atlas, refresh_summary["period"], refresh_summary["mom_period"])
    save("live.json", live)
    for target in LIVE_TARGETS: target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(live, indent=2, sort_keys=True), encoding="utf-8"); print(f"Wrote {target}")
    print(json.dumps(refresh_summary, indent=2, sort_keys=True)); print(f"Live ready: {live['cards']['sessions']}")
if __name__=="__main__": main()
