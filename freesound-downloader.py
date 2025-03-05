import os
import requests
import json
import time
import argparse
from urllib.parse import quote

class FreeSoundDownloader:
    def __init__(self, api_key, output_dir="sounds"):
        """Inizializza il downloader con la chiave API e la directory di output"""
        self.api_key = api_key
        self.base_url = "https://freesound.org/apiv2"
        self.output_dir = output_dir
        self.sound_mappings = {}
        self.downloaded_sounds = {}
        self.headers = {
            "Authorization": f"Token {api_key}"
        }
        
        # Assicurati che la directory di output esista
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Crea il file di mappatura se non esiste
        self.mapping_file = os.path.join(output_dir, "sound_mappings.json")
        if os.path.exists(self.mapping_file):
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                self.sound_mappings = json.load(f)
    
    def search_sounds(self, query, sort="score", filter_params=None, max_results=5):
        """Cerca suoni su Freesound con i parametri specificati"""
        endpoint = f"{self.base_url}/search/text/"
        
        # Parametri di base per la ricerca
        params = {
            "query": query,
            "sort": sort,
            "fields": "id,name,previews,tags,duration,license",
            "page_size": max_results
        }
        
        # Aggiungi eventuali filtri
        if filter_params:
            params.update(filter_params)
        
        try:
            response = requests.get(endpoint, params=params, headers=self.headers)
            response.raise_for_status()
            results = response.json()
            return results.get("results", [])
        except Exception as e:
            print(f"Errore nella ricerca di '{query}': {str(e)}")
            return []
    
    def download_preview(self, sound, category):
        """Scarica la preview di un suono usando l'URL delle preview"""
        sound_id = sound["id"]
        sound_name = sound["name"]
        
        # Verifica se esiste già il file
        safe_name = ''.join(c if c.isalnum() or c in [' ', '.', '_', '-'] else '_' for c in sound_name)
        filename = f"{category}_{sound_id}_{safe_name}.mp3"
        filepath = os.path.join(self.output_dir, filename)
        
        if os.path.exists(filepath):
            print(f"File già esistente: {filename}")
            return filename
        
        try:
            # Ottieni l'URL della preview MP3
            if "previews" in sound and "preview-hq-mp3" in sound["previews"]:
                preview_url = sound["previews"]["preview-hq-mp3"]
            elif "previews" in sound and "preview-lq-mp3" in sound["previews"]:
                preview_url = sound["previews"]["preview-lq-mp3"]
            else:
                print(f"Nessuna preview MP3 disponibile per il suono {sound_id}")
                return None
            
            # Scarica il file
            print(f"Download della preview di '{sound_name}' ({sound_id})...")
            download_response = requests.get(preview_url)
            download_response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(download_response.content)
            
            print(f"Preview salvata come: {filename}")
            return filename
        
        except Exception as e:
            print(f"Errore nel download della preview del suono {sound_id}: {str(e)}")
            return None
    
    def find_and_download_sounds_for_category(self, category, query=None, max_sounds=2):
        """Trova e scarica suoni per una specifica categoria"""
        if not query:
            query = category.replace("_", " ")
        
        print(f"\nCerca suoni per: {category} (query: '{query}')")
        
        # Filtri per ottenere suoni di buona qualità e di durata appropriata
        filters = {
            "duration": "[1 TO 30]",  # Tra 1 e 30 secondi
            "license": "creative_commons"
        }
        
        sounds = self.search_sounds(query, filter_params=filters, max_results=max_sounds)
        
        if not sounds:
            print(f"Nessun suono trovato per '{category}'")
            return []
        
        # Scarica i suoni trovati
        downloaded_files = []
        for sound in sounds:
            # Scarica la preview invece del file originale
            filename = self.download_preview(sound, category)
            if filename:
                downloaded_files.append({
                    "filename": filename,
                    "name": sound["name"],
                    "id": sound["id"],
                    "tags": sound.get("tags", []),
                    "duration": sound.get("duration", 0)
                })
            
            # Evita di sovraccaricare l'API
            time.sleep(1)
        
        return downloaded_files
    
    def create_sound_hierarchy(self):
        """Crea una gerarchia di suoni basata sulle categorie"""
        # Definisci la gerarchia dei luoghi
        # Il formato è: {"categoria": ["suono_base_1", "suono_base_2", ...]}
        hierarchy = {
            # Luoghi base con suoni propri
            "bosco": ["natura", "uccelli", "vento tra alberi"],
            "foresta": ["natura", "uccelli", "vento tra alberi", "scricchiolio legno"],
            "foresta_magica": ["foresta", "creature magiche", "sussurri"],
            "lago": ["acqua", "splash", "rane"],
            "lago_magico": ["lago", "magia", "creature acquatiche"],
            "mare": ["onde", "gabbiani"],
            "fiume": ["acqua che scorre", "natura"],
            "castello": ["eco", "vento", "passi su pietra"],
            "castello_incantato": ["castello", "magia", "incantesimi"],
            "scuola": ["voci studenti", "campanella", "passi corridoio"],
            "scuola_di_magia": ["scuola", "incantesimi", "magia"],
            
            # Interni di edifici
            "casa": ["rumori domestici", "passi", "conversazioni"],
            "sala": ["conversazioni", "eco"],
            "sala_magica": ["sala", "magia", "incantesimi"],
            "biblioteca": ["silenzio", "pagine", "sussurri"],
            "biblioteca_proibita": ["biblioteca", "sussurri inquietanti", "magia oscura"],
            "dormitorio": ["russare", "conversazioni tranquille", "passi"],
            "cucina": ["pentole", "cibo", "conversazioni"],
            "aula": ["lezioni", "penne su carta", "studenti"],
            "aula_magica": ["aula", "incantesimi", "magia"],
            "ufficio": ["scartoffie", "conversazioni formali"],
            "sotterraneo": ["gocciolamento", "eco", "umidità"],
            
            # Edifici e costruzioni
            "negozio": ["clienti", "cassa", "conversazioni"],
            "negozio_magico": ["negozio", "magia", "oggetti magici"],
            "pub": ["conversazioni allegre", "bicchieri", "musica"],
            "pub_magico": ["pub", "conversazioni magiche", "creature magiche"],
            "taverna": ["pub", "cibo"],
            "ospedale": ["strumenti medici", "passi corridoio", "conversazioni basse"],
            "ospedale_magico": ["ospedale", "pozioni", "incantesimi curativi"],
            "torre": ["vento", "altezza", "eco"],
            "prigione": ["catene", "porte metalliche", "eco"],
            "carcere_magico": ["prigione", "creature magiche", "incantesimi"],
            "capanna": ["legno che scricchiola", "fuoco", "vento"],
            "tana": ["animali", "conversazioni familiari"],
            
            # Ambienti naturali
            "parco": ["natura", "conversazioni", "bambini"],
            "giardino": ["uccelli", "natura", "insetti"],
            "campo": ["vento sull'erba", "natura", "insetti"],
            "grotta": ["gocciolamento", "eco", "umidità"],
            "passaggio_segreto": ["porta segreta", "passi furtivi", "eco"],
            "stanza_segreta": ["porta segreta", "eco", "sussurri"],
            
            # Infrastrutture
            "strada": ["traffico", "passi", "conversazioni"],
            "stazione": ["treni", "annunci", "folla"],
            "stazione_magica": ["stazione", "magia", "creature magiche"],
            "veicolo": ["motore", "viaggio"],
            "veicolo_magico": ["magia di movimento", "volo"]
        }
        
        # Mappa i suoni base alle categorie
        base_sounds = {}
        for category, sound_types in hierarchy.items():
            # Cerca e scarica i suoni per questa categoria
            print(f"Elaborazione categoria: {category}")
            
            # Se la categoria è già stata elaborata, salta
            if category in self.sound_mappings:
                print(f"Categoria {category} già elaborata, utilizzo i dati esistenti.")
                continue
            
            # Altrimenti cerca e scarica i suoni
            category_sounds = self.find_and_download_sounds_for_category(category)
            
            # Trova anche i suoni base associati a questa categoria
            base_sound_files = []
            for sound_type in sound_types:
                if sound_type in base_sounds:
                    # Usa i suoni base già scaricati
                    base_sound_files.extend(base_sounds[sound_type])
                else:
                    # Scarica nuovi suoni base
                    sound_files = self.find_and_download_sounds_for_category(sound_type)
                    base_sounds[sound_type] = sound_files
                    base_sound_files.extend(sound_files)
            
            # Salva la mappatura per questa categoria
            self.sound_mappings[category] = {
                "direct_sounds": category_sounds,
                "base_sounds": base_sound_files
            }
            
            # Salva le mappature dopo ogni categoria per evitare perdite in caso di errore
            self.save_mappings()
    
    def save_mappings(self):
        """Salva le mappature dei suoni su file"""
        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.sound_mappings, f, ensure_ascii=False, indent=4)
        print(f"Mappature salvate in {self.mapping_file}")
    
    def get_sounds_for_category(self, category):
        """Restituisce i suoni per una specifica categoria"""
        if category in self.sound_mappings:
            return self.sound_mappings[category]
        return None

def main():
    parser = argparse.ArgumentParser(description='Scarica effetti sonori da FreeSound per ambientazioni')
    parser.add_argument('--api_key', required=True, help='FreeSound API key')
    parser.add_argument('--output_dir', default='sounds', help='Directory per salvare i suoni')
    
    args = parser.parse_args()
    
    downloader = FreeSoundDownloader(args.api_key, args.output_dir)
    downloader.create_sound_hierarchy()
    print("Download completato!")

if __name__ == "__main__":
    main()