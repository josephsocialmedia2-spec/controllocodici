"""Real-estate Ads Engine: planning, landing generation and KPI decisions.

Standard-library only. It prepares campaign packages but does not publish ads;
platform credentials and account authorization belong to separate connectors.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlencode
import json
import re


@dataclass
class CampaignInput:
    campaign_name: str
    platform: str
    objective: str
    ad_format: str
    locality: str
    property_type: str
    property_address: str
    price: float = 0.0
    description: str = ""
    media_refs: str = ""
    video_ref: str = ""
    daily_budget: float = 0.0
    target_cpl: float = 20.0
    start_date: str = ""
    end_date: str = ""
    retargeting: bool = True
    landing_url: str = ""


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9àèéìòùÀÈÉÌÒÙ]+", "-", value or "").strip("-").lower()
    return value or "immobile"


def choose_format(requested: str, media_refs: str, video_ref: str) -> str:
    requested = (requested or "Auto").strip()
    if requested != "Auto":
        return requested
    photos = [x.strip() for x in (media_refs or "").split(";") if x.strip()]
    if video_ref.strip():
        return "Video tour"
    if len(photos) >= 3:
        return "Carousel"
    return "Immagine singola"


def build_utm_url(base_url: str, platform: str, campaign_name: str) -> str:
    base_url = (base_url or "").strip()
    if not base_url:
        return ""
    sep = "&" if "?" in base_url else "?"
    params = {
        "utm_source": "meta" if "meta" in platform.lower() else "google",
        "utm_medium": "paid_social" if "meta" in platform.lower() else "cpc",
        "utm_campaign": _slug(campaign_name),
        "utm_content": "f1_ads_engine",
    }
    return base_url + sep + urlencode(params)


def build_plan(data: CampaignInput) -> dict:
    fmt = choose_format(data.ad_format, data.media_refs, data.video_ref)
    loc = data.locality.strip() or "microzona dell'immobile"
    ptype = data.property_type.strip() or "immobile"
    price_txt = f"€ {data.price:,.0f}".replace(",", ".") if data.price else "prezzo su richiesta"
    headline = f"{ptype} a {loc} — {price_txt}"
    primary = (
        f"Scopri questo {ptype.lower()} a {loc}. Foto, caratteristiche e informazioni complete "
        "in una pagina dedicata. Richiedi i dettagli o prenota un contatto senza impegno."
    )
    return {
        "version": "1.0",
        "generated_on": date.today().isoformat(),
        "category": "Housing / Real Estate",
        "platform": data.platform,
        "objective": data.objective,
        "format": fmt,
        "creative": {
            "headline": headline,
            "primary_text": primary,
            "cta": "Scopri l'immobile",
            "media_rule": "Video tour se disponibile; altrimenti carousel con 3+ immagini; altrimenti immagine singola.",
        },
        "audience": {
            "geo": loc,
            "rule": "Target geografico coerente con immobile e bacino commerciale. Nessuna esclusione o selezione basata su attributi protetti.",
            "meta": (
                "Trattare la campagna come Housing. Usare solo opzioni di pubblico disponibili e consentite "
                "nell'account; evitare segmentazioni demografiche discriminatorie o inferenze su attributi protetti."
            ),
            "google": (
                "Priorità a Search con intento locale: tipologia + comune, case in vendita + comune, "
                "appartamento/casa + comune. Aggiungere audience solo se consentite dalla policy applicabile."
            ),
        },
        "retargeting": {
            "enabled": bool(data.retargeting),
            "rule": (
                "Usare esclusivamente audience first-party/visitatori/engager raccolti con base giuridica e consenso "
                "quando richiesto, e solo se la piattaforma consente il retargeting per la campagna Housing."
            ),
            "windows": ["7 giorni", "30 giorni"],
        },
        "landing": {
            "required": True,
            "utm_url": build_utm_url(data.landing_url, data.platform, data.campaign_name),
            "must_have": ["foto/video", "prezzo", "zona", "caratteristiche", "CTA", "contatto", "privacy/cookie"],
        },
        "budget": {"daily_budget": float(data.daily_budget or 0), "target_cpl": float(data.target_cpl or 0)},
        "automation": {
            "cycle": "CREA → PUBBLICA/ATTIVA CON ACCOUNT AUTORIZZATO → MISURA → OTTIMIZZA → RETARGETING",
            "review_rule": "Valutare dopo un volume minimo di click/spesa; non interrompere una campagna solo per poche impression.",
        },
    }


def kpi_decision(impressions: int, clicks: int, leads: int, spend: float, target_cpl: float = 20.0) -> dict:
    impressions = max(0, int(impressions or 0))
    clicks = max(0, int(clicks or 0))
    leads = max(0, int(leads or 0))
    spend = max(0.0, float(spend or 0))
    target_cpl = max(0.01, float(target_cpl or 20.0))
    ctr = (clicks / impressions * 100.0) if impressions else 0.0
    cpc = (spend / clicks) if clicks else 0.0
    cpl = (spend / leads) if leads else 0.0
    click_to_lead = (leads / clicks * 100.0) if clicks else 0.0
    if impressions < 1000 and clicks < 20 and spend < target_cpl:
        decision, reason = "RACCOGLI DATI", "Volume ancora insufficiente per una decisione affidabile."
    elif clicks >= 30 and leads == 0:
        decision, reason = "OTTIMIZZA LANDING/OFFERTA", "Traffico presente ma nessun lead: controllare pagina, CTA e proposta."
    elif impressions >= 1500 and ctr < 0.7:
        decision, reason = "CAMBIA CREATIVITÀ", "CTR basso: testare nuova apertura, foto/video o headline."
    elif leads > 0 and cpl > target_cpl * 1.35:
        decision, reason = "OTTIMIZZA TARGET/COSTI", "CPL sopra la soglia obiettivo."
    elif leads >= 2 and cpl <= target_cpl:
        decision, reason = "CONTINUA", "CPL in obiettivo con conversioni presenti."
    else:
        decision, reason = "TEST A/B", "Dati intermedi: mantenere la campagna e testare una sola variabile per volta."
    return {
        "decision": decision,
        "reason": reason,
        "ctr": round(ctr, 2),
        "cpc": round(cpc, 2),
        "cpl": round(cpl, 2) if leads else None,
        "click_to_lead": round(click_to_lead, 2),
    }


def generate_landing(data: CampaignInput, output_file: str | Path) -> Path:
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    photos = [x.strip() for x in (data.media_refs or "").split(";") if x.strip()]
    title = f"{data.property_type or 'Immobile'} a {data.locality or 'zona'}"
    price_txt = f"€ {data.price:,.0f}".replace(",", ".") if data.price else "Prezzo su richiesta"
    gallery = "".join(f'<figure><img src="{escape(src, quote=True)}" alt="{escape(title)}" loading="lazy"></figure>' for src in photos)
    video = f'<p><a class="button secondary" href="{escape(data.video_ref, quote=True)}" target="_blank" rel="noopener">Guarda il video tour</a></p>' if data.video_ref.strip() else ""
    desc = escape(data.description or "Richiedi informazioni per ricevere tutti i dettagli dell'immobile.")
    address = escape(data.property_address or data.locality)
    html = f'''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title>
<style>body{{margin:0;font-family:Arial,sans-serif;background:#f5f5f2;color:#17211b}}main{{max-width:1100px;margin:auto;padding:28px}}.hero{{background:#0e2017;color:white;padding:38px;border-radius:24px}}h1{{font-size:clamp(32px,6vw,62px);margin:0 0 10px}}.price{{font-size:28px;font-weight:800}}.gallery{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:22px 0}}figure{{margin:0}}img{{width:100%;height:260px;object-fit:cover;border-radius:16px;background:#ddd}}.card{{background:white;padding:24px;border-radius:18px;margin-top:16px}}.button{{display:inline-block;background:#197447;color:white;padding:14px 20px;border-radius:10px;text-decoration:none;font-weight:800}}.secondary{{background:#19324a}}small{{color:#68756d}}</style></head><body><main>
<section class="hero"><div>F1 IMMOBILIARE</div><h1>{escape(title)}</h1><p>{address}</p><div class="price">{price_txt}</div></section><section class="gallery">{gallery}</section><section class="card"><h2>La proprietà</h2><p>{desc}</p>{video}<p><a class="button" href="#contatto">Richiedi informazioni</a></p></section><section class="card" id="contatto"><h2>Vuoi ricevere dettagli o fissare una visita?</h2><p>Contatta F1 Immobiliare e indica l'immobile <strong>{escape(data.campaign_name)}</strong>.</p><p><small>Inserire recapiti, informativa privacy e gestione consenso/cookie prima della pubblicazione online.</small></p></section></main></body></html>'''
    output_file.write_text(html, encoding="utf-8")
    return output_file


def dump_plan(plan: dict) -> str:
    return json.dumps(plan, ensure_ascii=False, indent=2)
