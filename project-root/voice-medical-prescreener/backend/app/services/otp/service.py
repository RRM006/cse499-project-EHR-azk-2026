"""P4-1 (ADR-0045) — channel-independent OTP core: issue + verify.

Security properties (identical for every sender channel):
  * codes are 6 random digits from ``secrets`` (never equal to the bypass code);
  * only a salted SHA-256 hash is persisted — plaintext lives in the sender call;
  * 5-minute expiry (OTP_TTL_SECONDS) and single-use (``consumed_at``);
  * constant-time comparison via ``hmac.compare_digest`` on hashes;
  * max-attempt lockout (OTP_MAX_ATTEMPTS) — a locked code stays dead even for
    the CORRECT value; the patient must request a fresh code;
  * resend throttling (OTP_RESEND_COOLDOWN_SECONDS) — re-lookups inside the
    window do not send another SMS, the outstanding code stays valid.

The 000000 universal bypass is honored ONLY inside the ``otp_channel == "dev"``
branch AND with ``otp_dev_bypass`` true, so no env-var accident can enable it
under a production channel.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.db.models import OtpCode
from backend.app.services.otp.base import OtpSender, OtpSendError
from backend.app.services.otp.dev_log import DevLogSender
from backend.app.services.otp.textbee import TextBeeSender


def _hash_code(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()


def _as_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes even for timezone=True columns — pin to UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _generate_code(settings: Settings) -> str:
    while True:
        code = f"{secrets.randbelow(1_000_000):06d}"
        # A real code must never collide with the dev bypass value.
        if code != settings.dev_otp:
            return code


def get_sender(settings: Settings | None = None) -> OtpSender:
    """Factory for the configured channel — the ONE switch on OTP_CHANNEL."""
    settings = settings or get_settings()
    if settings.otp_channel == "dev":
        return DevLogSender()
    if settings.otp_channel == "textbee":
        return TextBeeSender(
            api_key=settings.textbee_api_key,
            device_id=settings.textbee_device_id,
            base_url=settings.textbee_base_url,
            ttl_minutes=max(1, settings.otp_ttl_seconds // 60),
        )
    raise ValueError(
        f"Unknown OTP_CHANNEL {settings.otp_channel!r} — expected 'dev' or 'textbee'."
    )


@dataclass
class IssueResult:
    sent: bool
    retry_after_seconds: int | None = None


def issue_otp(db: Session, *, phone: str, patient_id: int | None = None) -> IssueResult:
    """Issue (or throttle) a code for a normalized phone and hand it to the sender.

    Inside the resend cooldown the outstanding code stays valid and nothing is
    sent again. A new issue invalidates every older outstanding code, so exactly
    one code is live per phone. If delivery fails the fresh code is voided and
    :class:`OtpSendError` propagates — a code the patient never received must not
    remain verifiable.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    latest = (
        db.query(OtpCode)
        .filter(OtpCode.phone == phone, OtpCode.consumed_at.is_(None))
        .order_by(OtpCode.id.desc())
        .first()
    )
    if latest is not None:
        age = (now - _as_utc(latest.created_at)).total_seconds()
        if age < settings.otp_resend_cooldown_seconds and _as_utc(latest.expires_at) > now:
            return IssueResult(
                sent=False,
                retry_after_seconds=max(1, int(settings.otp_resend_cooldown_seconds - age)),
            )

    db.query(OtpCode).filter(OtpCode.phone == phone, OtpCode.consumed_at.is_(None)).update(
        {OtpCode.expires_at: now}, synchronize_session=False
    )
    code = _generate_code(settings)
    salt = secrets.token_hex(16)
    row = OtpCode(
        phone=phone,
        patient_id=patient_id,
        code_hash=_hash_code(code, salt),
        salt=salt,
        created_at=now,
        expires_at=now + timedelta(seconds=settings.otp_ttl_seconds),
    )
    db.add(row)
    db.commit()

    try:
        get_sender(settings).send(phone, code)
    except OtpSendError:
        row.expires_at = now  # undelivered -> not verifiable
        db.commit()
        raise
    return IssueResult(sent=True)


def verify_otp_code(db: Session, *, phone: str, code: str) -> str:
    """Check ``code`` for ``phone``. Returns 'ok' | 'invalid' | 'locked'.

    The dev bypass branch is checked first and is the ONLY place the bypass can
    succeed — it requires otp_channel == "dev" (structurally impossible under a
    production channel, whatever OTP_DEV_BYPASS is set to).
    """
    settings = get_settings()
    if settings.otp_channel == "dev" and settings.otp_dev_bypass:
        # Hash both sides: constant-time AND safe for non-ASCII input.
        if hmac.compare_digest(_hash_code(code, "bypass"), _hash_code(settings.dev_otp, "bypass")):
            return "ok"

    now = datetime.now(timezone.utc)
    row = (
        db.query(OtpCode)
        .filter(OtpCode.phone == phone, OtpCode.consumed_at.is_(None))
        .order_by(OtpCode.id.desc())
        .first()
    )
    if row is None:
        return "invalid"
    if row.attempts >= settings.otp_max_attempts:
        return "locked"
    if _as_utc(row.expires_at) <= now:
        return "invalid"
    if hmac.compare_digest(row.code_hash, _hash_code(code, row.salt)):
        row.consumed_at = now  # single-use
        db.commit()
        return "ok"
    row.attempts += 1
    db.commit()
    return "locked" if row.attempts >= settings.otp_max_attempts else "invalid"
