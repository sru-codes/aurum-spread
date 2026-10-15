"""Run Caddy and the Python API as supervised processes in one Railway container."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def main() -> int:
    stopping = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    api = subprocess.Popen(["python3", "-u", "/app/analytics/server.py"], env=os.environ.copy())
    caddy = subprocess.Popen(
        ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"],
        env=os.environ.copy(),
    )
    processes = (api, caddy)
    try:
        while not stopping:
            for process in processes:
                status = process.poll()
                if status is not None:
                    return status or 1
            time.sleep(0.25)
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        deadline = time.monotonic() + 10
        for process in processes:
            if process.poll() is None:
                try:
                    process.wait(timeout=max(0.1, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
