# Autonomous Software Agent

Agente Windows per acquisire un progetto, creare una baseline, eseguire test reali, proporre correzioni tramite Ollama, applicare modifiche solo in una copia di lavoro, ripetere i test e mantenere la migliore versione verificata.

## Flusso

`INBOX -> ORIGINAL -> WORK -> TEST -> REPAIR -> RETEST -> BEST -> REPORT -> NOTIFICA`

Gli originali non vengono sovrascritti. I comandi distruttivi di sistema sono bloccati. Il ramo/main dei repository esterni non viene modificato dal programma.

## Uso operativo

Dopo l'installazione l'agente parte automaticamente all'accesso Windows e sorveglia:

`Documenti\AutonomousSoftwareAgent\INBOX`

Inserire una cartella progetto oppure uno ZIP. Facoltativamente aggiungere `job.json`.

### Esempio job software

```json
{
  "name": "mio-programma",
  "type": "software",
  "source": {"type": "local", "path": "C:\\Percorso\\Programma"},
  "test_commands": ["python -m pytest -q"],
  "max_iterations": 3
}
```

### Esempio repository GitHub

```json
{
  "name": "open-social-scheduler",
  "type": "software",
  "source": {
    "type": "github",
    "url": "https://github.com/josephsocialmedia2-spec/open-social-scheduler.git",
    "branch": "main"
  },
  "test_commands": ["npm test", "npm run build"]
}
```

### Foto libro -> testo -> audiolibro

```json
{
  "name": "libro-01",
  "type": "book",
  "source": {"type": "local", "path": "C:\\FotoLibro"},
  "synthesize_audio": true
}
```

Output: `testo_ocr_fedele.txt`, `testo_tts_pulito.txt`, `report_ocr.json`, segmenti WAV e `audiolibro_finale.wav` su Windows.

## Motore di correzione

Default: Ollama locale su `http://127.0.0.1:11434`, modello `qwen2.5-coder:7b`. Modificare `Documenti\AutonomousSoftwareAgent\config.json` per usare un altro modello.

## Notifiche

- notifica desktop Windows al completamento;
- email tramite Outlook desktop configurato, oppure SMTP impostando `config.json` e la password in una variabile ambiente.

## QA del pacchetto

Il workflow GitHub Windows esegue: pytest -> self-test autoriparazione -> PyInstaller -> self-test EXE -> compilazione installer -> installazione silenziosa su Windows runner -> self-test dell'EXE installato. L'installer viene pubblicato come artifact solo se tutti questi controlli passano.
