"""
contact.py - Opens the user's default mail app pre-filled with a help request.
"""

import re
import urllib.parse
import webbrowser

# Basic RFC-5321 sanity check: local@domain.tld
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(address: str) -> bool:
    """Return True if *address* looks like a plausible email address."""
    return bool(_EMAIL_RE.match(address.strip()))


def compose_message(scan_result: dict) -> tuple[str, str]:
    """Return (subject, body) for the help-request email."""
    risk = scan_result.get("overall_risk", "unknown")
    scan_type = scan_result.get("type", "file")

    if scan_type == "file":
        name = scan_result.get("filename", "a file")
        subject = f"[Secure File Advisor] Can you help me check this file? — {name}"
        body = (
            f"Hello,\n\n"
            f"I'm using Secure File Advisor and it flagged something I need help with.\n\n"
            f"File name: {name}\n"
            f"Risk level: {risk.upper()}\n\n"
            f"Findings:\n"
        )
    else:
        url = scan_result.get("url", "a website")
        subject = f"[Secure File Advisor] Can you help me check this website? — {url}"
        body = (
            f"Hello,\n\n"
            f"I'm using Secure File Advisor and it flagged a website I need help with.\n\n"
            f"Website: {url}\n"
            f"Risk level: {risk.upper()}\n\n"
            f"Findings:\n"
        )

    for finding in scan_result.get("findings", []):
        body += f"\n• {finding['title']}\n  {finding['detail']}\n"

    body += "\nCould you please take a look and let me know if it's safe?\n\nThank you!"
    return subject, body


def open_mailto(to_email: str, subject: str, body: str) -> bool:
    """Open the system's default mail app with a pre-composed message.

    Returns True if the mailto link was opened successfully, False if the
    email address failed basic validation.
    """
    if not is_valid_email(to_email):
        return False
    params = urllib.parse.urlencode({"subject": subject, "body": body})
    mailto = f"mailto:{to_email}?{params}"
    webbrowser.open(mailto)
    return True
