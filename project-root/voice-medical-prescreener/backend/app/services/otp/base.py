"""P4-1 (ADR-0045) — the pluggable OTP sender seam.

A sender's ONLY job is delivery: it receives the phone and the plaintext code
and gets the code to the patient. Everything security-relevant (generation,
hashing, expiry, attempts, single-use) lives in service.py and is identical
for every channel — adding a real SMS aggregator later is one new subclass
plus an OTP_CHANNEL value, nothing else.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class OtpSendError(RuntimeError):
    """Delivery failed (gateway down, bad credentials, rejected number)."""


class OtpSender(ABC):
    channel: str = "abstract"

    @abstractmethod
    def send(self, phone: str, code: str) -> None:
        """Deliver ``code`` to ``phone`` (normalized ``+8801...``). Raises
        :class:`OtpSendError` on failure — never fails silently."""
