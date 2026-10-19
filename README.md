# Il Consiglio del Compratore

Catalogo statico pubblicato con GitHub Pages. La pagina legge `dati.json`.

## Gestione dei prodotti

- Modificare `dati.json` per aggiungere, sostituire o mettere in evidenza un prodotto.
- Conservare il link affiliato esatto del proprietario; non ricavare tag da nomi utente o domini.
- Usare `descrizione` per spiegare a chi serve il prodotto e `limite` per gli aspetti da valutare. Non dichiarare prove personali non svolte.
- Inserire in `immagine` solo immagini di cui è consentito l'uso. Senza immagine la scheda rimanda alle foto su Amazon.
- `featured: true` porta il prodotto in cima al catalogo.
- Verificare che la destinazione corrisponda al prodotto e alla variante indicata prima di sostituirlo.
- Conservare i prodotti rimossi in `catalogo-archiviato.json` con motivo e data del controllo. Allineare `links.txt` per evitare che una futura importazione li reinserisca.

## Selezione del 19 ottobre 2026

Aggiunti Logitech MK295, portapane KARL HAUSMANN e kit pittura Zenacolor da link affiliati già presenti in `links.txt`. Archiviato il MacBook Air M4 perché la pagina collegata risultava non disponibile. Otto prodotti hanno un consiglio e un aspetto da valutare; le categorie degli accessori per animali sono state corrette.

Il controllo è puntuale: non implica disponibilità futura. Le tre nuove schede rimandano alle foto su Amazon.

## Prezzi e automazioni

La pagina supporta prezzi e sconti attraverso `price-display.js`. Per mostrarli serve una `offerta` ottenuta dalle API Amazon, con valuta EUR, data del controllo e scadenza. Il catalogo attuale non contiene offerte autorizzate aggiornate: i valori storici `prezzo` vengono ignorati. Il collegamento alle API dell'account resta da configurare quando Amazon ne abilita l'accesso.

Formato della proprietà `offerta` di un prodotto (i seguenti dati sono esclusivamente un esempio e non sono nel catalogo pubblicato):

```json
{
  "amount": 80,
  "currency": "EUR",
  "source": "amazon-creators-api",
  "checkedAt": "2026-10-19T09:00:00Z",
  "expiresAt": "2026-10-19T10:00:00Z",
  "referenceAmount": 100,
  "referenceType": "list"
}
```

`source` ammette `amazon-creators-api` e `amazon-pa-api`; l'etichetta di provenienza non prova da sola l'autorizzazione. `referenceType` distingue prezzo consigliato (`list`) e prezzo precedente (`previous`), da copiare secondo il significato del dato fornito dalla fonte. Senza riferimento valido viene mostrato solo il prezzo corrente. Coupon, rate e abbonamenti non si trasformano automaticamente in sconti sul prezzo singolo.

Ogni prezzo mostra data e ora del controllo e un avviso sulla sua variabilità. Le offerte scadute, prive di timestamp o con validità oltre 24 ore vengono nascoste. La scadenza è ricontrollata ogni minuto e quando la pagina torna in primo piano. Un formato prezzo servito direttamente da Amazon va incorporato usando il suo formato ufficiale, non importato come JSON.

Verifica del modulo: `node --test test/price-display.test.cjs`.

Il workflow `.github/workflows/robot.yml` resta sospeso. Non esegue `scraper.py` e non ha una pianificazione.
