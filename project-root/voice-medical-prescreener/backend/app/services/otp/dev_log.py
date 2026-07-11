"""DevLogSender — the Option-A development channel: the code goes to the
server log, no SMS is sent. This is the ONLY place in the codebase where a
plaintext OTP may be logged; every other path treats the code as a secret.
"""

from __future__ import annotations

import logging

from backend.app.services.otp.base import OtpSender

# Same channel as main.py's startup banner: uvicorn's default config only wires
# handlers for its own loggers, so a plain module logger would print nothing.
logger = logging.getLogger("uvicorn.error")


class DevLogSender(OtpSender):
    channel = "dev"

    def send(self, phone: str, code: str) -> None:
        logger.info("[OTP] verification code for %s: %s", phone, code)
