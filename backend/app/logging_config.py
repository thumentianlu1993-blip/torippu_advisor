import logging
import sys


def configure_logging(level: str = "INFO"):
    """Configure structured-ish logging for the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers = [handler]

    # Uvicorn's default access formatter logs the raw request target. Share
    # tokens live in the path, so application route-template logging is the
    # only permitted request log.
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False
    access.disabled = True
    # HTTP clients include complete URLs in their default INFO messages.
    # Keep them disabled because URLs may contain share-token paths in tests,
    # internal probes or future service-to-service calls.
    logging.getLogger("httpx").disabled = True
    logging.getLogger("httpcore").disabled = True
