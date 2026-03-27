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
        # Pausa per sembrare un umano e non farsi bloccare da Amazon
        time.sleep(2) 
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Cerca Titolo
        titolo_elem = soup.find(id='productTitle')
        titolo = titolo_elem.text.strip() if titolo_elem else "Titolo non trovato"

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
        print(f"Errore: {e}")

# Salva tutto nel file che leggerà il sito
with open('dati.json', 'w', encoding='utf-8') as f:
    json.dump(prodotti, f, ensure_ascii=False, indent=2)
print("Finito! Dati salvati con successo.")
