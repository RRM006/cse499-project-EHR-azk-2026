"""P4-1 (ADR-0045) — real OTP behind a pluggable sender seam."""

from backend.app.services.otp.base import OtpSender, OtpSendError
from backend.app.services.otp.dev_log import DevLogSender
from backend.app.services.otp.service import (
    IssueResult,
    get_sender,
    issue_otp,
    verify_otp_code,
)
from backend.app.services.otp.textbee import TextBeeSender

__all__ = [
    "DevLogSender",
    "IssueResult",
    "OtpSender",
    "OtpSendError",
    "TextBeeSender",
    "get_sender",
    "issue_otp",
    "verify_otp_code",
]
