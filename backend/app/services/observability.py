"""
Observability — Phase 4
========================
1. Structured JSON logging with request context binding
2. OpenTelemetry distributed tracing (RAG pipeline spans)
3. LLM circuit breaker with GPT-4o fallback
4. Health check with detailed component status
5. Metrics endpoint for Prometheus/Datadog scraping
"""
import time
import structlog
import asyncio
from contextlib import asynccontextmanager, contextmanager
from typing import Optional, Callable, Any
from functools import wraps
from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


# ── Structured Logging Setup ──────────────────────────────────────────────────

def configure_structlog():
    """Configure structlog for production JSON output."""
    import logging

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.is_production:
        structlog.configure(
            processors=shared_processors + [structlog.processors.JSONRenderer()],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=shared_processors + [structlog.dev.ConsoleRenderer(colors=True)],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )


# ── OpenTelemetry Tracing ─────────────────────────────────────────────────────

_tracer = None


def get_tracer():
    """Get OpenTelemetry tracer — lazy init."""
    global _tracer
    if _tracer is not None:
        return _tracer
    if not settings.OTEL_ENDPOINT:
        return None
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({
            "service.name": "regulai-api",
            "service.version": settings.VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        })
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.OTEL_ENDPOINT)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("regulai")
        logger.info("otel_tracing_configured", endpoint=settings.OTEL_ENDPOINT)
        return _tracer
    except ImportError:
        logger.warning("otel_not_installed", msg="pip install opentelemetry-sdk opentelemetry-exporter-otlp")
        return None
    except Exception as e:
        logger.error("otel_init_failed", error=str(e))
        return None


@contextmanager
def trace_span(name: str, attributes: dict = None):
    """Context manager for creating a tracing span."""
    tracer = get_tracer()
    if tracer:
        with tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, str(v))
            yield span
    else:
        yield None


# ── LLM Circuit Breaker ───────────────────────────────────────────────────────

