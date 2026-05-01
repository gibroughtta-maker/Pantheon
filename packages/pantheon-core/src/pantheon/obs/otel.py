"""OpenTelemetry hooks — no-op by default; activated when `pantheon[otel]`
extra is installed and `PANTHEON_OTEL_ENDPOINT` is set."""
from __future__ import annotations

import contextlib
import os
import secrets


def no_op_trace_id() -> str:
    return secrets.token_hex(16)


@contextlib.contextmanager
def maybe_span(name: str, **attrs):
    """A span context manager that becomes real if OTel is configured,
    otherwise a no-op. Importing OTel is lazy so the no-op path has zero
    cost when the dependency is not installed."""
    if not os.environ.get("PANTHEON_OTEL_ENDPOINT"):
        yield None
        return
    try:
        from opentelemetry import trace  # type: ignore[import-not-found]
    except ImportError:
        yield None
        return
    tracer = trace.get_tracer("pantheon")
    with tracer.start_as_current_span(name, attributes=attrs) as span:
        yield span
