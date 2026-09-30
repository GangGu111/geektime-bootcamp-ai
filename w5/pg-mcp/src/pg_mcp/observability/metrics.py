"""Prometheus metrics collector for PostgreSQL MCP Server.

This module implements comprehensive metrics collection using prometheus_client,
tracking query requests, LLM calls, database operations, and system health.
"""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, start_http_server


class MetricsCollector:
    """Centralized metrics collector using Prometheus client.

    This class provides singleton access to all application metrics,
    implementing the metrics specified in the implementation plan.

    Metrics Categories:
    - Query metrics: Request counts and durations
    - LLM metrics: API calls, latency, and token usage
    - Database metrics: Connection pool and query performance
    - Security metrics: Rejected queries
    - Cache metrics: Schema cache age

    Example:
        >>> metrics = MetricsCollector()
        >>> metrics.query_requests.labels(status="success", database="mydb").inc()
        >>> with metrics.query_duration.time():
        ...     await execute_query()
    """

    _instance: "MetricsCollector | None" = None

    def __new__(cls) -> "MetricsCollector":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.registry = CollectorRegistry()
            cls._instance._initialize_metrics()
        return cls._instance

    def _initialize_metrics(self) -> None:
        """Initialize all Prometheus metrics.

        Creates counters, histograms, and gauges for tracking various
        aspects of the MCP server operation.
        """
        # Query Metrics
        self.query_requests: Counter = Counter(
            "pg_mcp_query_requests_total",
            "Total number of query requests processed",
            labelnames=["status", "database"],
            registry=self.registry,
        )

        self.query_duration: Histogram = Histogram(
            "pg_mcp_query_duration_seconds",
            "Query request processing duration in seconds",
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
            registry=self.registry,
        )

        # LLM Metrics
        self.llm_calls: Counter = Counter(
            "pg_mcp_llm_calls_total",
            "Total number of LLM API calls",
            labelnames=["operation"],
            registry=self.registry,
        )

        self.llm_latency: Histogram = Histogram(
            "pg_mcp_llm_latency_seconds",
            "LLM API call latency in seconds",
            labelnames=["operation"],
            buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0),
            registry=self.registry,
        )

        self.llm_tokens_used: Counter = Counter(
            "pg_mcp_llm_tokens_used",
            "Total number of tokens used by LLM",
            labelnames=["operation"],
            registry=self.registry,
        )

        # Security Metrics
        self.sql_rejected: Counter = Counter(
            "pg_mcp_sql_rejected_total",
            "Total number of SQL queries rejected by security checks",
            labelnames=["reason"],
            registry=self.registry,
        )

        # Database Metrics
        self.db_connections_active: Gauge = Gauge(
            "pg_mcp_db_connections_active",
            "Number of active database connections",
            labelnames=["database"],
            registry=self.registry,
        )

        self.db_query_duration: Histogram = Histogram(
            "pg_mcp_db_query_duration_seconds",
            "Database query execution duration in seconds",
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
            registry=self.registry,
        )

        self.retry_attempts: Counter = Counter(
            "pg_mcp_retry_attempts_total",
            "Total retry attempts for transient failures",
            labelnames=["operation"],
            registry=self.registry,
        )
        self.rate_limiter_wait: Histogram = Histogram(
            "pg_mcp_rate_limiter_wait_seconds",
            "Time spent waiting for a concurrency slot",
            labelnames=["resource"],
            buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 30.0),
            registry=self.registry,
        )

        # Cache Metrics
        self.schema_cache_age: Gauge = Gauge(
            "pg_mcp_schema_cache_age_seconds",
            "Age of the schema cache in seconds",
            labelnames=["database"],
            registry=self.registry,
        )

    def start_metrics_server(self, port: int) -> None:
        """Start the Prometheus metrics HTTP server.

        Args:
            port: Port number to listen on for metrics scraping.

        Example:
            >>> metrics = MetricsCollector()
            >>> metrics.start_metrics_server(9090)
            # Metrics available at http://localhost:9090/metrics
        """
        start_http_server(port, registry=self.registry)

    def increment_query_request(self, status: str, database: str) -> None:
        """Increment query request counter.

        Args:
            status: Query status (success, error, validation_failed, etc.)
            database: Target database name.
        """
        self.query_requests.labels(status=status, database=database).inc()

    def increment_llm_call(self, operation: str) -> None:
        """Increment LLM call counter.

        Args:
            operation: Type of LLM operation (generate_sql, validate_result, etc.)
        """
        self.llm_calls.labels(operation=operation).inc()

    def observe_llm_latency(self, operation: str, duration: float) -> None:
        """Record LLM call latency.

        Args:
            operation: Type of LLM operation.
            duration: Duration in seconds.
        """
        self.llm_latency.labels(operation=operation).observe(duration)

    def increment_llm_tokens(self, operation: str, tokens: int) -> None:
        """Increment LLM token usage counter.

        Args:
            operation: Type of LLM operation.
            tokens: Number of tokens used.
        """
        self.llm_tokens_used.labels(operation=operation).inc(tokens)

    def increment_sql_rejected(self, reason: str) -> None:
        """Increment SQL rejection counter.

        Args:
            reason: Reason for rejection (ddl_detected, blocked_function, etc.)
        """
        self.sql_rejected.labels(reason=reason).inc()

    def set_db_connections_active(self, database: str, count: int) -> None:
        """Set active database connection count.

        Args:
            database: Database name.
            count: Number of active connections.
        """
        self.db_connections_active.labels(database=database).set(count)

    def observe_db_query_duration(self, duration: float) -> None:
        """Record database query duration.

        Args:
            duration: Duration in seconds.
        """
        self.db_query_duration.observe(duration)

    def increment_retry_attempt(self, operation: str) -> None:
        """Record a retry before another attempt is made."""
        self.retry_attempts.labels(operation=operation).inc()

    def observe_rate_limiter_wait(self, resource: str, duration: float) -> None:
        """Record time spent waiting for a concurrency slot."""
        self.rate_limiter_wait.labels(resource=resource).observe(duration)

    def set_schema_cache_age(self, database: str, age_seconds: float) -> None:
        """Set schema cache age.

        Args:
            database: Database name.
            age_seconds: Cache age in seconds.
        """
        self.schema_cache_age.labels(database=database).set(age_seconds)

    def reset_all_metrics(self) -> None:
        """Replace registered collectors with fresh metrics on the same registry."""
        for collector in (
            self.query_requests,
            self.query_duration,
            self.llm_calls,
            self.llm_latency,
            self.llm_tokens_used,
            self.sql_rejected,
            self.db_connections_active,
            self.db_query_duration,
            self.retry_attempts,
            self.rate_limiter_wait,
            self.schema_cache_age,
        ):
            self.registry.unregister(collector)
        self._initialize_metrics()


# Singleton instance
metrics = MetricsCollector()
