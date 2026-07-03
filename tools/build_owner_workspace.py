from __future__ import annotations

import shutil
from pathlib import Path


SOURCE = Path("owner-workspace")
OUT = Path("firebase-static/public")


def copy_file(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Required owner workspace source not found: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def main() -> None:
    copy_file(SOURCE / "manage" / "index.html", OUT / "manage" / "index.html")
    copy_file(SOURCE / "assets" / "stott-marketing-logo.png", OUT / "assets" / "stott-marketing-logo.png")
    print("Wrote owner workspace to firebase-static/public")


if __name__ == "__main__":
    main()
