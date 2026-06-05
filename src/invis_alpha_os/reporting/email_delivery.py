"""Weekly report email delivery: SMTP (stdlib) or Gmail OAuth fallback (v1.1 approved)."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Protocol

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_REQUIRED_ENV_KEYS = (
    "WEEKLY_REPORT_EMAIL_ENABLED",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "WEEKLY_REPORT_EMAIL_FROM",
    "WEEKLY_REPORT_EMAIL_TO",
)


class SmtpSender(Protocol):
    def __call__(self, *, message: EmailMessage, host: str, port: int, username: str, password: str) -> None: ...


class GmailOAuthSender(Protocol):
    def __call__(self, *, message: EmailMessage, recipient: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class WeeklyEmailContent:
    subject: str
    text_body: str | None
    html_body: str | None
    content_source: str


@dataclass(frozen=True)
class WeeklyEmailDeliveryResult:
    email_delivery_status: str
    report_root: str
    report_date: str
    content_source: str | None
    recipient_redacted: str | None
    message_id: str | None
    reason: str | None
    missing: tuple[str, ...]
    delivery_transport: str | None = None

    @property
    def ok(self) -> bool:
        return self.email_delivery_status in {"sent", "dry_run"}


def redact_email_address(email: str) -> str:
    """Redact local part; keep domain for support logs."""

    normalized = email.strip()
    if "@" not in normalized:
        return "***"
    local, domain = normalized.split("@", 1)
    prefix = local[0] if local else "*"
    return f"{prefix}***@{domain}"


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def weekly_send_gate_open() -> bool:
    """SMTP path requires WEEKLY_REPORT_EMAIL_ENABLED; OAuth also accepts CONFIRM_GMAIL_SEND=YES."""

    if _truthy_env("WEEKLY_REPORT_EMAIL_ENABLED"):
        return True
    return os.environ.get("CONFIRM_GMAIL_SEND", "").strip() == "YES"


def missing_required_smtp_env() -> tuple[str, ...]:
    if not _truthy_env("WEEKLY_REPORT_EMAIL_ENABLED"):
        return ("WEEKLY_REPORT_EMAIL_ENABLED",)
    missing: list[str] = []
    for key in _REQUIRED_ENV_KEYS[1:]:
        if not os.environ.get(key, "").strip():
            missing.append(key)
    return tuple(missing)


def missing_required_email_env() -> tuple[str, ...]:
    """Backward-compatible alias for SMTP-only missing env check."""

    return missing_required_smtp_env()


def resolve_weekly_recipient() -> str:
    return (
        os.environ.get("WEEKLY_REPORT_EMAIL_TO", "").strip()
        or os.environ.get("GMAIL_REPORT_TO", "").strip()
    )


def resolve_weekly_sender(*, recipient: str) -> str:
    from invis_alpha_os.reports.gmail_delivery import resolve_gmail_sender

    explicit = (
        os.environ.get("WEEKLY_REPORT_EMAIL_FROM", "").strip()
        or os.environ.get("GMAIL_REPORT_FROM", "").strip()
    )
    if explicit:
        return explicit
    return resolve_gmail_sender(dry_run=False, recipient=recipient)


def gmail_oauth_delivery_ready() -> tuple[bool, tuple[str, ...]]:
    from invis_alpha_os.reports.gmail_delivery import credentials_configured

    missing: list[str] = []
    if not weekly_send_gate_open():
        missing.append("WEEKLY_REPORT_EMAIL_ENABLED_or_CONFIRM_GMAIL_SEND")
    recipient = resolve_weekly_recipient()
    if not recipient:
        missing.append("WEEKLY_REPORT_EMAIL_TO_or_GMAIL_REPORT_TO")
    if not credentials_configured():
        missing.append("GMAIL_OAUTH_CREDENTIALS")
    return (not missing, tuple(missing))


def default_weekly_email_env_files() -> tuple[Path, ...]:
    config_root = Path.home() / ".config" / "invest-alpha-os"
    return (
        config_root / "weekly_report_email.env",
        config_root / "daily_gmail.env",
    )


def load_env_file(path: Path, *, override: bool = False) -> None:
    """Load KEY=VALUE lines into os.environ without logging values."""

    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value


def bootstrap_weekly_email_env(*, env_file: Path | None = None, auto_env_file: bool = True) -> None:
    if env_file is not None:
        load_env_file(env_file, override=True)
        return
    if auto_env_file:
        for candidate in default_weekly_email_env_files():
            load_env_file(candidate)


def load_weekly_email_content(*, report_root: Path, report_date: str) -> WeeklyEmailContent:
    """Prefer html preview, then txt, then README_FOR_USER.md."""

    subject = f"[invest-alpha-os] Weekly Report {report_date}"
    email_dir = report_root / "email"
    html_path = email_dir / "email_preview.html"
    txt_path = email_dir / "email_preview.txt"
    readme_path = report_root / "README_FOR_USER.md"
    copy_path = report_root / "weekly_candidate_brief_copy.md"

    if html_path.is_file():
        html_body = html_path.read_text(encoding="utf-8")
        text_body = txt_path.read_text(encoding="utf-8") if txt_path.is_file() else None
        return WeeklyEmailContent(
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            content_source="email_preview_html",
        )
    if txt_path.is_file():
        return WeeklyEmailContent(
            subject=subject,
            text_body=txt_path.read_text(encoding="utf-8"),
            html_body=None,
            content_source="email_preview_txt",
        )
    if readme_path.is_file():
        return WeeklyEmailContent(
            subject=subject,
            text_body=readme_path.read_text(encoding="utf-8"),
            html_body=None,
            content_source="README_FOR_USER",
        )
    if copy_path.is_file():
        return WeeklyEmailContent(
            subject=subject,
            text_body=copy_path.read_text(encoding="utf-8"),
            html_body=None,
            content_source="weekly_candidate_brief_copy",
        )
    raise FileNotFoundError(f"no email content under report_root={report_root}")


def build_email_message(
    *,
    content: WeeklyEmailContent,
    from_addr: str,
    to_addr: str,
    cc: str | None = None,
    bcc: str | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = content.subject
    message["From"] = from_addr
    message["To"] = to_addr
    if cc:
        message["Cc"] = cc
    if bcc:
        message["Bcc"] = bcc

    if content.html_body:
        plain = content.text_body or "Weekly report (HTML body attached in multipart/alternative)."
        message.set_content(plain)
        message.add_alternative(content.html_body, subtype="html")
    elif content.text_body:
        message.set_content(content.text_body)
    else:
        message.set_content("Weekly report content unavailable.")
    return message


def _default_smtp_send(
    *,
    message: EmailMessage,
    host: str,
    port: int,
    username: str,
    password: str,
) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls(context=context)
        server.login(username, password)
        server.send_message(message)


def _default_gmail_oauth_send(*, message: EmailMessage, recipient: str) -> dict[str, Any]:
    from invis_alpha_os.reports.gmail_delivery import (
        encode_message_raw,
        send_gmail_message,
        validate_gmail_send_gates,
    )

    validate_gmail_send_gates(recipient=recipient)
    raw = encode_message_raw(message)
    return send_gmail_message(raw, allow_interactive_oauth=False)


def deliver_weekly_report_email(
    *,
    report_root: Path,
    report_date: str,
    send: bool,
    smtp_sender: SmtpSender | None = None,
    gmail_oauth_sender: GmailOAuthSender | None = None,
) -> WeeklyEmailDeliveryResult:
    """Dry-run by default; SMTP or Gmail OAuth when send=True and env is complete."""

    report_root = report_root.resolve()
    if not report_root.is_dir():
        return WeeklyEmailDeliveryResult(
            email_delivery_status="failed",
            report_root=str(report_root),
            report_date=report_date,
            content_source=None,
            recipient_redacted=None,
            message_id=None,
            reason="REPORT_ROOT_NOT_FOUND",
            missing=(),
        )

    try:
        content = load_weekly_email_content(report_root=report_root, report_date=report_date)
    except FileNotFoundError:
        return WeeklyEmailDeliveryResult(
            email_delivery_status="failed",
            report_root=str(report_root),
            report_date=report_date,
            content_source=None,
            recipient_redacted=None,
            message_id=None,
            reason="CONTENT_NOT_FOUND",
            missing=(),
        )

    if not send:
        to_preview = resolve_weekly_recipient()
        return WeeklyEmailDeliveryResult(
            email_delivery_status="dry_run",
            report_root=str(report_root),
            report_date=report_date,
            content_source=content.content_source,
            recipient_redacted=redact_email_address(to_preview) if to_preview else None,
            message_id=None,
            reason=None,
            missing=(),
        )

    smtp_missing = missing_required_smtp_env()
    oauth_ready, oauth_missing = gmail_oauth_delivery_ready()
    if smtp_missing and not oauth_ready:
        return WeeklyEmailDeliveryResult(
            email_delivery_status="blocked",
            report_root=str(report_root),
            report_date=report_date,
            content_source=content.content_source,
            recipient_redacted=None,
            message_id=None,
            reason="MISSING_REQUIRED_EMAIL_ENV",
            missing=smtp_missing if smtp_missing else oauth_missing,
        )

    if not smtp_missing:
        from_addr = os.environ["WEEKLY_REPORT_EMAIL_FROM"].strip()
        to_addr = os.environ["WEEKLY_REPORT_EMAIL_TO"].strip()
        cc = os.environ.get("WEEKLY_REPORT_EMAIL_CC", "").strip() or None
        bcc = os.environ.get("WEEKLY_REPORT_EMAIL_BCC", "").strip() or None
        host = os.environ["SMTP_HOST"].strip()
        port = int(os.environ["SMTP_PORT"].strip())
        username = os.environ["SMTP_USERNAME"].strip()
        password = os.environ["SMTP_PASSWORD"].strip()

        if not _EMAIL_RE.match(from_addr) or not _EMAIL_RE.match(to_addr):
            return WeeklyEmailDeliveryResult(
                email_delivery_status="blocked",
                report_root=str(report_root),
                report_date=report_date,
                content_source=content.content_source,
                recipient_redacted=redact_email_address(to_addr) if to_addr else None,
                message_id=None,
                reason="INVALID_EMAIL_ADDRESS",
                missing=(),
            )

        message = build_email_message(content=content, from_addr=from_addr, to_addr=to_addr, cc=cc, bcc=bcc)
        sender = smtp_sender or _default_smtp_send
        try:
            sender(message=message, host=host, port=port, username=username, password=password)
        except Exception:
            return WeeklyEmailDeliveryResult(
                email_delivery_status="failed",
                report_root=str(report_root),
                report_date=report_date,
                content_source=content.content_source,
                recipient_redacted=redact_email_address(to_addr),
                message_id=None,
                reason="EMAIL_SEND_FAILED",
                missing=(),
                delivery_transport="smtp",
            )

        message_id = message.get("Message-ID")
        return WeeklyEmailDeliveryResult(
            email_delivery_status="sent",
            report_root=str(report_root),
            report_date=report_date,
            content_source=content.content_source,
            recipient_redacted=redact_email_address(to_addr),
            message_id=message_id,
            reason=None,
            missing=(),
            delivery_transport="smtp",
        )

    to_addr = resolve_weekly_recipient()
    from_addr = resolve_weekly_sender(recipient=to_addr)
    from_ok = from_addr == "me" or bool(_EMAIL_RE.match(from_addr)) if from_addr else False
    if not from_addr or not from_ok or not _EMAIL_RE.match(to_addr):
        return WeeklyEmailDeliveryResult(
            email_delivery_status="blocked",
            report_root=str(report_root),
            report_date=report_date,
            content_source=content.content_source,
            recipient_redacted=redact_email_address(to_addr) if to_addr else None,
            message_id=None,
            reason="INVALID_EMAIL_ADDRESS",
            missing=oauth_missing,
            delivery_transport="gmail_oauth",
        )

    message = build_email_message(content=content, from_addr=from_addr, to_addr=to_addr)
    oauth = gmail_oauth_sender or _default_gmail_oauth_send
    try:
        api_result = oauth(message=message, recipient=to_addr)
    except Exception:
        return WeeklyEmailDeliveryResult(
            email_delivery_status="failed",
            report_root=str(report_root),
            report_date=report_date,
            content_source=content.content_source,
            recipient_redacted=redact_email_address(to_addr),
            message_id=None,
            reason="EMAIL_SEND_FAILED",
            missing=(),
            delivery_transport="gmail_oauth",
        )

    message_id = api_result.get("id") if isinstance(api_result, dict) else None
    return WeeklyEmailDeliveryResult(
        email_delivery_status="sent",
        report_root=str(report_root),
        report_date=report_date,
        content_source=content.content_source,
        recipient_redacted=redact_email_address(to_addr),
        message_id=str(message_id) if message_id else None,
        reason=None,
        missing=(),
        delivery_transport="gmail_oauth",
    )


def format_weekly_email_delivery_json(result: WeeklyEmailDeliveryResult) -> str:
    payload = {
        "email_delivery_status": result.email_delivery_status,
        "report_root": result.report_root,
        "report_date": result.report_date,
        "content_source": result.content_source,
        "recipient_redacted": result.recipient_redacted,
        "message_id": result.message_id,
        "reason": result.reason,
        "missing": list(result.missing),
        "delivery_transport": result.delivery_transport,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_weekly_email_delivery_markdown(result: WeeklyEmailDeliveryResult) -> str:
    lines = [
        "# Weekly Report Email Delivery",
        "",
        f"- email_delivery_status: {result.email_delivery_status}",
        f"- report_root: `{result.report_root}`",
        f"- report_date: {result.report_date}",
        f"- content_source: {result.content_source}",
        f"- recipient_redacted: {result.recipient_redacted}",
        f"- message_id: {result.message_id}",
        f"- reason: {result.reason}",
        f"- delivery_transport: {result.delivery_transport}",
    ]
    if result.missing:
        lines.append(f"- missing: {', '.join(result.missing)}")
    lines.extend(
        [
            "",
            "## Safety Notes",
            "- SMTP credentials are never logged",
            "- recipient addresses are redacted in logs",
            "- observation-only weekly report; not a trading instruction",
            "",
        ]
    )
    return "\n".join(lines)
