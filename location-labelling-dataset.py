import os
import re
import json
import spacy
import pandas as pd
from collections import Counter
from tqdm import tqdm
import requests
from transformers import pipeline
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("location_extraction.log"),
        logging.StreamHandler()
    ]
)

# Carica il modello italiano di spaCy
try:
    nlp = spacy.load("it_core_news_lg")
    logging.info("Caricato modello spaCy it_core_news_lg")
except:
    logging.warning("Modello it_core_news_lg non trovato. Installazione in corso...")
    os.system("python -m spacy download it_core_news_lg")
    nlp = spacy.load("it_core_news_lg")

# Carica un modello zero-shot di HuggingFace per la classificazione
if spacy.prefer_gpu():
    spacy.require_gpu()
    device = 0  # GPU
else:
    device = -1  # CPU

classifier = pipeline(
    "zero-shot-classification",
    model="MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7",
    device=device
)

# Categorie di luoghi possibili
LOCATION_CATEGORIES = [
    "città", "paese", "villaggio", "castello", "palazzo", "scuola", 
    "università", "montagna", "lago", "fiume", "mare", "oceano", 
    "foresta", "bosco", "parco", "piazza", "strada", "edificio", 
    "chiesa", "cattedrale", "tempio", "ristorante", "hotel", "negozio", 
    "teatro", "cinema", "museo", "biblioteca", "ospedale", "stazione",
    "aeroporto", "porto", "isola", "spiaggia", "deserto", "giardino"
    "taverna", "bar", "caffetteria", "discoteca", "pub", "centro commerciale",
    "supermercato", "mercato", "fattoria", "mulino", "miniera", "fortezza", 
    "accademia", "osservatorio", "laboratorio", "bunker", "caserma", "prigione", 
    "manicomio", "cimitero", "stadio", "arena", "campo da battaglia", 
    "base militare", "monastero", "santuario", "oasi", "ghiacciaio", 
    "vulcano", "grotta", "gola", "cascata", "baia", "diga", "faro", 
    "nave pirata", "sommergibile", "dirigibile", "spazioporto", 
    "stazione spaziale", "pianeta alieno", "dimensione parallela", "regno sommerso", 
    "città volante", "labirinto", "castello incantato", "foresta oscura", 
    "tempio sommerso", "villaggio maledetto", "biblioteca proibita", 

]

def extract_locations_from_text(text, min_occurrences=2):
    """Estrae le location dal testo usando spaCy."""
    doc = nlp(text)
    locations = []
    
    # Prima passata: estraiamo tutte le entità che spaCy riconosce come luoghi
    loc_entities = [ent.text for ent in doc.ents if ent.label_ in ["LOC", "GPE"]]
    
    # Seconda passata: cerchiamo nomi propri che iniziano con maiuscola
    # e potrebbero essere località non riconosciute
    potential_locs = set()
    for token in doc:
        # Se è un nome proprio che inizia con maiuscola
        if (token.pos_ in ["PROPN"] and token.text[0].isupper() and 
            len(token.text) > 2 and token.text.lower() not in nlp.Defaults.stop_words):
            potential_locs.add(token.text)
    
    # Conta occorrenze delle entità
    loc_counts = Counter(loc_entities)
    
    # Filtra solo location con più di min_occurrences occorrenze
    filtered_locations = {loc: count for loc, count in loc_counts.items() 
                        if count >= min_occurrences}
    
    # Aggiungi le potenziali location non riconosciute che appaiono frequentemente
    for loc in potential_locs:
        if loc not in filtered_locations:
            count = len(re.findall(r'\b' + re.escape(loc) + r'\b', text))
            if count >= min_occurrences:
                filtered_locations[loc] = count
    
    return filtered_locations

