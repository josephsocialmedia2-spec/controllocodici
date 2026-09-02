# Real Estate Ads + Buyer Lead Engine

Strategia automatizzata condivisa per F1 Immobiliare e, dove pertinente, Real Media Pro.

## Flusso ADS

IMMOBILE → PIANO CAMPAGNA → CREATIVITÀ → TARGET GEO → LANDING → RETARGETING → KPI → DECISIONE.

## Flusso Lead Magnet Acquirenti

TRAFFICO → PROFILO ACQUIRENTE → LEAD MAGNET → CONSENSO → CONSEGNA → CRM → LEAD SCORE → FOLLOW-UP.

Il Lead Magnet Engine seleziona automaticamente l'offerta primaria:

- ricerca entro 90 giorni / interesse off-market → lista riservata, ma solo se esistono opportunità reali nel database;
- prima casa o necessità mutuo → Checklist Prima Casa;
- fase informativa → Guida pratica all'acquisto casa / 10 errori da evitare.

## Endpoint F1 live

Backend e landing sono distribuiti tramite Supabase Edge Function:

`https://nqnmlsmeiynxbdojeyjt.supabase.co/functions/v1/f1-lead-intake`

GET mostra la landing pubblica. POST registra e qualifica il lead. La lista riservata usa un URL tokenizzato e legge soltanto opportunità presenti in `f1_market_opportunities`.

## Database F1

Il funnel usa le tabelle:

- `f1_lead_magnets`: catalogo e URL dei contenuti;
- `f1_buyer_leads`: lead, UTM, score, temperatura, consensi e prossima azione;
- `f1_buyer_lead_events`: storico acquisizione/consegna/aperture lista;
- `f1_house_requests`: sincronizzazione con il CRM acquirenti già esistente;
- `f1_market_opportunities`: inventario reale usato per la lista riservata.

Le tabelle lead hanno RLS abilitato e nessun accesso diretto anon/authenticated. Le scritture pubbliche passano esclusivamente dalla Edge Function server-side.

## Lead magnet PDF

I PDF sono generati da `generate_lead_magnets.py` e ricostruiti automaticamente da GitHub Actions:

- `public/assets/F1_Guida_Acquisto_Casa_2026.pdf`
- `public/assets/F1_Checklist_Prima_Casa_2026.pdf`

Il workflow `Build F1 Lead Magnets` verifica che entrambi i file siano generati e non vuoti prima di committarli.

## Scoring e follow-up

Il motore registra zona, tipologia, budget, tempistica, mutuo e interesse per opportunità riservate. Produce score 0–100 e classe `FREDDO`, `TIEPIDO` o `CALDO`. La prima data di follow-up viene assegnata automaticamente: 1 giorno per CALDO, 3 per TIEPIDO, 7 per FREDDO.

## Email e WhatsApp

Gli adapter sono già presenti nell'Edge Function ma non contengono credenziali. Invio email richiede i secret `RESEND_API_KEY` e `FROM_EMAIL`. WhatsApp Cloud API richiede `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TEMPLATE_NAME` e facoltativamente `WHATSAPP_TEMPLATE_LANG`.

Fino alla configurazione dei secret, il lead riceve comunque il contenuto immediatamente nella pagina di conferma; lo stato dei canali viene tracciato come `unconfigured`.

## Regole operative

- Campagne immobiliari classificate Housing / Real Estate quando richiesto dalla piattaforma.
- Nessun targeting o esclusione basato su attributi protetti.
- Retargeting solo con audience e base giuridica consentite.
- Nessuna promessa di immobili off-market o riservati quando l'inventario reale è vuoto.
- Credenziali, token e dati personali non vengono pubblicati nel repository.

## F1 / Real Media Pro

F1 usa questo backend per acquisizione e qualificazione acquirenti. Real Media Pro riutilizza il core strategico, ma ogni cliente deve mantenere brand, CRM, dominio, account pubblicitari e database separati: i lead dei clienti RMP non devono finire nel database F1.