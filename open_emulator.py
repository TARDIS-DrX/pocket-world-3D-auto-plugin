from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()

    deadline = time.monotonic() + 30
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            config = json.loads(args.config.read_text(encoding="utf-8"))
            port = int(config["gateway"]["nx_main_port"])
            body = json.dumps(
                {
                    "action": "open",
                    "id": str(uuid.uuid4()),
                    "params": {"cmd": "-s true", "index": 1},
                }
            ).encode()
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/player",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            print(urllib.request.urlopen(request, timeout=5).read().decode())
            return
        except (OSError, ValueError, KeyError, urllib.error.URLError) as error:
            last_error = error
            time.sleep(0.5)
    raise RuntimeError(f"MuMu main process did not accept requests: {last_error}")


if __name__ == "__main__":
    main()
