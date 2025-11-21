# ilconsigliodelcompratore

## Script Google Apps Script
Copia tutto il contenuto di `apps-script.gs` in un nuovo progetto Google Apps Script collegato al tuo foglio. Compila `ACCESS_KEY`, `SECRET_KEY` e `ASSOCIATE_TAG`, poi esegui manualmente `aggiornaProdottiDaAmazon()`.

## Pubblicare il CSV del foglio
1. Nel foglio Google: File → Condividi → Pubblica sul web → scegli il foglio corretto → formato CSV → Pubblica.
2. Copia l'URL generato e incollalo in `index.html` nella costante `CSV_URL`.

## Sito statico
Usa `index.html` così com'è (GitHub Pages o qualsiasi hosting statico). L'unica modifica da fare è l'URL CSV pubblicato.
