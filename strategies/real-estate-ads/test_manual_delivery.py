from manual_delivery import (
    F1_EMAIL_SENDER,
    F1_WHATSAPP_SENDER,
    email_compose_url,
    manual_delivery_actions,
    normalize_recipient_phone,
    whatsapp_compose_url,
)


def test_italian_mobile_is_normalized():
    assert normalize_recipient_phone('371 123 4567') == '393711234567'
    assert normalize_recipient_phone('+39 371 123 4567') == '393711234567'


def test_whatsapp_opens_recipient_chat_without_sending():
    url = whatsapp_compose_url('3711234567', 'Mario', 'Guida acquisto', 'https://example.com/guida.pdf')
    assert url.startswith('https://wa.me/393711234567?text=')
    assert 'send' not in url.lower()


def test_email_is_mailto_compose():
    url = email_compose_url('mario@example.com', 'Mario', 'Checklist Prima Casa', 'https://example.com/checklist.pdf')
    assert url.startswith('mailto:mario@example.com?')
    assert 'subject=' in url
    assert 'body=' in url


def test_fixed_operator_identities_are_exposed():
    actions = manual_delivery_actions('3711234567', 'mario@example.com', 'Mario', 'Guida', 'https://example.com/a.pdf')
    assert actions['auto_send'] is False
    assert actions['whatsapp_sender'] == F1_WHATSAPP_SENDER == '+39 371 370 8294'
    assert actions['email_sender'] == F1_EMAIL_SENDER == 'f1iimobiliaresusa@outlook.it'
    assert actions['whatsapp_url']
    assert actions['email_url']
