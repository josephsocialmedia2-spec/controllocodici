"""Buyer Lead Magnet Engine for F1 Immobiliare / Real Media Pro.

Builds the offer, lead-capture payload, delivery/follow-up plan and funnel scoring.
No email/SMS/WhatsApp is sent by this module: delivery adapters require authorized accounts.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from html import escape
from pathlib import Path
import json
import re


@dataclass
class BuyerProfile:
    locality: str = ""
    property_type: str = ""
    budget_min: float = 0.0
    budget_max: float = 0.0
    timeframe_days: int = 0
    first_home: bool = False
    mortgage_needed: bool = False
    off_market_interest: bool = False


@dataclass
class LeadMagnetOffer:
    code: str
    title: str
    kind: str
    funnel_stage: str
    promise: str
    qualification_questions: list[str]
    delivery_mode: str = "download"


def choose_offer(profile: BuyerProfile) -> LeadMagnetOffer:
    """Choose one primary offer based on purchase readiness.

    Hot intent → reserved property list.
    First-home / mortgage education → practical guide/checklist.
    Generic early-stage buyer → educational guide.
    """
    locality = (profile.locality or "la tua zona").strip()
    hot = 0 < profile.timeframe_days <= 90
    if profile.off_market_interest or hot:
        return LeadMagnetOffer(
            code="reserved-list",
            title=f"Lista riservata immobili e nuove opportunità a {locality}",
            kind="inventory_list",
            funnel_stage="BOFU",
            promise="Ricevi una selezione aggiornata di immobili coerenti con la tua ricerca, incluse opportunità non ancora promosse quando realmente disponibili.",
            qualification_questions=["Zona desiderata", "Budget massimo", "Tipologia", "Tempistica di acquisto", "Mutuo necessario"],
            delivery_mode="dynamic_list",
        )
    if profile.first_home or profile.mortgage_needed:
        return LeadMagnetOffer(
            code="first-home-checklist",
            title="Checklist Prima Casa: controlli, costi e documenti prima di fare una proposta",
            kind="pdf_checklist",
            funnel_stage="MOFU",
            promise="Una checklist pratica per evitare errori, capire i costi e arrivare preparato alla proposta d'acquisto.",
            qualification_questions=["Zona desiderata", "Budget", "Prima casa", "Mutuo necessario", "Tempistica"],
        )
    return LeadMagnetOffer(
        code="buyer-guide",
        title="Guida pratica all'acquisto casa: 10 errori da evitare",
        kind="pdf_guide",
        funnel_stage="TOFU",
        promise="Una guida sintetica per valutare meglio immobili, costi, documenti e passaggi prima dell'acquisto.",
        qualification_questions=["Zona di interesse", "Budget indicativo", "Tipologia cercata"],
    )


def qualification_score(profile: BuyerProfile) -> dict:
    score = 0
    reasons: list[str] = []
    if profile.locality.strip():
        score += 15; reasons.append("zona definita")
    if profile.property_type.strip():
        score += 10; reasons.append("tipologia definita")
    if profile.budget_max > 0:
        score += 20; reasons.append("budget definito")
    if 0 < profile.timeframe_days <= 90:
        score += 30; reasons.append("acquisto entro 90 giorni")
    elif 90 < profile.timeframe_days <= 180:
        score += 20; reasons.append("acquisto entro 6 mesi")
    elif profile.timeframe_days > 180:
        score += 5; reasons.append("orizzonte lungo")
    if profile.off_market_interest:
        score += 15; reasons.append("interesse opportunità riservate")
    if profile.mortgage_needed:
        score += 5; reasons.append("esigenza mutuo identificata")
    score = min(100, score)
    cls = "CALDO" if score >= 70 else "TIEPIDO" if score >= 40 else "FREDDO"
    return {"score": score, "class": cls, "reasons": reasons}


def followup_plan(profile: BuyerProfile, captured_on: date | None = None) -> list[dict]:
    captured_on = captured_on or date.today()
    q = qualification_score(profile)
    if q["class"] == "CALDO":
        offsets = [(0, "Consegna immediata + verifica ricezione"), (1, "Contatto personale e prequalifica"), (3, "Invio immobili coerenti / proposta appuntamento"), (7, "Aggiornamento opportunità")]
    elif q["class"] == "TIEPIDO":
        offsets = [(0, "Consegna immediata"), (2, "Domanda di qualificazione"), (7, "Contenuto utile + immobili coerenti"), (21, "Aggiornamento ricerca")]
    else:
        offsets = [(0, "Consegna immediata"), (7, "Contenuto educativo"), (21, "Check interesse"), (45, "Nuovo contenuto / aggiornamento mercato")]
    return [{"day": n, "date": (captured_on + timedelta(days=n)).isoformat(), "action": action} for n, action in offsets]


def lead_record(name: str, email: str, phone: str, consent: bool, profile: BuyerProfile, source: str = "landing") -> dict:
    if not consent:
        raise ValueError("Il consenso/privacy richiesto per il trattamento non risulta accettato.")
    if not email.strip() and not phone.strip():
        raise ValueError("Serve almeno un recapito tra email e telefono.")
    offer = choose_offer(profile)
    score = qualification_score(profile)
    return {
        "captured_on": date.today().isoformat(),
        "name": name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "source": source,
        "consent": True,
        "profile": asdict(profile),
        "lead_magnet": asdict(offer),
        "qualification": score,
        "crm_stage": "Acquirente - nuovo lead",
        "next_action": followup_plan(profile)[0],
    }


def generate_capture_landing(brand: str, profile: BuyerProfile, output_file: str | Path, privacy_url: str = "#") -> Path:
    offer = choose_offer(profile)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    locality = escape(profile.locality or "la tua zona")
    title = escape(offer.title)
    promise = escape(offer.promise)
    privacy = escape(privacy_url, quote=True)
    html = f'''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{margin:0;font-family:Arial,sans-serif;background:#f3f5f3;color:#17211b}}main{{max-width:960px;margin:auto;padding:30px}}.hero{{background:#0e2017;color:#fff;border-radius:24px;padding:42px}}h1{{font-size:clamp(34px,6vw,58px);margin:8px 0}}.grid{{display:grid;grid-template-columns:1.2fr .8fr;gap:18px;margin-top:18px}}.card{{background:#fff;border-radius:18px;padding:24px}}label{{display:block;font-weight:700;margin:12px 0 5px}}input,select{{width:100%;box-sizing:border-box;padding:12px;border:1px solid #ccd4cf;border-radius:9px}}button{{width:100%;padding:15px;border:0;border-radius:10px;background:#197447;color:#fff;font-weight:800;margin-top:16px}}small{{color:#66736b}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><main>
<section class="hero"><div>{escape(brand.upper())}</div><h1>{title}</h1><p>{promise}</p><p>Area di interesse: <strong>{locality}</strong></p></section>
<div class="grid"><section class="card"><h2>Cosa ricevi</h2><p>{promise}</p><p>Il contenuto viene consegnato dopo l'invio del modulo. Le eventuali liste riservate includono soltanto immobili realmente disponibili.</p></section>
<section class="card"><h2>Ricevilo ora</h2><form method="post" action="{{{{FORM_ENDPOINT}}}}"><label>Nome</label><input name="name" required><label>Email</label><input name="email" type="email"><label>Telefono</label><input name="phone" type="tel"><label>Quando vuoi acquistare?</label><select name="timeframe"><option>Entro 3 mesi</option><option>3-6 mesi</option><option>6-12 mesi</option><option>Sto iniziando a informarmi</option></select><label><input style="width:auto" type="checkbox" name="consent" required> Accetto l'informativa privacy</label><small><a href="{privacy}">Leggi l'informativa privacy</a></small><button type="submit">Ricevi il contenuto</button></form></section></div></main></body></html>'''
    output_file.write_text(html, encoding="utf-8")
    return output_file


def dump_record(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2)
