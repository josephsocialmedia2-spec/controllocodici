"""Manual assisted delivery for F1 buyer leads.

No WhatsApp or email API is used. The module only builds compose links so the
operator can review the message and press Send manually.
"""
from __future__ import annotations

from urllib.parse import quote, urlencode
import re

F1_WHATSAPP_SENDER = "+39 371 370 8294"
F1_EMAIL_SENDER = "f1iimobiliaresusa@outlook.it"


def normalize_recipient_phone(value: str) -> str:
    """Return a wa.me-compatible number.

    Italian mobile numbers written without country code are normalized to +39.
    """
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("39"):
        return digits
    if len(digits) == 10 and digits.startswith("3"):
        return "39" + digits
    return digits


def delivery_message(first_name: str, material_title: str, delivery_url: str) -> str:
    name = (first_name or "").strip()
    greeting = f"Buongiorno {name}," if name else "Buongiorno,"
    return (
        f"{greeting} come richiesto le invio {material_title}.\n"
        f"Può aprirlo qui: {delivery_url}\n\n"
        "Se vuole, mi indica anche zona, budget e tempi della ricerca così posso "
        "aggiornarla solo sulle opportunità pertinenti.\n\n"
        "F1 Immobiliare"
    )


def whatsapp_compose_url(recipient_phone: str, first_name: str, material_title: str, delivery_url: str) -> str:
    """Open the customer's WhatsApp chat with a prefilled message.

    The message is NOT sent automatically. The logged-in WhatsApp session must
    be the F1 operational account (+39 371 370 8294) if that is the desired sender.
    """
    recipient = normalize_recipient_phone(recipient_phone)
    if not recipient:
        return ""
    text = delivery_message(first_name, material_title, delivery_url)
    return f"https://wa.me/{recipient}?text={quote(text, safe='')}"


def email_compose_url(recipient_email: str, first_name: str, material_title: str, delivery_url: str) -> str:
    """Open the default mail composer addressed to the customer.

    Nothing is sent automatically. Configure Outlook with
    f1iimobiliaresusa@outlook.it as the default sending account to keep the
    sender fixed without using an API.
    """
    recipient = (recipient_email or "").strip()
    if not recipient:
        return ""
    name = (first_name or "").strip()
    greeting = f"Buongiorno {name}," if name else "Buongiorno,"
    subject = f"F1 Immobiliare - {material_title}"
    body = (
        f"{greeting}\n\n"
        f"come richiesto le invio {material_title}.\n\n"
        f"{delivery_url}\n\n"
        "Se vuole, mi indica anche zona, budget e tempi della ricerca così posso "
        "aggiornarla solo sulle opportunità pertinenti.\n\n"
        f"F1 Immobiliare\n{F1_EMAIL_SENDER}"
    )
    query = urlencode({"subject": subject, "body": body}, quote_via=quote)
    return f"mailto:{quote(recipient, safe='@.+')}?{query}"


def manual_delivery_actions(recipient_phone: str, recipient_email: str, first_name: str, material_title: str, delivery_url: str) -> dict:
    return {
        "mode": "manual_assisted",
        "auto_send": False,
        "whatsapp_sender": F1_WHATSAPP_SENDER,
        "email_sender": F1_EMAIL_SENDER,
        "whatsapp_url": whatsapp_compose_url(recipient_phone, first_name, material_title, delivery_url),
        "email_url": email_compose_url(recipient_email, first_name, material_title, delivery_url),
        "instruction": "Apri il canale, controlla il testo e premi Invia manualmente.",
    }
