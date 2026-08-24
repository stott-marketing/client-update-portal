from __future__ import annotations
import json, os, subprocess, urllib.parse, urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sjawc"
CONFIG = Path.home() / ".config" / "stott-marketing"
SJAWC = {"slug": "st-johns-aesthetics","ga4_property_id": "309158748","google_profile": "sjawc-michaelrstott","google_ads_customer_id":"1778140560","meta_ad_account_id":"983492348722531","ghl_location_id":"Efay365CqUELKItt9nyN","search_atlas_domain":"sjawc.com"}
LIVE_TARGETS = [ROOT / "firebase-static" / "public" / "st-johns-aesthetics" / "data" / "live.json", ROOT / "client-update-portal" / "public" / "st-johns-aesthetics" / "data" / "live.json"]
def request_json(url, *, method="GET", headers=None, body=None):
    h=dict(headers or {}); d=None
    if body is not None: d=json.dumps(body).encode("utf-8"); h["Content-Type"]="application/json"
    req=urllib.request.Request(url, data=d, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode("utf-8"))
def request_json_curl(url, *, method="GET", headers=None, body=None):
    cmd=["curl","-sS","-X",method]
    for k,v in (headers or {}).items(): cmd.extend(["-H",f"{k}: {v}"])
    if body is not None: cmd.extend(["-H","Content-Type: application/json","--data-binary",json.dumps(body)])
    cmd.append(url)
    result=subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout or "{}")
def save(name,data): OUT.mkdir(parents=True, exist_ok=True); (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
def read_json_env(name): v=os.getenv(name); return json.loads(v) if v else None
def read_text(path: Path) -> str: return path.read_text(encoding="utf-8").strip()
def google_access_token(profile: str) -> str:
    token = read_json_env("SJAWC_GOOGLE_TOKEN_JSON") or read_json_env("GOOGLE_TOKEN_JSON")
    client = read_json_env("GOOGLE_OAUTH_CLIENT_JSON")
    if token and client:
        cd = client.get("installed") or client.get("web") or client
        payload = urllib.parse.urlencode({"client_id": cd["client_id"],"client_secret": cd["client_secret"],"refresh_token": token["refresh_token"],"grant_type": "refresh_token"}).encode()
        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=payload, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read().decode())["access_token"]
    token_path = CONFIG / "google-data" / "tokens" / f"{profile}.json"
    token_data = json.loads(token_path.read_text(encoding="utf-8"))
    refresh = token_data.get("refresh_token")
    cid = token_data.get("client_id"); csec = token_data.get("client_secret")
    if not cid:
        client_path = CONFIG / "ga4-oauth-client.json"
        client_data = json.loads(client_path.read_text(encoding="utf-8"))
        cd = client_data.get("installed") or client_data.get("web") or client_data
        cid = cd.get("client_id"); csec = cd.get("client_secret")
    payload = urllib.parse.urlencode({"client_id": cid,"client_secret": csec,"refresh_token": refresh,"grant_type": "refresh_token"}).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=payload, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        if "access_token" not in data:
            print(f"TOKEN ERROR: {data}"); raise RuntimeError(f"Token refresh failed: {data}")
        token_data["token"] = data["access_token"]
        token_data["expiry"] = (datetime.now(timezone.utc)+timedelta(seconds=data.get("expires_in",3600))).isoformat()
        token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
        return data["access_token"]
def refresh_ga4(at,s,e):
    url=f"https://analyticsdata.googleapis.com/v1beta/properties/{SJAWC['ga4_property_id']}:runReport"
    body={"dateRanges":[{"startDate":s,"endDate":e}],"metrics":[{"name":"activeUsers"},{"name":"sessions"},{"name":"newUsers"},{"name":"engagementRate"},{"name":"keyEvents"},{"name":"totalRevenue"}]}
    raw=request_json(url, method="POST", headers={"Authorization":f"Bearer {at}"}, body=body)
    vals=[v.get("value") for v in raw.get("rows",[{}])[0].get("metricValues",[])]; keys=["active_users","sessions","new_users","engagement_rate","key_events","total_revenue"]
    return {"period":{"start":s,"end":e},"metrics":dict(zip(keys,vals))}
