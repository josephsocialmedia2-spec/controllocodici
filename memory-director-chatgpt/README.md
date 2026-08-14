# Memory Director - ChatGPT Dedicated

Questa edizione usa come motore principale una conversazione ChatGPT dedicata:

`https://chatgpt.com/c/6a7e69a9-b370-83ed-9092-86a0dca7d308`

## Flusso

1. Incolla il materiale da memorizzare.
2. Premi **PREPARA + APRI CHATGPT**.
3. Il programma copia negli appunti il prompt mnemonico e apre la conversazione dedicata.
4. In ChatGPT premi **CTRL+V** e **INVIO**.
5. Copia la risposta JSON completa di ChatGPT.
6. Torna in Memory Director e premi **IMPORTA RISPOSTA DAGLI APPUNTI**.
7. Puoi visualizzare la seduta, avviare la voce guidata e usare Active Recall.

## Perche questo passaggio e manuale

L'URL `chatgpt.com/c/...` e una conversazione dell'interfaccia ChatGPT, non un endpoint API. L'app quindi non automatizza la UI del browser: apre la chat esatta e usa gli appunti per trasferire prompt e risposta in modo stabile.

## Requisiti

- Windows
- accesso a ChatGPT nel browser
- connessione Internet
- sintesi vocale Windows SAPI per la voce guidata

## Test

Il workflow GitHub Actions compila il programma su Windows e lancia i self-test inclusi nell'EXE prima di pubblicare l'artefatto.
