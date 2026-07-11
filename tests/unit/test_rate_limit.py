from concurrent.futures import ThreadPoolExecutor

from app.rate_limit import SlidingWindowRateLimiter


def test_sliding_window_allows_requests_after_expiry():
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10, max_clients=100)
    assert limiter.check("client", now=0).allowed
    assert limiter.check("client", now=1).allowed
    blocked = limiter.check("client", now=2)
    assert not blocked.allowed
    assert blocked.retry_after_seconds == 8
    assert limiter.check("client", now=11).allowed


def test_client_tracking_is_bounded():
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, max_clients=100)
    for index in range(500):
        limiter.check(f"client-{index}", now=0)
    assert limiter.tracked_clients == 100


def test_limiter_is_thread_safe():
    limiter = SlidingWindowRateLimiter(limit=10, window_seconds=60, max_clients=100)
    with ThreadPoolExecutor(max_workers=20) as pool:
        decisions = list(pool.map(lambda _: limiter.check("shared", now=1), range(100)))
    assert sum(decision.allowed for decision in decisions) == 10