def refresh_ga4_channels(at,s,e):
    url=f"https://analyticsdata.googleapis.com/v1beta/properties/{SJAWC['ga4_property_id']}:runReport"
    body={"dateRanges":[{"startDate":s,"endDate":e}],"dimensions":[{"name":"sessionDefaultChannelGroup"}],"metrics":[{"name":"sessions"},{"name":"activeUsers"},{"name":"keyEvents"}],"orderBys":[{"metric":{"metricName":"sessions"},"desc":True}],"limit":12}
    return request_json(url, method="POST", headers={"Authorization":f"Bearer {at}"}, body=body)
def refresh_ga4_key_events(at,s,e):
    url=f"https://analyticsdata.googleapis.com/v1beta/properties/{SJAWC['ga4_property_id']}:runReport"
    body={"dateRanges":[{"startDate":s,"endDate":e}],"dimensions":[{"name":"eventName"}],"metrics":[{"name":"keyEvents"},{"name":"eventCount"}],"orderBys":[{"metric":{"metricName":"keyEvents"},"desc":True}],"limit":25}
    return request_json(url, method="POST", headers={"Authorization":f"Bearer {at}"}, body=body)
def refresh_organic_content(at,s,e):
    url=f"https://analyticsdata.googleapis.com/v1beta/properties/{SJAWC['ga4_property_id']}:runReport"
    def run(body): return request_json(url, method="POST", headers={"Authorization":f"Bearer {at}"}, body=body)
    organic_filter={"filter":{"fieldName":"sessionDefaultChannelGroup","stringFilter":{"matchType":"EXACT","value":"Organic Search"}}}
    content_filter={"filter":{"fieldName":"pagePath","stringFilter":{"matchType":"CONTAINS","value":"/blog/"}}}
    organic_landing_pages=run({"dateRanges":[{"startDate":s,"endDate":e}],"dimensions":[{"name":"landingPagePlusQueryString"}],"metrics":[{"name":"sessions"},{"name":"activeUsers"},{"name":"engagementRate"},{"name":"keyEvents"}],"dimensionFilter":organic_filter,"orderBys":[{"metric":{"metricName":"sessions"},"desc":True}],"limit":12})
    content_pages=run({"dateRanges":[{"startDate":s,"endDate":e}],"dimensions":[{"name":"pagePath"},{"name":"pageTitle"}],"metrics":[{"name":"screenPageViews"},{"name":"activeUsers"},{"name":"engagementRate"}],"dimensionFilter":content_filter,"orderBys":[{"metric":{"metricName":"screenPageViews"},"desc":True}],"limit":12})
    organic_aggregate=run({"dateRanges":[{"startDate":s,"endDate":e}],"metrics":[{"name":"sessions"},{"name":"activeUsers"},{"name":"engagementRate"},{"name":"keyEvents"}],"dimensionFilter":organic_filter})
    content_aggregate=run({"dateRanges":[{"startDate":s,"endDate":e}],"metrics":[{"name":"screenPageViews"},{"name":"activeUsers"},{"name":"engagementRate"}],"dimensionFilter":content_filter})
    return {"period":{"start":s,"end":e},"organic_landing_pages":organic_landing_pages,"content_pages":content_pages,"organic_aggregate":organic_aggregate,"content_aggregate":content_aggregate}
