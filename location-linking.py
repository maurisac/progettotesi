import os
import json
import random

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
        
        # Se la categoria specifica non esiste, cerca di mappare a una categoria più generica
        if location_category not in self.sound_mappings:
            # Mappa categorie simili
            mapping = {
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
                "dormitorio": "casa"
            }
            
            # Se esiste una mappatura, usa quella
            if location_category in mapping and mapping[location_category] in self.sound_mappings:
                location_category = mapping[location_category]
            else:
                # Altrimenti usa suoni generici di ambiente
                print(f"Categoria '{location_category}' non trovata, uso suoni generici")
                if "natura" in self.sound_mappings:
                    location_category = "natura"
                else:
                    return result  # Lista vuota se non ci sono alternative
        
        # Ottieni i suoni per questa categoria
        category_data = self.sound_mappings[location_category]
        
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
    

# esecuzione 
env = SoundEnvironment()
env.check_sound_availability()
print(env.get_sounds_for_location("città"))
print(env.get_sounds_for_location("casa"))
