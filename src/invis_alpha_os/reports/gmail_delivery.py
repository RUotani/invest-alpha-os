"""Gmail MIME build and gated send (dry-run default)."""

from __future__ import annotations

import base64
import os
import re
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Sequence

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class GmailSendBlockedError(RuntimeError):
    """Send aborted by safety gate."""


def build_mime_message(
    *,
    sender: str,
    to: Sequence[str],
    subject: str,
    text_body: str,
    html_body: str | None = None,
    attachments: Sequence[tuple[str, bytes, str]] | None = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")
    for name, data, mime in attachments or ():
        maintype, _, subtype = (mime.partition("/") + ("", "", ""))[:3]
        msg.add_attachment(data, maintype=maintype or "application", subtype=subtype or "octet-stream", filename=name)
    return msg


def encode_message_raw(message: EmailMessage) -> str:
    raw = message.as_bytes()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _parse_allowlist(raw: str | None) -> frozenset[str]:
    if not raw:
        return frozenset()
    parts = {p.strip().lower() for p in raw.split(",") if p.strip()}
    return frozenset(parts)


def validate_gmail_send_gates(
    *,
    recipient: str,
    confirm_env: str | None = None,
    allowlist_env: str | None = None,
    self_email_env: str | None = None,
) -> None:
    confirm = (confirm_env if confirm_env is not None else os.environ.get("CONFIRM_GMAIL_SEND", "")).strip()
    if confirm != "YES":
        raise GmailSendBlockedError("CONFIRM_GMAIL_SEND=YES is required for Gmail send")

    to_addr = recipient.strip()
    if not to_addr or not _EMAIL_RE.match(to_addr):
        raise GmailSendBlockedError("GMAIL_REPORT_TO must be a valid email address")

    allowlist = _parse_allowlist(allowlist_env if allowlist_env is not None else os.environ.get("GMAIL_REPORT_ALLOWLIST"))
    self_email = (self_email_env if self_email_env is not None else os.environ.get("GMAIL_SELF_EMAIL", "")).strip().lower()
    to_lower = to_addr.lower()

    if allowlist and to_lower not in allowlist:
        raise GmailSendBlockedError("recipient not in GMAIL_REPORT_ALLOWLIST")
    if not allowlist and self_email and to_lower != self_email:
        raise GmailSendBlockedError("recipient must match GMAIL_SELF_EMAIL when allowlist is unset")


def resolve_gmail_paths() -> tuple[Path | None, Path | None]:
    cred = os.environ.get("GMAIL_CREDENTIALS_FILE", "").strip()
    token = os.environ.get("GMAIL_TOKEN_FILE", "").strip()
    cred_path = Path(cred).expanduser() if cred else None
    token_path = Path(token).expanduser() if token else Path.home() / ".config/invest-alpha-os/gmail_token.json"
    return cred_path, token_path


def credentials_configured() -> bool:
    cred_path, token_path = resolve_gmail_paths()
    return bool(cred_path and cred_path.is_file() and token_path and token_path.is_file())


def send_gmail_message(raw_message: str, *, user_id: str = "me") -> dict[str, Any]:
    """Call Gmail API users.messages.send (requires optional google packages)."""

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as e:
        raise GmailSendBlockedError(
            "Gmail API packages not installed. Install google-api-python-client and google-auth-oauthlib for send mode."
        ) from e

    cred_path, token_path = resolve_gmail_paths()
    if not cred_path or not cred_path.is_file():
        raise GmailSendBlockedError("GMAIL_CREDENTIALS_FILE missing or not found")
    if not token_path or not token_path.is_file():
        raise GmailSendBlockedError("GMAIL_TOKEN_FILE missing or not found")

    creds = Credentials.from_authorized_user_file(str(token_path))
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return (
        service.users()
        .messages()
        .send(userId=user_id, body={"raw": raw_message})
        .execute()
    )


def _extract_body_text(message: EmailMessage) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                continue
            if part.get_content_type() == "text/plain":
                payload = part.get_content()
                return str(payload) if payload is not None else ""
    payload = message.get_content()
    return str(payload) if payload is not None else ""


def write_email_previews(
    out_dir: Path,
    *,
    message: EmailMessage,
    draft_text_path: Path | None = None,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    eml_path = out_dir / "email_preview.eml"
    txt_path = out_dir / "email_preview.txt"
    html_path = out_dir / "email_preview.html"
    eml_path.write_bytes(message.as_bytes())
    txt_path.write_text(_extract_body_text(message), encoding="utf-8")
    html_payload = ""
    for part in message.walk():
        if part.get_content_type() == "text/html":
            html_payload = part.get_content() or ""
            break
    html_path.write_text(html_payload or "<html><body></body></html>", encoding="utf-8")
    paths = {"eml": eml_path, "txt": txt_path, "html": html_path}
    if draft_text_path and draft_text_path.is_file():
        paths["draft_source"] = draft_text_path
    return paths
