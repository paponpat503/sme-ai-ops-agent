from concurrent.futures import ThreadPoolExecutor

from app.telemetry import configure_telemetry, get_tracer


def test_telemetry_configuration_is_thread_safe():
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: (configure_telemetry(), get_tracer()), range(32)))
    assert all(tracer is not None for _, tracer in results)
