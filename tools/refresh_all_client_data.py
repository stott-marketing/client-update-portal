from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"


def run_refresh(script: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "script": script,
        "status": "ok" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "stdout": result.stdout[-6000:],
        "stderr": result.stderr[-6000:],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    facebook_ads = run_refresh("refresh_facebook_ads_data.py")
    summary = {
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "clients": {
            "st-johns-aesthetics": run_refresh("refresh_sjawc_data.py"),
            "zincs-for-boats": run_refresh("refresh_z4b_data.py"),
            "airocide": run_refresh("refresh_airocide_data.py"),
            "punch-club": run_refresh("refresh_facebook_ads_data.py"),
        },
        "shared_sources": {
            "facebook_ads": {
                **facebook_ads,
                "note": "Config-driven per-client Meta Ads refresh. Missing config means no Facebook Ads clients are mapped yet.",
            }
        },
    }
    (OUT / "refresh_all_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
