#!/usr/bin/env python3
"""Pull Strava activities (recorded on Apple Watch) into data/cardio/activities.csv.

One-time setup:
    1. Create an app at https://www.strava.com/settings/api
       (Authorization Callback Domain: localhost)
    2. Put STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env
    3. python3 scripts/strava_sync.py --auth

Then:
    python3 scripts/strava_sync.py             # new activities since the last one stored
    python3 scripts/strava_sync.py --days 90   # backfill the last 90 days
    python3 scripts/strava_sync.py --streams ID  # per-second HR/pace for one activity -> JSON
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

from common import CARDIO_CSV, DATA, fmt_num, rel, require_private, load_env, read_csv, set_env, write_csv

API = "https://www.strava.com/api/v3"
PORT = 8721


def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get(path, token, params=None):
    url = f"{API}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def require(env, *keys):
    missing = [k for k in keys if not env.get(k)]
    if missing:
        sys.exit(f"Missing {', '.join(missing)} in .env — see .env.example")


def authorize(env):
    require(env, "STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET")
    redirect = f"http://localhost:{PORT}/callback"
    url = "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode({
        "client_id": env["STRAVA_CLIENT_ID"], "redirect_uri": redirect, "response_type": "code",
        "approval_prompt": "auto", "scope": "read,activity:read_all",
    })
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result["code"] = q.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Strava connected. You can close this tab.")

        def log_message(self, *a):
            pass

    print(f"Opening Strava to authorize. If nothing opens, visit:\n{url}\n")
    webbrowser.open(url)
    HTTPServer(("localhost", PORT), Handler).handle_request()
    if not result.get("code"):
        sys.exit("Authorization was cancelled.")
    tok = post("https://www.strava.com/oauth/token", {
        "client_id": env["STRAVA_CLIENT_ID"], "client_secret": env["STRAVA_CLIENT_SECRET"],
        "code": result["code"], "grant_type": "authorization_code",
    })
    set_env("STRAVA_REFRESH_TOKEN", tok["refresh_token"])
    print(f"Connected as {tok.get('athlete', {}).get('firstname', 'athlete')}. Refresh token saved to .env")


def access_token(env):
    require(env, "STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN")
    tok = post("https://www.strava.com/oauth/token", {
        "client_id": env["STRAVA_CLIENT_ID"], "client_secret": env["STRAVA_CLIENT_SECRET"],
        "refresh_token": env["STRAVA_REFRESH_TOKEN"], "grant_type": "refresh_token",
    })
    if tok.get("refresh_token") and tok["refresh_token"] != env["STRAVA_REFRESH_TOKEN"]:
        set_env("STRAVA_REFRESH_TOKEN", tok["refresh_token"])
    return tok["access_token"]


def to_row(a):
    km = a.get("distance", 0) / 1000
    moving_min = a.get("moving_time", 0) / 60
    local = a.get("start_date_local", "")  # e.g. 2026-10-30T07:12:45Z (already local time)
    return {
        "date": local[:10],
        "start_time": local[11:16],
        "strava_id": str(a["id"]),
        "type": a.get("sport_type") or a.get("type", ""),
        "name": a.get("name", ""),
        "distance_km": fmt_num(km, 2),
        "moving_min": fmt_num(moving_min, 1),
        "pace_min_per_km": fmt_num(moving_min / km, 2) if km > 0.1 else "",
        "avg_hr": fmt_num(a.get("average_heartrate"), 0),
        "max_hr": fmt_num(a.get("max_heartrate"), 0),
        "elev_gain_m": fmt_num(a.get("total_elevation_gain"), 0),
        "suffer_score": fmt_num(a.get("suffer_score"), 0),
    }


def sync(env, days):
    token = access_token(env)
    rows = read_csv(CARDIO_CSV)
    known = {r["strava_id"] for r in rows}
    if days:
        after = datetime.now(timezone.utc) - timedelta(days=days)
    elif rows:
        after = datetime.fromisoformat(max(r["date"] for r in rows)).replace(tzinfo=timezone.utc) - timedelta(days=1)
    else:
        after = datetime.now(timezone.utc) - timedelta(days=28)

    new, page = [], 1
    while True:
        batch = get("/athlete/activities", token, {"after": int(after.timestamp()), "per_page": 100, "page": page})
        if not batch:
            break
        new += [to_row(a) for a in batch if str(a["id"]) not in known]
        page += 1

    if not new:
        print("No new activities.")
        return
    rows = sorted(rows + new, key=lambda r: (r["date"], r["start_time"]))
    write_csv(CARDIO_CSV, rows)
    for r in new:
        print(f"  {r['date']} {r['type']:<10} {r['distance_km']:>6} km  {r['moving_min']:>6} min  HR {r['avg_hr'] or '-'}  {r['name']}")
    print(f"{len(new)} new activities → {rel(CARDIO_CSV)}")


def streams(env, activity_id):
    token = access_token(env)
    data = get(f"/activities/{activity_id}/streams", token,
               {"keys": "time,distance,heartrate,velocity_smooth,cadence,altitude", "key_by_type": "true"})
    out = DATA / "cardio" / "streams" / f"{activity_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data), encoding="utf-8")
    print(f"Saved per-second streams → {rel(out)}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--auth", action="store_true", help="connect your Strava account (once)")
    p.add_argument("--days", type=int, help="backfill this many days")
    p.add_argument("--streams", metavar="ACTIVITY_ID", help="download per-second data for one activity")
    args = p.parse_args()
    env = load_env()
    if args.auth:
        authorize(env)
    elif args.streams:
        require_private()
        streams(env, args.streams)
    else:
        require_private()
        sync(env, args.days)


if __name__ == "__main__":
    main()
