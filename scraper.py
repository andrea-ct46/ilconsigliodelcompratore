import requests
from bs4 import BeautifulSoup
import json
import time
import os

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
}

prodotti = []

# Legge i link dal tuo file
with open('links.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in lines:
    if not line.strip(): continue
    parts = line.split(',', 1)
    
    categoria = parts[0].strip() if len(parts) == 2 else "Generico"
    url = parts[1].strip() if len(parts) == 2 else parts[0].strip()

    print(f"Sto leggendo: {url}")
    
    try:
        # Pausa per sembrare un umano
        time.sleep(2) 
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Cerca Titolo
        titolo_elem = soup.find(id='productTitle')
        
        # TRUCCO ANTIBLOCCO: Se non trova il titolo, significa che Amazon ha bloccato la pagina.
        # In questo caso saltiamo il prodotto per non mettere card vuote sul sito!
        if not titolo_elem:
            print(f"-> Amazon ha bloccato la lettura di questo link. Lo salto.")
            continue # Passa al link successivo

        titolo = titolo_elem.text.strip()

        # Cerca Prezzo
        prezzo = None
        prezzo_elem = soup.find('span', class_='a-price-whole')
        if prezzo_elem:
            prezzo_str = prezzo_elem.text.replace(',', '.').replace('\u202f', '').strip()
            try: prezzo = float(prezzo_str)
            except: pass
        
        # Cerca Immagine
        img_elem = soup.find(id='landingImage') or soup.find(id='imgBlkFront')
        immagine = img_elem['src'] if img_elem and 'src' in img_elem.attrs else ""

        prodotti.append({
            "titolo": titolo,
            "descrizione": "",
            "immagine": immagine,
            "link": url,
            "categoria": categoria,
            "prezzo": prezzo,
            "featured": False
        })
    except Exception as e:
        print(f"Errore su {url}: {e}")

# Salva tutto nel file
with open('dati.json', 'w', encoding='utf-8') as f:
    json.dump(prodotti, f, ensure_ascii=False, indent=2)
print("Finito! Dati salvati con successo.")
