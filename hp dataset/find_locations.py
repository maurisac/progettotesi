import json
import pprint

def extract_actual_locations():
    """
    Estrae i luoghi che non sono classificati come "non_luogo" dal file delle locations.
    Restituisce un dizionario con le informazioni rilevanti sui luoghi.
    """
    # Percorsi dei file
    locations_file = "output_locations/dataset/locations_uncertain_edited.json"
    
    try:
        # Carica il file JSON
        with open(locations_file, 'r', encoding='utf-8') as f:
            locations = json.load(f)
        
        # Filtra per trovare i luoghi veri (non classificati come "non_luogo")
        actual_locations = {}
        
        for location_name, location_data in locations.items():
            # Verifica se c'è una categorizzazione
            if "categorization" in location_data and "category" in location_data["categorization"]:
                category = location_data["categorization"]["category"]
                confidence = location_data["categorization"].get("confidence", 0)
                
                # Se non è un "non_luogo", aggiungilo alla lista dei luoghi reali
                # if category != "non_luogo":
                actual_locations[location_name] = {
                        "category": category,
                        "confidence": confidence,
                        "occurrences": location_data.get("occurrences", 0)
                    }
        
        # Ordina i luoghi per numero di occorrenze (dal più frequente al meno frequente)
        sorted_locations = dict(sorted(
            actual_locations.items(), 
            key=lambda item: item[1]["occurrences"], 
            reverse=True
        ))
        
        return sorted_locations
    
    except FileNotFoundError:
        print(f"File non trovato: {locations_file}")
        return {}
    except json.JSONDecodeError:
        print(f"Errore nel parsing del file JSON: {locations_file}")
        return {}

def main():
    # Estrai i luoghi reali
    actual_locations = extract_actual_locations()
    
    # Stampa i risultati
    if actual_locations:
        print(f"Trovati {len(actual_locations)} luoghi reali (non 'non_luogo'):\n")
        print("=====================================")
        print("Nome | Categoria | Occorrenze | Confidenza")
        print("=====================================")
        
        for name, data in actual_locations.items():
            print(f"{name}")#| {data['category']} | {data['occurrences']} | {data['confidence']}")
    else:
        print("Nessun luogo reale trovato o errore nell'apertura del file.")
    
    # Salva i risultati in un file JSON
    with open("luoghi_reali.json", "w", encoding="utf-8") as f:
        json.dump(actual_locations, f, ensure_ascii=False, indent=4)
    
    print("\nI risultati sono stati salvati nel file 'luoghi_reali.json'")

if __name__ == "__main__":
    main()