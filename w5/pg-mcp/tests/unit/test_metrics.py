"""Unit tests for Prometheus metric collection and reset behavior."""

from pg_mcp.observability.metrics import MetricsCollector, metrics


def test_metrics_are_recorded_and_reset_on_the_same_registry() -> None:
    metrics.reset_all_metrics()

    metrics.increment_query_request("success", "test_db")
    sample_value = metrics.registry.get_sample_value(
        "pg_mcp_query_requests_total",
        labels={"status": "success", "database": "test_db"},
    )
    assert sample_value == 1

    registry = metrics.registry
    metrics.reset_all_metrics()

    assert metrics.registry is registry
    assert metrics.registry.get_sample_value(
        "pg_mcp_query_requests_total",
        labels={"status": "success", "database": "test_db"},
    ) is None
    assert MetricsCollector() is metrics
