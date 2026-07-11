"""TextBeeSender — real SMS via a TextBee.dev Android gateway device.

TextBee (https://textbee.dev, open source) turns an Android phone with a local
SIM into an SMS gateway: one REST call here -> the phone sends a real SMS to
any Bangladeshi number at the SIM's own rate. Chosen as the free real-OTP
channel for the capstone demo (research 2026-07-11; a BTRC-approved aggregator
slots in later as just another OtpSender subclass).

The code is NEVER logged on this path — it exists only in the request body.
"""

from __future__ import annotations

import httpx

from backend.app.services.otp.base import OtpSender, OtpSendError


class TextBeeSender(OtpSender):
    channel = "textbee"

    def __init__(self, *, api_key: str, device_id: str, base_url: str, ttl_minutes: int) -> None:
        if not api_key or not device_id:
            raise OtpSendError(
                "OTP_CHANNEL=textbee needs TEXTBEE_API_KEY and TEXTBEE_DEVICE_ID in backend/.env "
                "(get both from textbee.dev after registering your Android device)."
            )
        self._api_key = api_key
        self._device_id = device_id
        self._base_url = base_url.rstrip("/")
        self._ttl_minutes = ttl_minutes

    def send(self, phone: str, code: str) -> None:
        url = f"{self._base_url}/gateway/devices/{self._device_id}/send-sms"
        message = (
            f"Your medical pre-screening verification code is {code}. "
            f"It expires in {self._ttl_minutes} minutes."
        )
        try:
            response = httpx.post(
                url,
                headers={"x-api-key": self._api_key},
                json={"recipients": [phone], "message": message},
                timeout=15.0,
            )
        except httpx.HTTPError as exc:
            raise OtpSendError(f"TextBee request failed: {exc}") from exc
        if response.status_code >= 400:
            # Never echo the request body (it holds the code) — status + server text only.
            raise OtpSendError(
                f"TextBee rejected the SMS (HTTP {response.status_code}): {response.text[:200]}"
            )
