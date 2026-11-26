"""Shared contact inquiry persistence (SQLite) and optional SMTP notification."""

from __future__ import annotations

import logging
import os
import smtplib
import sqlite3
import time
from email.message import EmailMessage

from django.conf import settings

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(settings.BASE_DIR, "var", "data")
_DB_PATH = os.path.join(_DATA_DIR, "analytics.db")


def save_and_notify_contact(name: str, email: str, message: str) -> None:
    """Persist contact submission to SQLite and optionally notify via configured SMTP."""
    clean_name = str(name or "").strip()[:150]
    clean_email = str(email or "").strip()[:254]
    clean_msg = str(message or "").strip()[:5000]

    os.makedirs(_DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, timeout=10.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS contact_messages ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  name TEXT NOT NULL,"
            "  email TEXT NOT NULL,"
            "  message TEXT NOT NULL,"
            "  created_at INTEGER NOT NULL"
            ")"
        )
        conn.execute(
            "INSERT INTO contact_messages (name, email, message, created_at) VALUES (?, ?, ?, ?)",
            (clean_name, clean_email, clean_msg, int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()

    recipient = getattr(settings, "CONTACT_EMAIL", "").strip()
    smtp_host = getattr(settings, "SMTP_HOST", "").strip()
    if recipient and smtp_host and smtp_host not in ("localhost", "127.0.0.1"):
        try:
            msg = EmailMessage()
            msg["Subject"] = f"[StoryBrain AI Contact] {clean_name}"
            msg["From"] = getattr(settings, "SMTP_USER", "") or recipient
            msg["To"] = recipient
            msg["Reply-To"] = clean_email
            msg.set_content(f"From: {clean_name} <{clean_email}>\n\n{clean_msg}")

            port = int(getattr(settings, "SMTP_PORT", 587))
            user = getattr(settings, "SMTP_USER", "").strip()
            password = getattr(settings, "SMTP_PASS", "").strip()
            with smtplib.SMTP(smtp_host, port, timeout=8) as server:
                if port in (587, 465):
                    server.starttls()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        except Exception:
            logger.warning("Contact SMTP notification failed (message persisted to SQLite)", exc_info=True)
