"""Reviewed rollback bridge contract for pre-expand and expand schemas."""

BRIDGE_SCHEMA_COMPATIBILITY = ("pre-expand", "expand")
BRIDGE_ARTIFACT = "travel-mvp-bridge-v1"


def fail_closed(operation: str) -> None:
    """The bridge reads old shares but denies creator and collection writes."""
    if operation in {"creator", "collection", "vote", "candidate-write"}:
        raise PermissionError("bridge_write_disabled")
