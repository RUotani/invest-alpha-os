"""Gmail MIME build and gated send (dry-run default)."""

from __future__ import annotations

import base64
import os
import re
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Sequence

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GMAIL_SCOPES = [GMAIL_SEND_SCOPE]


class GmailSendBlockedError(RuntimeError):
    """Send aborted by safety gate."""


class GmailDeliveryError(RuntimeError):
    """Gmail send/bootstrap failed with a machine-readable reason (no secrets in output)."""

    def __init__(self, reason: str, *, detail: str | None = None) -> None:
        self.reason = reason
        safe_detail = (detail or reason).strip()
        super().__init__(safe_detail)


def classify_gmail_failure(exc: BaseException) -> str:
    """Map exceptions to stable failure reason codes (never includes token/credential bodies)."""

    if isinstance(exc, GmailDeliveryError):
        return exc.reason
    if isinstance(exc, GmailSendBlockedError):
        msg = str(exc).lower()
        if "packages not installed" in msg:
            return "gmail_dependency_missing"
        if "interactive oauth not allowed" in msg:
            return "gmail_oauth_required"
        if "token" in msg and ("missing" in msg or "invalid" in msg):
            return "gmail_oauth_required"
        if "credentials_file" in msg or "gmail_credentials_file" in msg:
            return "gmail_oauth_required"
        if "confirm_gmail_send" in msg:
            return "gmail_send_gate_confirm"
        if "allowlist" in msg or "gmail_self_email" in msg:
            return "gmail_send_gate_recipient"
        return "gmail_send_blocked"
    exc_name = type(exc).__name__
    if exc_name == "HttpError":
        return "gmail_api_error"
    if exc_name in {"RefreshError", "GoogleAuthError"}:
        return "gmail_auth_refresh_failed"
    mod = type(exc).__module__
    if mod.startswith("google.auth") or mod.startswith("google.oauth2"):
        return "gmail_auth_refresh_failed"
    if mod.startswith("googleapiclient"):
        return "gmail_api_error"
    if isinstance(exc, ImportError):
        return "gmail_dependency_missing"
    return "gmail_send_failed"


def resolve_gmail_sender(*, dry_run: bool, recipient: str) -> str:
    """Resolve RFC822 From for send mode; dry-run may use placeholder ``me``."""

    explicit = os.environ.get("GMAIL_REPORT_FROM", "").strip()
    if explicit:
        return explicit
    if dry_run:
        return "me"
    for key in ("GMAIL_SELF_EMAIL", "GMAIL_REPORT_TO"):
        candidate = os.environ.get(key, "").strip()
        if candidate and _EMAIL_RE.match(candidate):
            return candidate
    if recipient and _EMAIL_RE.match(recipient):
        return recipient
    return ""


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
    """True when OAuth client credentials file exists (token may be bootstrapped on first send)."""

    cred_path, _token_path = resolve_gmail_paths()
    return bool(cred_path and cred_path.is_file())


def _save_gmail_token(creds: Any, token_path: Path) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    try:
        os.chmod(token_path, 0o600)
    except OSError:
        pass


def ensure_gmail_credentials(*, allow_interactive_oauth: bool = True) -> Any:
    """Load, refresh, or bootstrap Gmail OAuth credentials. Never prints token contents."""

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        raise GmailSendBlockedError(
            "Gmail API packages not installed. Install google-api-python-client and google-auth-oauthlib for send mode."
        ) from e

    cred_path, token_path = resolve_gmail_paths()
    if not cred_path or not cred_path.is_file():
        raise GmailSendBlockedError("GMAIL_CREDENTIALS_FILE missing or not found")
    if token_path is None:
        raise GmailSendBlockedError("GMAIL_TOKEN_FILE path not configured")

    creds: Any | None = None
    if token_path.is_file():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)
        except (ValueError, OSError):
            creds = None

    if creds is not None and creds.valid:
        return creds

    if creds is not None and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            raise GmailDeliveryError(
                "gmail_auth_refresh_failed",
                detail="Gmail OAuth refresh failed",
            ) from e
        _save_gmail_token(creds, token_path)
        return creds

    if not allow_interactive_oauth:
        raise GmailSendBlockedError("GMAIL_TOKEN_FILE missing or invalid; interactive OAuth not allowed")

    flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), GMAIL_SCOPES)
    creds = flow.run_local_server(port=0)
    _save_gmail_token(creds, token_path)
    return creds


def send_gmail_message(
    raw_message: str,
    *,
    user_id: str = "me",
    allow_interactive_oauth: bool = True,
) -> dict[str, Any]:
    """Call Gmail API users.messages.send (requires optional google packages)."""

    try:
        from googleapiclient.discovery import build
    except ImportError as e:
        raise GmailDeliveryError(
            "gmail_dependency_missing",
            detail="Gmail API packages not installed",
        ) from e

    try:
        creds = ensure_gmail_credentials(allow_interactive_oauth=allow_interactive_oauth)
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return (
            service.users()
            .messages()
            .send(userId=user_id, body={"raw": raw_message})
            .execute()
        )
    except GmailDeliveryError:
        raise
    except GmailSendBlockedError as e:
        raise GmailDeliveryError(classify_gmail_failure(e), detail=str(e)) from e
    except Exception as e:
        reason = classify_gmail_failure(e)
        raise GmailDeliveryError(reason, detail="Gmail API send failed") from e


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