def refresh_google_ads(at,s,e):
    ads_config=read_json_env("GOOGLE_ADS_CONFIG_JSON") or json.loads((CONFIG / "google-data" / "google-ads.json").read_text(encoding="utf-8"))
    query=f"""SELECT metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.average_cpc FROM customer WHERE segments.date BETWEEN '{s}' AND '{e}'"""
    headers={"Authorization":f"Bearer {at}","developer-token":ads_config["developer_token"],"login-customer-id":ads_config.get("manager_customer_id","").replace("-","")}
    last_error=None; raw=None; used=None
    for version in ["v22"]:
        try:
            candidate=request_json_curl(f"https://googleads.googleapis.com/{version}/customers/{SJAWC['google_ads_customer_id']}/googleAds:searchStream", method="POST", headers=headers, body={"query":query})
            if isinstance(candidate, list) and candidate and isinstance(candidate[0], dict) and candidate[0].get("error"):
                raise RuntimeError(candidate[0]["error"].get("message") or candidate[0]["error"])
            raw=candidate; used=version; break
        except Exception as exc:
            last_error=exc
    if raw is None: raise RuntimeError(f"Google Ads request failed: {last_error}")
    totals=Counter(); avg_cpc_micros=0
    for batch in raw if isinstance(raw,list) else []:
        for row in batch.get("results",[]):
            metrics=row.get("metrics",{})
            totals["cost_micros"]+=int(float(metrics.get("costMicros",0) or 0))
            totals["impressions"]+=int(float(metrics.get("impressions",0) or 0))
            totals["clicks"]+=int(float(metrics.get("clicks",0) or 0))
            totals["conversions"]+=float(metrics.get("conversions",0) or 0)
            if metrics.get("averageCpc"): avg_cpc_micros=int(float(metrics["averageCpc"]))
    spend=totals["cost_micros"]/1_000_000
    return {"period":{"start":s,"end":e},"api_version":used,"raw_batches":len(raw) if isinstance(raw,list) else 0,"metrics":{"spend":spend,"impressions":totals["impressions"],"clicks":totals["clicks"],"conversions":totals["conversions"],"average_cpc":avg_cpc_micros/1_000_000,"cost_per_conversion":spend/totals["conversions"] if totals["conversions"] else 0}}
def refresh_meta(s,e):
    token=(
        os.getenv("SJAWC_META_ACCESS_TOKEN")
        or os.getenv("SJAWC_META_TOKEN")
        or os.getenv("META_ACCESS_TOKEN")
        or os.getenv("FACEBOOK_ACCESS_TOKEN")
        or read_text(CONFIG / "meta-data" / "tokens" / "michaelrstott.txt")
    )
    account="act_" + SJAWC["meta_ad_account_id"]
    params=urllib.parse.urlencode({"fields":"spend,impressions,clicks,reach,cpc,ctr,actions","time_range":json.dumps({"since":s,"until":e}),"access_token":token})
    raw=request_json(f"https://graph.facebook.com/v23.0/{account}/insights?{params}")
    row=(raw.get("data") or [{}])[0]
    actions={a.get("action_type"):float(a.get("value",0) or 0) for a in row.get("actions",[])}
    leads=actions.get("lead",0) or actions.get("onsite_conversion.lead_grouped",0)
    return {"period":{"start":s,"end":e},"metrics":{"spend":float(row.get("spend",0) or 0),"impressions":int(float(row.get("impressions",0) or 0)),"clicks":int(float(row.get("clicks",0) or 0)),"reach":int(float(row.get("reach",0) or 0)),"cpc":float(row.get("cpc",0) or 0),"ctr":float(row.get("ctr",0) or 0),"leads":leads,"link_clicks":actions.get("link_click",0),"video_views":actions.get("video_view",0)},"raw":raw}
