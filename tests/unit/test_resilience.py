import pytest

from app.resilience import CircuitBreaker, CircuitOpenError, RetryPolicy, call_with_retry


def test_transient_failure_retries_then_succeeds():
    attempts = []
    def operation():
        attempts.append(1)
        if len(attempts) < 3:
            raise TimeoutError("temporary")
        return "ok"
    result = call_with_retry(
        operation,
        policy=RetryPolicy(max_retries=2, base_delay_seconds=0),
        breaker=CircuitBreaker(),
        is_retryable=lambda exc: isinstance(exc, TimeoutError),
        sleep=lambda _: None,
    )
    assert result == "ok"
    assert len(attempts) == 3


def test_non_retryable_failure_opens_circuit_at_threshold():
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=60)
    for _ in range(2):
        with pytest.raises(ValueError):
            call_with_retry(
                lambda: (_ for _ in ()).throw(ValueError("bad")),
                policy=RetryPolicy(max_retries=3, base_delay_seconds=0),
                breaker=breaker,
                is_retryable=lambda _: False,
                sleep=lambda _: None,
            )
    with pytest.raises(CircuitOpenError):
        breaker.before_call()


def test_exhausted_transient_call_counts_one_circuit_failure():
    breaker = CircuitBreaker(failure_threshold=2)
    with pytest.raises(TimeoutError):
        call_with_retry(
            lambda: (_ for _ in ()).throw(TimeoutError("down")),
            policy=RetryPolicy(max_retries=2, base_delay_seconds=0),
            breaker=breaker,
            is_retryable=lambda _: True,
            sleep=lambda _: None,
        )
    assert breaker.failures == 1