class CircuitBreaker:
    """
    Circuit breaker for LLM API calls.
    States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery)

    Failure threshold: 3 failures in 60 seconds → open circuit
    Recovery timeout: 30 seconds before trying again
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        window_seconds: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.window_seconds = window_seconds
        self._state = self.CLOSED
        self._failures: list[float] = []
        self._last_failure_time: Optional[float] = None
        self._success_count = 0

    @property
    def state(self) -> str:
        if self._state == self.OPEN:
            # Check if recovery timeout has passed
            if self._last_failure_time and (time.monotonic() - self._last_failure_time) > self.recovery_timeout:
                self._state = self.HALF_OPEN
                logger.info("circuit_breaker_half_open", name=self.name)
        return self._state

    def record_success(self):
        self._failures = []
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= 2:
                self._state = self.CLOSED
                self._success_count = 0
                logger.info("circuit_breaker_closed", name=self.name)
        else:
            self._state = self.CLOSED

    def record_failure(self):
        now = time.monotonic()
        self._failures = [t for t in self._failures if now - t < self.window_seconds]
        self._failures.append(now)
        self._last_failure_time = now
        self._success_count = 0

        if len(self._failures) >= self.failure_threshold:
            if self._state != self.OPEN:
                logger.error("circuit_breaker_opened", name=self.name, failures=len(self._failures))
            self._state = self.OPEN

    def is_available(self) -> bool:
        return self.state in (self.CLOSED, self.HALF_OPEN)


# Global circuit breakers per LLM provider
_breakers: dict[str, CircuitBreaker] = {
    "anthropic": CircuitBreaker("anthropic", failure_threshold=3, recovery_timeout=30),
    "openai":    CircuitBreaker("openai",    failure_threshold=3, recovery_timeout=30),
}


async def call_llm_with_fallback(
    primary_fn: Callable,
    fallback_fn: Optional[Callable] = None,
    provider: str = "anthropic",
    fallback_provider: str = "openai",
    **kwargs,
) -> Any:
    """
    Call an LLM function with circuit breaker protection and automatic fallback.

    If primary provider (Anthropic) circuit is open → automatically falls back to OpenAI.
    Records successes/failures to manage circuit state.
    """
    primary_breaker = _breakers.get(provider)
    fallback_breaker = _breakers.get(fallback_provider)

    # Try primary
    if primary_breaker and primary_breaker.is_available():
        try:
            with trace_span(f"llm.{provider}", {"model": kwargs.get("model", "")}):
                result = await primary_fn(**kwargs)
            primary_breaker.record_success()
            return result
        except Exception as e:
            primary_breaker.record_failure()
            logger.warning(
                "llm_primary_failed",
                provider=provider,
                error=str(e),
                circuit_state=primary_breaker.state,
            )
            if not fallback_fn:
                raise
    else:
        logger.warning("llm_circuit_open", provider=provider, falling_back=fallback_provider)

    # Try fallback
    if fallback_fn and fallback_breaker and fallback_breaker.is_available():
        try:
            with trace_span(f"llm.{fallback_provider}_fallback", {}):
                result = await fallback_fn(**kwargs)
            fallback_breaker.record_success()
            logger.info("llm_fallback_success", provider=fallback_provider)
            return result
        except Exception as e:
            fallback_breaker.record_failure()
            logger.error("llm_fallback_failed", provider=fallback_provider, error=str(e))
            raise

    raise RuntimeError(f"All LLM providers unavailable. Primary: {provider}, Fallback: {fallback_provider}")


def get_circuit_breaker_status() -> dict:
    """Return circuit breaker health for the /health endpoint."""
    return {
        name: {
            "state": breaker.state,
            "recent_failures": len(breaker._failures),
            "available": breaker.is_available(),
        }
        for name, breaker in _breakers.items()
    }


# ── Metrics Collection ────────────────────────────────────────────────────────

class Metrics:
    """
    Simple in-memory metrics counters.
    In production these feed into Prometheus/Datadog via a scrape endpoint.
    """
    def __init__(self):
        self._counters: dict[str, int] = {}
        self._histograms: dict[str, list[float]] = {}
        self._gauges: dict[str, float] = {}
        self._start_time = time.time()

    def increment(self, name: str, value: int = 1, tags: dict = None):
        key = f"{name}{self._tag_str(tags)}"
        self._counters[key] = self._counters.get(key, 0) + value

    def histogram(self, name: str, value: float, tags: dict = None):
        key = f"{name}{self._tag_str(tags)}"
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
        # Keep only last 1000 values
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]

    def gauge(self, name: str, value: float, tags: dict = None):
        key = f"{name}{self._tag_str(tags)}"
        self._gauges[key] = value

    def _tag_str(self, tags: dict = None) -> str:
        if not tags:
            return ""
        return "{" + ",".join(f'{k}="{v}"' for k, v in sorted(tags.items())) + "}"

    def summary(self) -> dict:
        import statistics
        histo_summary = {}
        for k, values in self._histograms.items():
            if values:
                histo_summary[k] = {
                    "count": len(values),
                    "mean": round(statistics.mean(values), 2),
                    "p50": round(statistics.median(values), 2),
                    "p95": round(sorted(values)[int(len(values) * 0.95)], 2) if len(values) > 20 else None,
                    "p99": round(sorted(values)[int(len(values) * 0.99)], 2) if len(values) > 100 else None,
                }
        return {
            "uptime_seconds": round(time.time() - self._start_time),
            "counters": dict(self._counters),
            "histograms": histo_summary,
            "gauges": dict(self._gauges),
        }

    def prometheus_format(self) -> str:
        """Export metrics in Prometheus text format for scraping."""
        lines = []
        for k, v in self._counters.items():
            name = k.split("{")[0]
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{k} {v}")
        for k, values in self._histograms.items():
            if values:
                name = k.split("{")[0]
                import statistics
                lines.append(f"# TYPE {name} histogram")
                lines.append(f"{name}_count {len(values)}")
                lines.append(f"{name}_sum {sum(values):.3f}")
        for k, v in self._gauges.items():
            name = k.split("{")[0]
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{k} {v}")
        return "\n".join(lines) + "\n"


metrics = Metrics()