def refresh_ghl(ytd_start):
    token=(os.getenv("SJAWC_GHL_TOKEN") or os.getenv("SJAWC_GHL_ACCESS_TOKEN") or os.getenv("GHL_ACCESS_TOKEN") or read_text(CONFIG / "ghl-data" / "tokens" / "sjawc.txt"))
    location_id=SJAWC["ghl_location_id"]; headers={"Authorization":f"Bearer {token}","Version":"2021-07-28"}
    loc=request_json_curl(f"https://services.leadconnectorhq.com/locations/{location_id}", headers=headers)
    pipelines=request_json_curl(f"https://services.leadconnectorhq.com/opportunities/pipelines?{urllib.parse.urlencode({'locationId':location_id})}", headers=headers)
    pipeline_names={p["id"]:p.get("name") or p["id"] for p in pipelines.get("pipelines",[])}
    stage_names={s["id"]:s.get("name") or s["id"] for p in pipelines.get("pipelines",[]) for s in p.get("stages",[])}
    all_opps=[]; start_after=None; start_after_id=None
    while True:
        params={"location_id":location_id,"limit":"100"}
        if start_after and start_after_id:
            params["startAfter"]=str(start_after); params["startAfterId"]=start_after_id
        data=request_json_curl("https://services.leadconnectorhq.com/opportunities/search?"+urllib.parse.urlencode(params), headers=headers)
        opps=data.get("opportunities",[]); all_opps.extend(opps)
        meta=data.get("meta") or {}; start_after=meta.get("startAfter"); start_after_id=meta.get("startAfterId")
        if not opps or not start_after or not start_after_id: break
    ytd=[o for o in all_opps if (o.get("createdAt") or "")[:10] >= ytd_start]
    facebook=[o for o in ytd if pipeline_names.get(o.get("pipelineId"),o.get("pipelineId")) == "Facebook Form Submission"]
    appointment_stages={"Booked Appointment","Showed - Appointment"}
    appointment_count=sum(1 for o in facebook if stage_names.get(o.get("pipelineStageId"),o.get("pipelineStageId")) in appointment_stages)
    return {"location":{"name":(loc.get("location") or {}).get("name"),"logoUrl":(loc.get("location") or {}).get("logoUrl")},"period":{"start":ytd_start},"metrics":{"total_opportunities":len(all_opps),"ytd_opportunities":len(ytd),"facebook_ytd":{"opportunities":len(facebook),"appointment_stage_opportunities":appointment_count,"by_stage":dict(Counter(stage_names.get(o.get("pipelineStageId"),o.get("pipelineStageId") or "Unknown") for o in facebook).most_common())},"by_status":dict(Counter(o.get("status") or "Unknown" for o in all_opps).most_common()),"by_source":dict(Counter(o.get("source") or "Unknown" for o in all_opps).most_common()),"by_pipeline":dict(Counter(pipeline_names.get(o.get("pipelineId"),o.get("pipelineId") or "Unknown") for o in all_opps).most_common()),"by_stage":dict(Counter(stage_names.get(o.get("pipelineStageId"),o.get("pipelineStageId") or "Unknown") for o in all_opps).most_common())}}
def refresh_search_atlas():
    key=os.getenv("SEARCH_ATLAS_API_KEY") or os.getenv("SJAWC_SEARCH_ATLAS_KEY") or read_text(CONFIG / "search-atlas" / "tokens" / "search-atlas-key.txt")
    data=request_json_curl("https://api.searchatlas.com/api/customer/projects/projects/", headers={"X-API-Key":key})
    projects=data.get("results") or data.get("data") or []
    project=next((p for p in projects if p.get("domain_url")==SJAWC["search_atlas_domain"]), None)
    if not project: raise RuntimeError("Search Atlas project not found for sjawc.com")
    se=((project.get("data_v2") or {}).get("se") or {}); sa=((project.get("data_v2") or {}).get("sa") or {}); otto=((project.get("data_v2") or {}).get("otto_v2") or {}); llm=((project.get("data_v2") or {}).get("llmv") or {})
    return {"project_id":project.get("id"),"domain":project.get("domain_url"),"ai_summary":project.get("ai_summary"),"metrics":{"site_health":sa.get("health"),"domain_power":se.get("domain_power"),"domain_rating":se.get("domain_rating"),"domain_authority":se.get("domain_authority"),"organic_traffic":se.get("organic_traffic") or se.get("traffic"),"traffic_change":se.get("traffic_change"),"traffic_change_percent":se.get("traffic_change_percent"),"keyword_count":se.get("keyword_count") or se.get("organic_keywords"),"keyword_count_change":se.get("keyword_count_change"),"keyword_count_change_percent":se.get("keyword_count_change_percent"),"top_3_keywords_count":se.get("top_3_keywords_count"),"refdomain_count":se.get("refdomain_count") or se.get("refdomains"),"refdomain_new_count":se.get("refdomain_new_count"),"refdomain_lost_count":se.get("refdomain_lost_count"),"backlinks":se.get("backlinks"),"spam_score":se.get("spam_score"),"otto_score":otto.get("seo_optimization_score"),"otto_total_deployed_fixes":otto.get("total_deployed_fixes"),"otto_total_time_saved":otto.get("total_time_saved"),"llm_current_mentions":llm.get("current_mentions"),"llm_previous_mentions":llm.get("previous_mentions")}}
