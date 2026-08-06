"""
gmail_client.py
================

This is the engine room of the project: it connects to Gmail over IMAP
and pulls every message sent *from* one particular address, exactly
like the classic recipe of "search for a sender, then walk each
message and pull out the body" -- just wrapped up so it's safe to call
from a web view, with real error handling and clean, structured
output instead of raw prints.

Nothing here ever writes the App Password to disk or to the database;
callers are responsible for keeping it in the request/session only.
"""

from __future__ import annotations

import email
import imaplib
import re
from dataclasses import dataclass, field
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Optional


class GmailAuthError(Exception):
    """Raised when Gmail rejects the address/App Password pair."""


class GmailConnectionError(Exception):
    """Raised when the IMAP server can't be reached at all."""


class GmailSearchError(Exception):
    """Raised when the mailbox/search itself fails after a successful login."""


DEFAULT_IMAP_SERVER = "imap.gmail.com"
DEFAULT_IMAP_PORT = 993


@dataclass
class FetchedEmail:
    message_id: str = ""
    subject: str = "(no subject)"
    from_address: str = ""
    to_address: str = ""
    date_header: str = ""
    received_at: Optional[datetime] = None
    snippet: str = ""
    body_text: str = ""
    body_html: str = ""
    attachment_names: List[str] = field(default_factory=list)

    @property
    def has_attachments(self) -> bool:
        return bool(self.attachment_names)


def _decode_header_value(raw_value: Optional[str]) -> str:
    """Turn a possibly-encoded ("=?UTF-8?B?...?=") header into plain text."""
    if not raw_value:
        return ""
    decoded_parts = decode_header(raw_value)
    pieces = []
    for text, charset in decoded_parts:
        if isinstance(text, bytes):
            try:
                pieces.append(text.decode(charset or "utf-8", errors="replace"))
            except (LookupError, TypeError):
                pieces.append(text.decode("utf-8", errors="replace"))
        else:
            pieces.append(text)
    return "".join(pieces)


def _extract_body(msg: email.message.Message) -> tuple[str, str, list[str]]:
    """Walk a (possibly multipart) message and return (text_body, html_body, attachment_names)."""
    text_body = ""
    html_body = ""
    attachments: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition") or "")

            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    attachments.append(_decode_header_value(filename))
                continue

            if content_type == "text/plain" and not text_body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text_body = payload.decode(charset, errors="replace")
            elif content_type == "text/html" and not html_body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    html_body = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        content = payload.decode(charset, errors="replace") if payload else ""
        if msg.get_content_type() == "text/html":
            html_body = content
        else:
            text_body = content

    return text_body.strip(), html_body.strip(), attachments


def _strip_html(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _make_snippet(text: str, length: int = 220) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= length:
        return collapsed
    return collapsed[:length].rsplit(" ", 1)[0] + "\u2026"


def connect(gmail_address: str, app_password: str, imap_server: str = DEFAULT_IMAP_SERVER) -> imaplib.IMAP4_SSL:
    """
    Open an authenticated IMAP connection.

    Raises GmailConnectionError if the server can't be reached, or
    GmailAuthError if the address/App Password pair is rejected.
    """
    try:
        connection = imaplib.IMAP4_SSL(imap_server, DEFAULT_IMAP_PORT)
    except (OSError, imaplib.IMAP4.error) as exc:
        raise GmailConnectionError(f"Could not reach {imap_server}: {exc}") from exc

    try:
        connection.login(gmail_address, app_password)
    except imaplib.IMAP4.error as exc:
        raise GmailAuthError(
            "Gmail rejected that address/App Password combination. "
            "Make sure IMAP is enabled and you're using a 16-character "
            "App Password, not your normal account password."
        ) from exc

    return connection


def fetch_from_sender(
    gmail_address: str,
    app_password: str,
    sender_email: str,
    mailbox: str = "INBOX",
    limit: int = 25,
    imap_server: str = DEFAULT_IMAP_SERVER,
) -> List[FetchedEmail]:
    """
    Log in to Gmail and return up to `limit` messages sent from
    `sender_email`, newest first.

    This mirrors the classic three-step IMAP recipe: connect, SEARCH
    FROM "<sender>", then FETCH + parse each matching message -- with
    proper error handling and structured results instead of prints.
    """
    connection = connect(gmail_address, app_password, imap_server)

    try:
        status, _ = connection.select(mailbox)
        if status != "OK":
            raise GmailSearchError(f"Could not open mailbox '{mailbox}'.")

        search_criteria = f'(FROM "{sender_email}")'
        status, data = connection.search(None, search_criteria)
        if status != "OK":
            raise GmailSearchError("The search request was rejected by Gmail.")

        message_numbers = data[0].split()
        # Newest first, capped at `limit`.
        message_numbers = list(reversed(message_numbers))[:limit]

        results: List[FetchedEmail] = []
        for num in message_numbers:
            status, msg_data = connection.fetch(num, "(RFC822)")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            text_body, html_body, attachments = _extract_body(msg)
            display_text = text_body or _strip_html(html_body)

            received_at = None
            date_header = msg.get("Date", "")
            if date_header:
                try:
                    received_at = parsedate_to_datetime(date_header)
                except (TypeError, ValueError):
                    received_at = None

            results.append(
                FetchedEmail(
                    message_id=msg.get("Message-ID", ""),
                    subject=_decode_header_value(msg.get("Subject")) or "(no subject)",
                    from_address=_decode_header_value(msg.get("From")),
                    to_address=_decode_header_value(msg.get("To")),
                    date_header=date_header,
                    received_at=received_at,
                    snippet=_make_snippet(display_text) if display_text else "",
                    body_text=display_text,
                    body_html=html_body,
                    attachment_names=attachments,
                )
            )

        return results
    finally:
        try:
            connection.close()
        except imaplib.IMAP4.error:
            pass
        connection.logout()
