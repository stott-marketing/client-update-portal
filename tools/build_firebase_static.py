from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIREBASE_DIR = ROOT / "firebase-static"


def run(script: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "tools" / script)], cwd=ROOT, check=True)


def write_firebase_config() -> None:
    FIREBASE_DIR.mkdir(parents=True, exist_ok=True)
    (FIREBASE_DIR / "firebase.json").write_text(
        '{\n'
        '  "hosting": {\n'
        '    "site": "stott-mktg-client-update-data",\n'
        '    "public": "public",\n'
        '    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],\n'
        '    "cleanUrls": true\n'
        '  }\n'
        '}\n',
        encoding="utf-8",
    )
    (FIREBASE_DIR / ".firebaserc").write_text(
        '{\n  "projects": { "default": "stott-mktg-client-update-data" }\n}\n',
        encoding="utf-8",
    )


def main() -> None:
    run("build_sjawc_static.py")
    run("build_punch_club_static.py")
    run("build_sjawc_meeting_report.py")
    run("build_z4b_report.py")
    run("build_airocide_report.py")
    run("build_owner_workspace.py")
    write_firebase_config()
    print("Assembled Firebase static deploy folder")


if __name__ == "__main__":
    main()
