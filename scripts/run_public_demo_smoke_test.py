from __future__ import annotations

import os

import httpx


def run() -> bool:
    base_url = os.getenv("PUBLIC_DEMO_URL", "").rstrip("/")
    if not base_url:
        raise SystemExit("Set PUBLIC_DEMO_URL to the deployed service URL.")
    with httpx.Client(base_url=base_url, timeout=30, follow_redirects=True) as client:
        live = client.get("/live")
        ready = client.get("/ready")
        demo = client.get("/demo")
    passed = live.status_code == 200 and ready.status_code == 200 and demo.status_code == 200 and "SME AI Ops Agent" in demo.text
    print(f"public_demo_smoke: {'PASS' if passed else 'FAIL'}")
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
