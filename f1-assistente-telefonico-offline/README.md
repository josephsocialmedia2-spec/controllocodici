# F1 Assistente Telefonico Offline

Applicazione desktop Windows che ascolta contemporaneamente la voce del cliente e il microfono dell'operatore, trascrive entrambe in italiano con Vosk e propone localmente la frase successiva da dire.

## Funzioni

- Trascrizione continua di CLIENTE e JOSEPH in due canali separati.
- Acquisizione da Phone Link, Voicemeeter, VB-CABLE, Stereo Mix o loopback.
- Motore locale di suggerimento basato su obiezioni e script modificabili.
- Nessuna API o invio dell'audio a servizi cloud.
- Autosalvataggio e archivio finale con `trascrizione.txt`, `riepilogo.txt` e `sessione.json`.
- Modalità demo e diagnostica dei dispositivi audio.

## Installazione

1. Scaricare la cartella `f1-assistente-telefonico-offline`.
2. Eseguire `INSTALLA_E_AVVIA.bat`.
3. Attendere l'installazione e il download del modello italiano Vosk.
4. In CONFIGURAZIONE selezionare il canale del cliente e il microfono di Joseph.

Serve Python 64 bit, preferibilmente 3.11 o 3.12. Internet serve soltanto durante la prima installazione.

## Configurazione audio

Per CLIENTE selezionare un dispositivo che contenga soltanto l'audio ricevuto: `Voicemeeter Output (B1)`, `CABLE Output`, Phone Link, Stereo Mix o il loopback dell'altoparlante. Per JOSEPH selezionare il microfono usato durante la telefonata.

La separazione funziona soltanto se il canale cliente non contiene anche il microfono dell'operatore.

## Uso

1. Compilare contatto, telefono e comune.
2. Scegliere lo script.
3. Premere AVVIA ASCOLTO.
4. Premere TERMINA per chiudere e salvare.

L'archivio viene creato in `Documenti/F1 Assistente Telefonico/Chiamate`.

## Script personalizzati

I file `.txt` sono nella cartella `scripts`. Una risposta può essere sostituita così:

```text
[RISPOSTA:NON_INTERESSATO]
Testo personalizzato da mostrare.
```

Categorie: `NON_INTERESSATO`, `PIU_AVANTI`, `NESSUN_TEMPO`, `GIA_SEGUITO`, `NON_FIRMO`, `COSTO`, `CURIOSI`, `FACCIO_DA_SOLO`, `PREZZO`, `INVIA_MATERIALE`, `DOMANDA_CHI_SIETE`, `DOMANDA_COSA_FATE`, `APPUNTAMENTO`.

## Verifica

```bat
.venv\Scripts\python.exe -m compileall -q app.py f1 tools tests
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Il programma salva solo testo, metadati e suggerimenti; non registra file audio. L'utilizzatore deve rispettare la normativa applicabile sulla trascrizione delle chiamate.