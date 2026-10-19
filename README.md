# Il Consiglio del Compratore

Catalogo statico pubblicato con GitHub Pages. La pagina legge `dati.json`.

## Gestione dei prodotti

- Modificare `dati.json` per aggiungere, sostituire o mettere in evidenza un prodotto.
- Conservare il link affiliato esatto del proprietario; non ricavare tag da nomi utente o domini.
- Usare `descrizione` per spiegare a chi serve il prodotto e `limite` per gli aspetti da valutare. Non dichiarare prove personali non svolte.
- `featured: true` porta il prodotto in cima al catalogo.
- Verificare prodotto e variante prima di sostituirli.
- Conservare i prodotti rimossi in `catalogo-archiviato.json` con motivo e data.
- `links.txt` resta un elenco editoriale: lo scraper aggiorna solo i prodotti già selezionati in `dati.json`, senza importare automaticamente gli altri link.

## Aggiornamento automatico

Su richiesta del proprietario, lo scraper viene riattivato con il workflow `.github/workflows/robot.yml`:

- esecuzione ogni sei ore, alle 00:17, 06:17, 12:17 e 18:17 UTC;
- avvio manuale da GitHub Actions → Robot Prezzi Amazon → Run workflow;
- avvio quando cambia il codice dello scraper o del workflow;
- aggiornamento delle sole offerte, senza sovrascrivere descrizioni, immagini, categorie, selezioni o link affiliati;
- salvataggio del rapporto `scraper-report.json` nel repository e come artefatto del workflow;
- richiesta esplicita di pubblicazione GitHub Pages dopo il commit automatico (i commit fatti con `GITHUB_TOKEN` non avviano da soli la pubblicazione).

GitHub può ritardare le esecuzioni pianificate. In caso di pagina bloccata, timeout o prezzo non leggibile, l'offerta precedente non viene rinnovata artificialmente. La scadenza resta quella del suo controllo effettivo. Se nessun prezzo viene raccolto, il workflow segnala un errore e conserva il catalogo.

Lo scraper legge pagine pubbliche Amazon con richieste HTTP ordinarie: non richiede l'API prodotti, non supera CAPTCHA e non garantisce che Amazon renda sempre disponibile il contenuto. La fonte è registrata come `amazon-page`, distinta dalle API. Questa implementazione non modifica le condizioni del programma di affiliazione.

## Visualizzazione dei prezzi

`price-display.js` usa la proprietà `offerta` del prodotto:

```json
{
  "amount": 80,
  "currency": "EUR",
  "source": "amazon-page",
  "checkedAt": "2026-10-19T09:00:00Z",
  "expiresAt": "2026-10-19T21:00:00Z",
  "referenceAmount": 100,
  "referenceType": "list"
}
```

L'esempio non è un'offerta reale. Lo scraper assegna una validità di 12 ore e rileva il prezzo dell'acquisto singolo del prodotto principale. Rate, abbonamenti e coupon non diventano automaticamente un prezzo scontato. Il riferimento barrato deve essere esplicitamente etichettato dalla pagina: `list` indica prezzo consigliato/listino, `previous` un prezzo precedente. Senza riferimento leggibile viene mostrato solo il prezzo corrente.

La scheda mostra data e ora del controllo. I vecchi valori `prezzo` senza data, le offerte scadute e quelle malformate non vengono mostrate. La scadenza è ricontrollata ogni minuto e al ritorno sulla scheda del browser. Le fonti API `amazon-creators-api` e `amazon-pa-api` restano supportate.

## Verifiche

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test test/price-display.test.cjs
python scraper.py --limit 1 --delay 0
```

L'ultimo comando verifica un prodotto reale e aggiorna la sua offerta nel catalogo locale, mantenendo tutti gli altri prodotti.
