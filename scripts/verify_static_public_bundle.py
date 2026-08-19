from __future__ import annotations

import argparse
from pathlib import Path

FORBIDDEN = (
    b"subscriber_token",
    b"/api/v1/subscribers",
    b"/api/v1/scenario",
    b"model_score",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the static public bundle boundary.")
    parser.add_argument("--dist", type=Path, default=Path("web/dist"))
    arguments = parser.parse_args()
    files = [path for path in arguments.dist.rglob("*") if path.is_file()]
    if not files:
        raise SystemExit("Static public bundle is empty")
    findings = [
        f"{path}: {token.decode()}"
        for path in files
        for token in FORBIDDEN
        if token in path.read_bytes()
    ]
    if findings:
        raise SystemExit("Forbidden private content in static bundle:\n" + "\n".join(findings))
    print(f"static_public_bundle=passed files={len(files)} forbidden_matches=0")


if __name__ == "__main__":
    main()
