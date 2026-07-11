from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from typing import Callable, TypeVar


T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    pass


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 2
    base_delay_seconds: float = 0.2
    max_delay_seconds: float = 2.0


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.opened_at: float | None = None
        self._lock = threading.Lock()

    def before_call(self) -> None:
        with self._lock:
            if self.opened_at is None:
                return
            if time.monotonic() - self.opened_at >= self.cooldown_seconds:
                self.opened_at = None
                self.failures = 0
                return
            raise CircuitOpenError("Dependency circuit is open.")

    def record_success(self) -> None:
        with self._lock:
            self.failures = 0
            self.opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.opened_at = time.monotonic()


def call_with_retry(
    operation: Callable[[], T],
    *,
    policy: RetryPolicy,
    breaker: CircuitBreaker,
    is_retryable: Callable[[Exception], bool],
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    breaker.before_call()
    for attempt in range(policy.max_retries + 1):
        try:
            result = operation()
            breaker.record_success()
            return result
        except Exception as exc:
            if not is_retryable(exc):
                breaker.record_failure()
                raise
            if attempt >= policy.max_retries:
                breaker.record_failure()
                raise
            delay = min(policy.max_delay_seconds, policy.base_delay_seconds * (2**attempt))
            sleep(delay * (0.8 + random.random() * 0.4))
    raise AssertionError("Retry loop exhausted unexpectedly.")
