# Memory Director - ChatGPT dedicato

Build Windows C# testata con GitHub Actions.

## Modalita principale: ChatGPT web dedicato

La conversazione usata e:

`https://chatgpt.com/c/6a7a16c8-8a94-83eb-9492-001e95b12c67`

Il programma non tenta di pilotare internamente il sito ChatGPT. L'API ufficiale OpenAI non consente di inviare messaggi direttamente a una conversazione web esistente identificata da un URL `/c/...`.

Flusso:

1. Incolla il materiale da memorizzare.
2. Premi **COPIA PROMPT + APRI CHATGPT**.
3. Nella conversazione ChatGPT dedicata premi `CTRL+V` e invia.
4. ChatGPT restituisce il JSON della seduta.
5. Copia la risposta completa.
6. Torna a Memory Director e premi **IMPORTA RISPOSTA CHATGPT**.
7. La seduta diventa disponibile per voce guidata e active recall.

## Fallback Ollama

Resta disponibile **GENERA CON OLLAMA** usando `qwen3:4b` locale su `http://127.0.0.1:11434`.

## Test

La CI Windows compila l'EXE e avvia `--self-test`. I test verificano anche l'URL della conversazione ChatGPT dedicata e non richiedono rete.
