from __future__ import annotations
import json, os, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sjawc"
CONFIG = Path.home() / ".config" / "stott-marketing"
SJAWC = {"slug": "st-johns-aesthetics","ga4_property_id": "309158748","google_profile": "sjawc-michaelrstott","meta_ad_account_id":"983492348722531"}
LIVE_TARGETS = [ROOT / "firebase-static" / "public" / "st-johns-aesthetics" / "data" / "live.json", ROOT / "client-update-portal" / "public" / "st-johns-aesthetics" / "data" / "live.json"]
def request_json(url, *, method="GET", headers=None, body=None):
    h=dict(headers or {}); d=None
    if body is not None: d=json.dumps(body).encode("utf-8"); h["Content-Type"]="application/json"
    req=urllib.request.Request(url, data=d, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read().decode("utf-8"))
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
    summary={"period":{"start":last30_start.isoformat(),"end":end.isoformat()},"refreshed":{"ga4.json":"ok","ga4_channels.json":"ok","ga4_key_events.json":"ok","ga4_key_events_prev30.json":"ok","live.json":"ok"}}
    try:
        meta=refresh_meta(last30_start.isoformat(),end.isoformat()); save("meta.json", meta); summary["refreshed"]["meta.json"]="ok"; print(" Meta ok")
    except Exception as exc:
        summary["refreshed"]["meta.json"]=f"{type(exc).__name__}: {exc}"; print(f" Meta failed: {exc}")
    save("refresh_summary.json", summary)
    live={"client_slug":SJAWC["slug"],"updatedAt":datetime.now(timezone.utc).isoformat(),"default_view":"last30_vs_prev30","periods":{"last30":{"label":"Last 30 days","start":allp["last30"]["period"]["start"],"end":allp["last30"]["period"]["end"],"metrics":m("last30")},"prev30":{"label":"Previous 30 days","start":allp["prev30"]["period"]["start"],"end":allp["prev30"]["period"]["end"],"metrics":m("prev30")},"lastMonth":{"label":"Last Month","start":allp["lastMonth"]["period"]["start"],"end":allp["lastMonth"]["period"]["end"],"metrics":m("lastMonth")},"prevMonth":{"label":"Previous Month","start":allp["prevMonth"]["period"]["start"],"end":allp["prevMonth"]["period"]["end"],"metrics":m("prevMonth")},"lastQuarter":{"label":"Last Quarter","start":allp["lastQuarter"]["period"]["start"],"end":allp["lastQuarter"]["period"]["end"],"metrics":m("lastQuarter")},"prevQuarter":{"label":"Previous Quarter","start":allp["prevQuarter"]["period"]["start"],"end":allp["prevQuarter"]["period"]["end"],"metrics":m("prevQuarter")},"ytd":{"label":"Year to Date","start":allp["ytd"]["period"]["start"],"end":allp["ytd"]["period"]["end"],"metrics":m("ytd")},},"comparisons":{"last30_vs_prev30":{"label":"Last 30 vs Prev 30","mom":mom}},"channels":rows,"cards":{"sessions":{"last30":m("last30").get("sessions"),"prev30":m("prev30").get("sessions"),"mom":mom.get("sessions"),"ytd":m("ytd").get("sessions")},"active_users":{"last30":m("last30").get("active_users"),"prev30":m("prev30").get("active_users"),"mom":mom.get("active_users")}}}
    save("live.json", live)
    for tgt in LIVE_TARGETS:
        tgt.parent.mkdir(parents=True, exist_ok=True); tgt.write_text(json.dumps(live, indent=2, sort_keys=True), encoding="utf-8"); print(f"Wrote {tgt}")
    print(f"Live ready SJAWC MoM {mom.get('sessions')}%")
if __name__=="__main__": main()
