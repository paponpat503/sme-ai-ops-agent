from __future__ import annotations

import math
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int = 0


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: float, max_clients: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self._clients: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> RateLimitDecision:
        now = time.monotonic() if now is None else now
        with self._lock:
            window = self._clients.get(key)
            if window is None:
                if len(self._clients) >= self.max_clients:
                    self._clients.popitem(last=False)
                window = deque()
                self._clients[key] = window
            else:
                self._clients.move_to_end(key)

            cutoff = now - self.window_seconds
            while window and window[0] <= cutoff:
                window.popleft()
            if len(window) >= self.limit:
                retry_after = max(1, math.ceil(self.window_seconds - (now - window[0])))
                return RateLimitDecision(False, 0, retry_after)
            window.append(now)
            return RateLimitDecision(True, self.limit - len(window))

    @property
    def tracked_clients(self) -> int:
        with self._lock:
            return len(self._clients)
