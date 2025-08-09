import logging
import os
from contextlib import contextmanager
from time import perf_counter


def setup_logging():
    level = os.getenv("RISK_ASSIST_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@contextmanager
def audit_span(logger: logging.Logger, event: str, correlation_id: str | None = None, extra: dict | None = None):
    start = perf_counter()
    meta = {"event": event}
    if correlation_id:
        meta["correlation_id"] = correlation_id
    if extra:
        meta.update(extra)
    logger.info("start", extra=meta)
    try:
        yield
        duration_ms = int((perf_counter() - start) * 1000)
        meta["duration_ms"] = duration_ms
        logger.info("end", extra=meta)
    except Exception as e:
        duration_ms = int((perf_counter() - start) * 1000)
        meta["duration_ms"] = duration_ms
        meta["error"] = str(e)
        logger.exception("error", extra=meta)
        raise
