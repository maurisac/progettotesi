import os
import json
import random
import difflib

class SoundEnvironment:
    def __init__(self, sounds_dir="sounds"):
        """Inizializza l'ambiente sonoro"""
        self.sounds_dir = sounds_dir
        self.sound_mappings_file = os.path.join(sounds_dir, "sound_mappings.json")
        self.sound_mappings = {}
        
        # Carica le mappature dei suoni se il file esiste
        if os.path.exists(self.sound_mappings_file):
            with open(self.sound_mappings_file, 'r', encoding='utf-8') as f:
                self.sound_mappings = json.load(f)
        else:
            print(f"Attenzione: file delle mappature sonore non trovato in {self.sound_mappings_file}")
        
        # Mappa categorie simili
        self.category_mapping = {
            "città": "strada",
            "paese": "strada",
            "villaggio": "strada",
            "villaggio_magico": "strada",
            "palazzo": "castello",
            "università": "scuola",
            "montagna": "natura",
            "oceano": "mare",
            "piazza": "strada",
            "edificio": "casa",
            "chiesa": "sala",
            "cattedrale": "sala",
            "tempio": "sala",
            "ristorante": "pub",
            "hotel": "casa",
            "teatro": "sala",
            "cinema": "sala",
            "museo": "sala",
            "libreria": "biblioteca",
            "aeroporto": "stazione",
            "porto": "mare",
            "isola": "mare",
            "spiaggia": "mare",
            "deserto": "natura",
            "bar": "pub",
            "caffetteria": "pub",
            "supermercato": "negozio",
            "mercato": "negozio",
            "fattoria": "campo",
            "mulino": "campo",
            "miniera": "grotta",
            "fortezza": "castello",
            "accademia": "scuola",
            "osservatorio": "torre",
            "laboratorio": "ufficio",
            "bunker": "sotterraneo",
            "caserma": "dormitorio",
            "manicomio": "ospedale",
            "cimitero": "natura",
            "stadio": "campo",
            "arena": "campo",
            "campo_da_battaglia": "campo",
            "base_militare": "caserma",
            "monastero": "castello",
            "santuario": "sala_magica",
            "oasi": "natura",
            "ghiacciaio": "natura",
            "vulcano": "natura",
            "gola": "natura",
            "cascata": "fiume",
            "baia": "mare",
            "diga": "fiume",
            "faro": "torre",
            "labirinto": "passaggio_segreto",
            "scuola di magia": "scuola_di_magia",
            "villaggio magico": "villaggio_magico",
            "luogo magico": "sala_magica",
            "negozio magico": "negozio_magico",
            "edificio magico": "castello_incantato",
            "stazione magica": "stazione_magica"
        }
    
    def is_category_supported(self, category):
        """Verifica se la categoria è direttamente supportata"""
        normalized_category = category.lower().replace(' ', '_')
        return normalized_category in self.sound_mappings
    
    def find_similar_category(self, category):
        """Trova una categoria simile se quella esatta non esiste"""
        # Normalizza la categoria
        normalized_category = category.lower().replace(' ', '_')
        
        # Controlla nella mappatura diretta
        if normalized_category in self.category_mapping:
            return self.category_mapping[normalized_category]
        
        # Controlla anche la versione con spazi
        if category.lower() in self.category_mapping:
            return self.category_mapping[category.lower()]
        
        # Usa difflib per trovare la categoria più simile
        categories = list(self.sound_mappings.keys())
        if categories:
            matches = difflib.get_close_matches(normalized_category, categories, n=1, cutoff=0.6)
            if matches:
                return matches[0]
        
        # Fallback a "natura" se esiste, altrimenti usa la prima categoria disponibile
        if "natura" in self.sound_mappings:
            return "natura"
        elif categories:
            return categories[0]
        
        return None
        
    def get_sounds_for_location(self, location_category, max_sounds=3):
        """
        Restituisce una lista di file audio da riprodurre per una determinata categoria di location
        
        Args:
            location_category (str): Categoria della location (es. "scuola_di_magia")
            max_sounds (int): Numero massimo di suoni da restituire
            
        Returns:
            list: Lista di percorsi di file audio
        """
        result = []
        
        # Normalizza la categoria
        normalized_category = location_category.lower().replace(' ', '_')
        
        # Se la categoria specifica non esiste, cerca di mappare a una categoria più generica
        if normalized_category not in self.sound_mappings:
            # Cerca nella mappatura delle categorie
            if normalized_category in self.category_mapping:
                normalized_category = self.category_mapping[normalized_category]
            # Oppure cerca con la versione con spazi
            elif location_category.lower() in self.category_mapping:
                normalized_category = self.category_mapping[location_category.lower()]
            else:
                # Usa difflib per trovare la categoria più simile
                categories = list(self.sound_mappings.keys())
                if categories:
                    matches = difflib.get_close_matches(normalized_category, categories, n=1, cutoff=0.6)
                    if matches:
                        normalized_category = matches[0]
                    elif "natura" in self.sound_mappings:
                        normalized_category = "natura"
                    else:
                        # Se proprio non trova nulla, usa la prima categoria disponibile
                        normalized_category = categories[0]
                else:
                    # Nessuna categoria disponibile
                    return result
        
        # Ottieni i suoni per questa categoria
        category_data = self.sound_mappings[normalized_category]
        
        # Aggiungi i suoni diretti della categoria
        direct_sounds = category_data.get("direct_sounds", [])
        if direct_sounds:
            sound_files = [sound["filename"] for sound in direct_sounds]
            # Scegli casualmente se ci sono più suoni disponibili
            if len(sound_files) > max_sounds // 2:
                sound_files = random.sample(sound_files, max_sounds // 2)
            result.extend([os.path.join(self.sounds_dir, f) for f in sound_files])
        
        # Aggiungi i suoni base
        base_sounds = category_data.get("base_sounds", [])
        if base_sounds:
            sound_files = [sound["filename"] for sound in base_sounds]
            # Scegli casualmente se ci sono più suoni disponibili
            remaining_slots = max_sounds - len(result)
            if len(sound_files) > remaining_slots and remaining_slots > 0:
                sound_files = random.sample(sound_files, remaining_slots)
            result.extend([os.path.join(self.sounds_dir, f) for f in sound_files])
        
        return result[:max_sounds]  # Limita al numero massimo di suoni
    
    def get_available_categories(self):
        """Restituisce l'elenco delle categorie di suoni disponibili"""
        return list(self.sound_mappings.keys())
    
    def check_sound_availability(self):
        """Verifica la disponibilità dei file sonori"""
        missing_files = []
        for category, data in self.sound_mappings.items():
            # Verifica suoni diretti
            for sound in data.get("direct_sounds", []):
                filename = os.path.join(self.sounds_dir, sound.get("filename", ""))
                if not os.path.exists(filename):
                    missing_files.append(filename)
            
            # Verifica suoni base
            for sound in data.get("base_sounds", []):
                filename = os.path.join(self.sounds_dir, sound.get("filename", ""))
                if not os.path.exists(filename):
                    missing_files.append(filename)
        
        if missing_files:
            print(f"Attenzione: {len(missing_files)} file audio mancanti:")
            for filename in missing_files[:10]:  # Mostra solo i primi 10
                print(f"  - {filename}")
            if len(missing_files) > 10:
                print(f"  ... e altri {len(missing_files) - 10} file")
        else:
            print("Tutti i file audio sono disponibili!")
        
        return len(missing_files) == 0