def calc_mom(c,p):
    try: cf=float(c or 0); pf=float(p or 0); return None if pf==0 else round((cf-pf)/pf*100,1)
    except: return None
def main():
    today=date.today(); end=today-timedelta(days=1)
    last30_start=end-timedelta(days=29); prev30_end=last30_start-timedelta(days=1); prev30_start=prev30_end-timedelta(days=29)
    first_this_month=date(today.year,today.month,1); last_month_end=first_this_month-timedelta(days=1); last_month_start=date(last_month_end.year,last_month_end.month,1)
    prev_month_end=last_month_start-timedelta(days=1); prev_month_start=date(prev_month_end.year,prev_month_end.month,1)
    q=(today.month-1)//3; this_q_start=date(today.year,q*3+1,1); last_q_end=this_q_start-timedelta(days=1); lq=(last_q_end.month-1)//3; last_q_start=date(last_q_end.year,lq*3+1,1)
    prev_q_end=last_q_start-timedelta(days=1); pq=(prev_q_end.month-1)//3; prev_q_start=date(prev_q_end.year,pq*3+1,1)
    ytd_start=date(today.year,1,1)
    print(f"Refreshing SJAWC {last30_start}->{end} vs {prev30_start}->{prev30_end}")
    at=google_access_token(SJAWC["google_profile"]); print(f"Token ok {at[:20]}...")
    fetch={"last30":(last30_start.isoformat(),end.isoformat()),"prev30":(prev30_start.isoformat(),prev30_end.isoformat()),"lastMonth":(last_month_start.isoformat(),last_month_end.isoformat()),"prevMonth":(prev_month_start.isoformat(),prev_month_end.isoformat()),"lastQuarter":(last_q_start.isoformat(),last_q_end.isoformat()),"prevQuarter":(prev_q_start.isoformat(),prev_q_end.isoformat()),"ytd":(ytd_start.isoformat(),end.isoformat())}
    allp={}
    for k,(s,e) in fetch.items():
        allp[k]=refresh_ga4(at,s,e); save(f"ga4_{k}.json", allp[k]); print(f" GA4 {k} {s}->{e} ok")
    ch=refresh_ga4_channels(at,last30_start.isoformat(),end.isoformat()); save("ga4_channels.json", ch)
    key_events=refresh_ga4_key_events(at,last30_start.isoformat(),end.isoformat()); save("ga4_key_events.json", key_events)
    prev_key_events=refresh_ga4_key_events(at,prev30_start.isoformat(),prev30_end.isoformat()); save("ga4_key_events_prev30.json", prev_key_events)
    def m(n): return allp.get(n,{}).get("metrics",{})
    mom={k:calc_mom(m("last30").get(k), m("prev30").get(k)) for k in m("last30").keys()}
    rows=[]
    for row in (ch.get("rows") or []):
        dim=(row.get("dimensionValues") or [{}])[0].get("value") or "Unknown"; vals=[v.get("value") for v in row.get("metricValues",[])]
        rows.append({"channel":dim,"sessions":vals[0] if len(vals)>0 else "0","active_users":vals[1] if len(vals)>1 else "0"})
    save("ga4.json", allp["last30"])
    organic=refresh_organic_content(at,last30_start.isoformat(),end.isoformat()); save("ga4_organic_content.json", organic)
    summary={"period":{"start":last30_start.isoformat(),"end":end.isoformat()},"ytd_period":{"start":ytd_start.isoformat(),"end":end.isoformat()},"manual_sources":{"workbook.json":"Boulevard matched revenue and ROAS remain manually supplied/static."},"refreshed":{"ga4.json":"ok","ga4_channels.json":"ok","ga4_key_events.json":"ok","ga4_key_events_prev30.json":"ok","ga4_organic_content.json":"ok","live.json":"ok"}}
    external_tasks={
        "google_ads.json": lambda: refresh_google_ads(at,last30_start.isoformat(),end.isoformat()),
        "meta.json": lambda: refresh_meta(last30_start.isoformat(),end.isoformat()),
        "ghl.json": lambda: refresh_ghl(ytd_start.isoformat()),
        "search_atlas.json": refresh_search_atlas,
    }
    for name, fn in external_tasks.items():
        try:
            save(name, fn()); summary["refreshed"][name]="ok"; print(f" {name} ok")
        except Exception as exc:
            summary["refreshed"][name]=f"{type(exc).__name__}: {exc}"; print(f" {name} failed: {exc}")
    save("refresh_summary.json", summary)
    live={"client_slug":SJAWC["slug"],"updatedAt":datetime.now(timezone.utc).isoformat(),"default_view":"last30_vs_prev30","periods":{"last30":{"label":"Last 30 days","start":allp["last30"]["period"]["start"],"end":allp["last30"]["period"]["end"],"metrics":m("last30")},"prev30":{"label":"Previous 30 days","start":allp["prev30"]["period"]["start"],"end":allp["prev30"]["period"]["end"],"metrics":m("prev30")},"lastMonth":{"label":"Last Month","start":allp["lastMonth"]["period"]["start"],"end":allp["lastMonth"]["period"]["end"],"metrics":m("lastMonth")},"prevMonth":{"label":"Previous Month","start":allp["prevMonth"]["period"]["start"],"end":allp["prevMonth"]["period"]["end"],"metrics":m("prevMonth")},"lastQuarter":{"label":"Last Quarter","start":allp["lastQuarter"]["period"]["start"],"end":allp["lastQuarter"]["period"]["end"],"metrics":m("lastQuarter")},"prevQuarter":{"label":"Previous Quarter","start":allp["prevQuarter"]["period"]["start"],"end":allp["prevQuarter"]["period"]["end"],"metrics":m("prevQuarter")},"ytd":{"label":"Year to Date","start":allp["ytd"]["period"]["start"],"end":allp["ytd"]["period"]["end"],"metrics":m("ytd")},},"comparisons":{"last30_vs_prev30":{"label":"Last 30 vs Prev 30","mom":mom}},"channels":rows,"cards":{"sessions":{"last30":m("last30").get("sessions"),"prev30":m("prev30").get("sessions"),"mom":mom.get("sessions"),"ytd":m("ytd").get("sessions")},"active_users":{"last30":m("last30").get("active_users"),"prev30":m("prev30").get("active_users"),"mom":mom.get("active_users")}}}
    save("live.json", live)
    for tgt in LIVE_TARGETS:
        tgt.parent.mkdir(parents=True, exist_ok=True); tgt.write_text(json.dumps(live, indent=2, sort_keys=True), encoding="utf-8"); print(f"Wrote {tgt}")
    print(f"Live ready SJAWC MoM {mom.get('sessions')}%")
if __name__=="__main__": main()
