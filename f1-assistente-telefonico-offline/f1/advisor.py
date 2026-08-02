from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Advice:
    text: str
    category: str


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", normalized).strip()


class LocalAdvisor:
    DEFAULT_RESPONSES = {
        "NON_INTERESSATO": "Capisco. Le invio una presentazione breve, così potrà valutarla con calma quando sarà il momento.",
        "PIU_AVANTI": "Va bene. Quale periodo sarebbe più corretto per ricontattarla senza disturbarla?",
        "NESSUN_TEMPO": "Comprendo. Mi bastano dieci minuti in un momento concordato, senza farle perdere tempo oggi.",
        "GIA_SEGUITO": "Perfetto. Non voglio interferire: posso solo mostrarle un metodo promozionale complementare e poi decide lei.",
        "NON_FIRMO": "Non le sto chiedendo di firmare nulla. Le spiego il metodo e poi valuta liberamente.",
        "COSTO": "Prima di parlare di costo verifichiamo se il metodo può ridurre tempi, visite inutili e dispersione.",
        "CURIOSI": "Le visite vengono organizzate e filtrate, così si evita di perdere tempo con persone non realmente interessate.",
        "FACCIO_DA_SOLO": "È una scelta legittima. Posso comunque mostrarle come aumentare l’esposizione e organizzare meglio i contatti.",
        "PREZZO": "Il prezzo va sostenuto con dati, posizionamento e confronto con gli immobili concorrenti, non con tentativi casuali.",
        "INVIA_MATERIALE": "Certamente. Qual è l’indirizzo email o il numero migliore a cui inviare la presentazione?",
        "DOMANDA_CHI_SIETE": "Lavoro sulla promozione e comunicazione degli immobili, in affiancamento alla parte tecnica abilitata.",
        "DOMANDA_COSA_FATE": "Organizziamo presentazione, promozione, contatti e visite per evitare dispersione di tempo.",
        "APPUNTAMENTO": "Perfetto. Preferisce una breve chiamata organizzativa al mattino oppure nel pomeriggio?",
        "SALUTO": "Buongiorno, sono Joseph. Posso rubarle un minuto per spiegarle perché la sto contattando?",
        "ASCOLTO": "Capisco. Mi racconta qual è oggi la difficoltà principale che sta incontrando?",
    }

    RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("NON_FIRMO", ("non firmo", "non voglio firmare", "niente firma", "nessun contratto")),
        ("GIA_SEGUITO", ("gia seguito", "gia un agente", "gia qualcuno", "gia affidato", "gia incaricato")),
        ("NESSUN_TEMPO", ("non ho tempo", "sono occupato", "non posso parlare", "richiami", "sto lavorando")),
        ("COSTO", ("quanto costa", "costa troppo", "commissione", "prezzo del servizio", "troppo caro")),
        ("CURIOSI", ("curiosi", "perditempo", "visite inutili", "gente a vedere")),
        ("FACCIO_DA_SOLO", ("faccio da solo", "vendo da solo", "privatamente", "senza intermediari", "metto sui portali")),
        ("PREZZO", ("non abbasso", "prezzo", "valore", "svendere", "ribasso")),
        ("INVIA_MATERIALE", ("mandi", "invia", "email", "whatsapp", "materiale", "brochure", "presentazione")),
        ("DOMANDA_CHI_SIETE", ("chi siete", "chi e lei", "da dove chiama", "che societa")),
        ("DOMANDA_COSA_FATE", ("cosa fate", "come funziona", "in cosa consiste", "che metodo")),
        ("APPUNTAMENTO", ("va bene", "possiamo sentirci", "fissiamo", "appuntamento", "quando")),
        ("PIU_AVANTI", ("piu avanti", "in futuro", "non adesso", "fra qualche mese", "magari dopo")),
        ("NON_INTERESSATO", ("non interessato", "non sono interessato", "non siamo interessati", "non mi interessa", "non voglio", "lasci perdere", "no grazie")),
    )

    def __init__(self, script: str) -> None:
        self.script = ""
        self.responses = dict(self.DEFAULT_RESPONSES)
        self.update_script(script)

    def update_script(self, script: str) -> None:
        self.script = script or ""
        self.responses = dict(self.DEFAULT_RESPONSES)
        marker = re.compile(r"^\s*\[RISPOSTA:([A-Z0-9_]+)\]\s*$", re.IGNORECASE)
        lines = self.script.splitlines()
        for index, line in enumerate(lines):
            match = marker.match(line)
            if not match:
                continue
            category = match.group(1).upper()
            response_lines: list[str] = []
            for following in lines[index + 1:]:
                if marker.match(following):
                    break
                stripped = following.strip()
                if stripped:
                    response_lines.append(stripped)
                elif response_lines:
                    break
            if response_lines:
                self.responses[category] = " ".join(response_lines)

    @staticmethod
    def _contains_any(text: str, phrases: Iterable[str]) -> bool:
        return any(phrase in text for phrase in phrases)

    def suggest(self, customer_text: str, turns: list[dict[str, str]] | None = None) -> Advice:
        normalized = _normalize(customer_text)
        history = turns or []
        for category, phrases in self.RULES:
            if self._contains_any(normalized, phrases):
                return Advice(self.responses[category], category)
        if "?" in customer_text or normalized.startswith(("perche", "come", "cosa", "quando", "dove")):
            return Advice(self.responses["ASCOLTO"], "DOMANDA_APERTA")
        customer_turns = sum(1 for turn in history if turn.get("speaker") == "CLIENTE")
        if customer_turns == 0:
            return Advice(self.responses["SALUTO"], "APERTURA")
        return Advice(self.responses["ASCOLTO"], "ASCOLTO")
