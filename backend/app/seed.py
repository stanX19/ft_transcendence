"""Deterministic application seed entry point.

Foundation startup intentionally has no rows to seed. Later feature slices
can add local, deterministic demo data here without changing the startup
contract or introducing a remote dependency.
"""

from __future__ import annotations


def seed() -> None:
    """Run the current idempotent no-op seed."""

    return None


if __name__ == "__main__":
    seed()
