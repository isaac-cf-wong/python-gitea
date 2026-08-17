"""Assertion helper for the CLI's `{"data": ..., "metadata": ...}` JSON envelope."""

from __future__ import annotations

import json
from typing import Any

ENVELOPE_KEYS = frozenset({"data", "metadata"})


def parse_envelope(stdout: str, *, allow_prefix: str = "") -> dict[str, Any]:
    """Parse standard output as the JSON envelope, rejecting anything else on it.

    Unlike `json.loads(stdout[stdout.index("{") :])`, this refuses to skip over
    text printed before the envelope. In JSON mode stdout belongs to the
    envelope alone, so a leaked log line or human-readable rendering has to fail
    the test rather than be parsed around.

    Args:
        stdout: Captured standard output of an `--output json` invocation.
        allow_prefix: Text expected before the envelope, and nothing else.
            `CliRunner` echoes answers typed at a prompt into stdout, which a
            real non-interactive consumer never sees; tests supplying `input`
            declare that echo here.

    Returns:
        The parsed envelope.

    Raises:
        AssertionError: If stdout is not `allow_prefix` followed by the envelope
            alone, or if the envelope's top-level keys are not `data` and
            `metadata`.

    """
    if not stdout.startswith(allow_prefix):
        raise AssertionError(f"stdout does not start with the declared prefix {allow_prefix!r}: {stdout!r}")

    body = stdout[len(allow_prefix) :]

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise AssertionError(f"stdout is not the JSON envelope alone: {stdout!r}") from error

    keys = set(payload) if isinstance(payload, dict) else None
    if keys != set(ENVELOPE_KEYS):
        raise AssertionError(f"stdout is not an object keyed by {sorted(ENVELOPE_KEYS)}: {stdout!r}")

    return payload
