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

Prezzi e sconti non sono mostrati nel sito. Eventuali valori storici in `dati.json` non sono dati aggiornati e non devono essere usati per affermare offerte attuali. La visualizzazione futura richiede una fonte autorizzata da Amazon e il rispetto delle condizioni applicabili.

Il workflow `.github/workflows/robot.yml` resta sospeso. Non esegue `scraper.py` e non ha una pianificazione.