def extract_locations_from_books(directory_path, output_dir):
    """Estrae le location da tutti i libri nella directory specificata."""
    os.makedirs(output_dir, exist_ok=True)
    
    all_locations = {}
    
    for filename in tqdm(os.listdir(directory_path)):
        if filename.endswith('.txt'):
            file_path = os.path.join(directory_path, filename)
            book_name = os.path.splitext(filename)[0]
            
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()
                
                # Estrai location dal libro
                locations = extract_locations_from_text(text)
                
                # Salva risultati per questo libro
                output_file = os.path.join(output_dir, f"{book_name}_locations.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(locations, f, ensure_ascii=False, indent=4)
                
                # Aggiorna il dizionario di tutte le location
                for loc, count in locations.items():
                    if loc in all_locations:
                        all_locations[loc]["total_occurrences"] += count
                        all_locations[loc]["books"].append({"name": book_name, "occurrences": count})
                    else:
                        all_locations[loc] = {
                            "total_occurrences": count,
                            "books": [{"name": book_name, "occurrences": count}]
                        }
                
                logging.info(f"Processato {book_name}. Trovate {len(locations)} location potenziali.")
            
            except Exception as e:
                logging.error(f"Errore nel processare {book_name}: {str(e)}")
    
    # Salva un file riassuntivo con tutte le location
    summary_file = os.path.join(output_dir, "all_locations_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_locations, f, ensure_ascii=False, indent=4)
    
    return all_locations

def clean_locations(all_locations, min_total_occurrences=3, min_books=1):
    """Pulisce la lista di location rimuovendo quelle poco frequenti o sospette."""
    filtered_locations = {}
    
    for loc, data in tqdm(all_locations.items()):
        # Filtro per occorrenze totali e numero di libri
        if (data["total_occurrences"] >= min_total_occurrences and 
            len(data["books"]) >= min_books):
            
            # Verifica se sembra un nome proprio valido
            if (loc[0].isupper() and                # Inizia con maiuscola
                not any(c.isdigit() for c in loc) and  # Non contiene numeri
                len(loc) > 2 and                    # Lunghezza significativa
                " " in loc or len(loc) > 4):        # O è composto o è lungo
                
                filtered_locations[loc] = data
    
    logging.info(f"Pulizia: da {len(all_locations)} a {len(filtered_locations)} location")
    return filtered_locations

def categorize_location(location, context=""):
    """Categorizza una location usando il modello zero-shot."""
    try:
        # Prepara il testo per la classificazione
        text = f"{location}"
        if context:
            text += f". {context}"
        
        # Usa il modello zero-shot per classificare
        result = classifier(text, LOCATION_CATEGORIES, multi_label=False)
        
        # Prendi la categoria più probabile e il punteggio
        category = result['labels'][0]
        score = result['scores'][0]
        
        return {
            "category": category,
            "confidence": score,
            "all_categories": [{"label": label, "score": score} 
                              for label, score in zip(result['labels'], result['scores'])]
        }
    except Exception as e:
        logging.error(f"Errore nella categorizzazione di {location}: {str(e)}")
        return {"category": "sconosciuto", "confidence": 0, "all_categories": []}

def search_wikipedia(location, book_name=""):
    """Cerca informazioni su una location su Wikipedia."""
    try:
        # Costruisci la query
        query = location
        if book_name:
            query += f" {book_name}"
        
        # Chiama l'API Wikipedia in italiano
        url = "https://it.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srprop": "snippet",
            "srlimit": 3
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'query' in data and 'search' in data['query'] and data['query']['search']:
            # Estrai il primo risultato
            first_result = data['query']['search'][0]
            title = first_result['title']
            snippet = first_result['snippet']
            
            # Pulisci lo snippet da tag HTML
            clean_snippet = re.sub(r'<.*?>', '', snippet)
            
            return {
                "found": True,
                "title": title,
                "snippet": clean_snippet,
                "results": data['query']['search']
            }
        else:
            return {"found": False}
    
    except Exception as e:
        logging.error(f"Errore nella ricerca Wikipedia per {location}: {str(e)}")
        return {"found": False, "error": str(e)}

def build_dataset(locations_data, output_dir):
    """Costruisce il dataset finale di location categorizzate."""
    os.makedirs(os.path.join(output_dir, "dataset"), exist_ok=True)
    
    # Prepara i file per le diverse categorie di certezza
    confident_file = os.path.join(output_dir, "dataset", "locations_confident.json")
    uncertain_file = os.path.join(output_dir, "dataset", "locations_uncertain.json")
    manual_file = os.path.join(output_dir, "dataset", "locations_for_manual_review.json")
    
    confident_locations = {}
    uncertain_locations = {}
    manual_review_locations = {}
    
    # Soglie di confidenza
    HIGH_CONFIDENCE = 0.7
    LOW_CONFIDENCE = 0.4
    
    for location, data in tqdm(locations_data.items()):
        # Prepara un contesto usando i libri in cui appare
        book_names = [book["name"] for book in data["books"]]
        context = f"Questo luogo appare nei seguenti libri: {', '.join(book_names[:3])}"
        
        # Categorizza la location
        categorization = categorize_location(location, context)
        
        # Arricchisci con informazioni da Wikipedia
        wiki_info = search_wikipedia(location, book_names[0] if book_names else "")
        
        # Crea un record completo
        location_record = {
            "location": location,
            "occurrences": data["total_occurrences"],
            "books": data["books"],
            "categorization": categorization,
            "wikipedia_info": wiki_info
        }
        
        # Decidi dove inserire il record in base alla confidenza
        confidence = categorization["confidence"]
        
        if confidence >= HIGH_CONFIDENCE:
            confident_locations[location] = location_record
        elif confidence >= LOW_CONFIDENCE or wiki_info["found"]:
            # Se abbiamo trovato info su Wikipedia, mettiamo tra le incerte anche se confidenza bassa
            uncertain_locations[location] = location_record
        else:
            manual_review_locations[location] = location_record
    
    # Salva i risultati
    with open(confident_file, 'w', encoding='utf-8') as f:
        json.dump(confident_locations, f, ensure_ascii=False, indent=4)
    
    with open(uncertain_file, 'w', encoding='utf-8') as f:
        json.dump(uncertain_locations, f, ensure_ascii=False, indent=4)
    
    with open(manual_file, 'w', encoding='utf-8') as f:
        json.dump(manual_review_locations, f, ensure_ascii=False, indent=4)
    
    # Crea anche un CSV per il fine-tuning di BERT
    create_bert_finetuning_dataset(confident_locations, os.path.join(output_dir, "dataset", "bert_finetuning.csv"))
    
    logging.info(f"Dataset creato con {len(confident_locations)} location confidenti, "
                f"{len(uncertain_locations)} incerte e {len(manual_review_locations)} da rivedere manualmente.")
    
    return {
        "confident": confident_locations,
        "uncertain": uncertain_locations,
        "manual": manual_review_locations
    }

def create_bert_finetuning_dataset(confident_locations, output_file):
    """Crea un dataset CSV per il fine-tuning di BERT."""
    rows = []
    
    for location, data in confident_locations.items():
        category = data["categorization"]["category"]
        
        # Crea record nel formato "location [SEP] context" come input e categoria come output
        for book in data["books"]:
            # Estrai il nome del libro
            book_name = book["name"]
            
            # Crea una riga per il fine-tuning
            row = {
                "location": location,
                "category": category,
                "context": f"Questa location si trova nel libro {book_name}",
                "confidence": data["categorization"]["confidence"]
            }
            rows.append(row)
    
    # Crea il DataFrame e salva in CSV
    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    logging.info(f"Creato dataset per fine-tuning BERT con {len(df)} esempi")

def main():
    """Funzione principale che esegue tutto il processo."""
    # Parametri
    books_directory = "libri"  # Directory contenente i libri in formato .txt
    output_directory = "output_locations"  # Directory di output
    
    # Fase 1: Estrai location dai libri
    logging.info("FASE 1: Estrazione location dai libri")
    all_locations = extract_locations_from_books(books_directory, output_directory)
    
    # Fase 2: Pulizia delle location
    logging.info("FASE 2: Pulizia delle location")
    cleaned_locations = clean_locations(all_locations)
    
    # Salva le location pulite
    cleaned_file = os.path.join(output_directory, "cleaned_locations.json")
    with open(cleaned_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_locations, f, ensure_ascii=False, indent=4)
    
    # Fase 3: Categorizzazione e creazione dataset
    logging.info("FASE 3: Categorizzazione e creazione dataset")
    dataset = build_dataset(cleaned_locations, output_directory)
    
    logging.info("PROCESSO COMPLETATO!")
    logging.info(f"Risultati salvati in: {output_directory}")

if __name__ == "__main__":
    main()