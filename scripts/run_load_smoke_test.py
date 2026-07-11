from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app


def _request(_: int) -> int:
    with TestClient(app) as client:
        response = client.post("/agent/ask", json={"question": "Which customers need follow-up today?"})
        return response.status_code


def run(users: int = 5, requests: int = 25) -> bool:
    with ThreadPoolExecutor(max_workers=users) as pool:
        statuses = list(pool.map(_request, range(requests)))
    passed = all(status == 200 for status in statuses)
    print(f"load_smoke: {'PASS' if passed else 'FAIL'} ({requests} requests, {users} workers)")
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
