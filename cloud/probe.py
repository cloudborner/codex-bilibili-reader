"""Bounded public read probe; does not use local account credentials."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> int:
    # An empty, temporary home prevents browser or stored credential discovery.
    with tempfile.TemporaryDirectory(prefix="bili-public-probe-") as isolated_home:
        env = dict(os.environ, HOME=isolated_home, USERPROFILE=isolated_home,
                   PYTHONIOENCODING="utf-8")
        checks = {}
        commands = {
            "video": ["video", "BV1d8pU6xEZX", "--json"],
            "search": ["search", "DeepSeek Harness", "--type", "video", "--max", "2", "--json"],
        }
        for name, args in commands.items():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "bili_cli.cli", *args], env=env,
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45,
                )
                try:
                    payload = json.loads(result.stdout)
                except ValueError:
                    payload = {}
                data = payload.get("data")
                has_content = bool(data.get("video", {}).get("bvid")) if name == "video" and isinstance(data, dict) else bool(data)
                checks[name] = {
                    "exit_code": result.returncode,
                    "ok": result.returncode == 0 and payload.get("ok") is True and has_content,
                    "has_content": has_content,
                    "error_code": payload.get("error", {}).get("code"),
                }
            except subprocess.TimeoutExpired:
                checks[name] = {"ok": False, "error_code": "timeout"}
        report = {"scope": "public reads only; no login or subtitles tested", "checks": checks}
        out = Path(__file__).resolve().parent / "probe-result.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if all(c["ok"] for c in checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
