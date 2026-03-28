import requests
from bs4 import BeautifulSoup
import json
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
}

prodotti = []

with open('links.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in lines:
    if not line.strip(): continue
    parts = line.split(',', 1)
    
    categoria = parts[0].strip() if len(parts) == 2 else "Generico"
    url = parts[1].strip() if len(parts) == 2 else parts[0].strip()

    print(f"Sto leggendo: {url}")
    
    try:
        time.sleep(2) 
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. Cerca Titolo
        titolo_elem = soup.find(id='productTitle')
        if not titolo_elem:
            print(f"-> Blocco Amazon o pagina non valida. Salto.")
            continue
        titolo = titolo_elem.text.strip()

        # 2. Cerca Prezzo (TENTATIVI MULTIPLI)
        prezzo = None
        
        # Tentativo A: Prezzo intero classico
        prezzo_elem = soup.find('span', class_='a-price-whole')
        
        # Tentativo B: Prezzo nascosto per lettori schermo (molto frequente ora)
        if not prezzo_elem:
            prezzo_elem = soup.find('span', class_='a-offscreen')
            
        # Tentativo C: Vecchi layout di Amazon
        if not prezzo_elem:
            prezzo_elem = soup.find(id='priceblock_ourprice') or soup.find(id='priceblock_dealprice')

        # Se trova uno di questi, lo pulisce e lo trasforma in numero
        if prezzo_elem:
            prezzo_str = prezzo_elem.text.replace('€', '').replace('EUR', '').replace('.', '').replace(',', '.').replace('\u202f', '').strip()
            try: 
                prezzo = float(prezzo_str)
            except: 
                pass
        
        # 3. Cerca Immagine
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

with open('dati.json', 'w', encoding='utf-8') as f:
    json.dump(prodotti, f, ensure_ascii=False, indent=2)
print("Finito! Dati salvati con successo.")
