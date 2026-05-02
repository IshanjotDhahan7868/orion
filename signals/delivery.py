from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> tuple[bool, str]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return True, res.read().decode("utf-8") or "ok"
    except urllib.error.HTTPError as exc:
        return False, exc.read().decode("utf-8")
    except urllib.error.URLError as exc:
        return False, str(exc)


def deliver_signal_alert(
    *,
    channel: str,
    destination: str,
    subject: str,
    body: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = channel.strip().lower()
    metadata = metadata or {}

    if normalized == "webhook":
        ok, response = _post_json(
            destination,
            {
                "subject": subject,
                "body": body,
                "metadata": metadata,
            },
        )
        return {"ok": ok, "channel": normalized, "response": response}

    if normalized == "slack":
        ok, response = _post_json(
            destination,
            {
                "text": f"*{subject}*\n{body}",
                "metadata": metadata,
            },
        )
        return {"ok": ok, "channel": normalized, "response": response}

    if normalized == "email":
        api_key = os.getenv("RESEND_API_KEY")
        from_email = os.getenv("RESEND_FROM_EMAIL")
        if not api_key or not from_email:
            return {
                "ok": False,
                "channel": normalized,
                "response": "RESEND_API_KEY and RESEND_FROM_EMAIL are required for email delivery.",
            }
        ok, response = _post_json(
            "https://api.resend.com/emails",
            {
                "from": from_email,
                "to": [destination],
                "subject": subject,
                "text": body,
            },
            headers={"Authorization": f"Bearer {api_key}"},
        )
        return {"ok": ok, "channel": normalized, "response": response}

    return {
        "ok": False,
        "channel": normalized,
        "response": f"Unsupported alert channel: {channel}",
    }
