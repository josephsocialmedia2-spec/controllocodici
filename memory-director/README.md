# Memory Director

Applicazione Windows per trasformare concetti di studio in sedute di memorizzazione guidata basate su micro-concetti, film mentale, PAV, sensorialita e active recall.

## Architettura

Questa versione abbandona PowerShell e il server browser locale. E una applicazione **C# WinForms compilata** che comunica direttamente con Ollama su `http://127.0.0.1:11434` e usa il modello `qwen3:4b`.

## Avvio su Windows

1. Assicurarsi che Ollama sia in esecuzione e che `qwen3:4b` sia installato.
2. Fare doppio clic su `BUILD_AND_RUN.bat`.
3. Lo script compila prima un eseguibile di test, esegue i self-test e **solo se passano** compila e avvia `MemoryDirector.exe`.

## Test inclusi

- rimozione code fence JSON;
- costruzione del prompt mnemonico;
- validazione della struttura della seduta;
- parsing della risposta JSON annidata di Ollama.

GitHub Actions compila e testa il progetto su `windows-latest` a ogni modifica.
