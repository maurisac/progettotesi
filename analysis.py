import sys
import re
import os
import fitz  # PyMuPDF per i PDF
import docx  # python-docx per i file Word
import csv
import datetime
import time
import json
from transformers import BertTokenizerFast, BertForSequenceClassification
import spacy
import torch, torch.multiprocessing as mp
from collections import Counter
import logging
import ast
from feel_it import EmotionClassifier, SentimentClassifier  # Libreria Feel-it per analisi emozioni

# Configura il logging per salvare gli errori in un file di log
logging.basicConfig(
    filename="analysis.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

PAGE_SIZE = 3300  # Deve essere lo stesso della GUI
DEFAULT_CHAPTER_LENGTH = 12  # Se nessun capitolo viene trovato

# Caricare il modello spaCy per l'italiano
nlp = spacy.load("it_core_news_md")

# Inizializza i classificatori Feel-it
emotion_classifier = EmotionClassifier()
sentiment_classifier = SentimentClassifier()

# Configurazione dei pesi per la scelta del luogo principale
LOCATION_WEIGHTS = {
    "occurrence": 0.03,    # Peso per il numero di occorrenze
    "confidence": 0.90,    # Peso per la confidenza di BERT
    "early_appearance": 0.04,  # Peso per l'apparizione all'inizio
    "spacy_loc_bonus": 0.03    # Bonus se riconosciuto come LOC da spaCy
}

# Configurazione dei pesi per la scelta del personaggio principale
CHARACTER_WEIGHTS = {
    "occurrence": 0.60,    # Peso per il numero di occorrenze
    "early_appearance": 0.4,  # Peso per l'apparizione all'inizio
}















# -------------------------------------------- FUNZIONI DI APERTURA FILE --------------------------------------------
def read_txt(file_path):
# Legge un file di testo e lo divide in pagine.
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    return text




def read_pdf(file_path):
# Legge un file PDF ed estrae il testo.
    doc = fitz.open(file_path)
    text = "\n".join([page.get_text() for page in doc])
    return text




def read_docx(file_path):
# Legge un file Word (.docx) ed estrae il testo.
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text




def read_book(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        return read_txt(file_path)
    elif ext == ".pdf":
        return read_pdf(file_path)
    elif ext == ".docx":
        return read_docx(file_path)
    else:
        print("Errore: formato file non supportato.")
        sys.exit(4)
















# -------------------------------------------- FUNZIONI DI INDIVIDUAZIONE CAPITOLI --------------------------------------------
def find_index_section(text):
# Cerca un possibile indice del libro nelle prime pagine.
    print("Cerco l'indice...")
    matches = re.findall(r'(\b(?:Capitolo|Chapter)\s+\d+\b).*?(\d+)', text[:PAGE_SIZE*5], re.IGNORECASE)
    if matches:
        return {int(num): int(matches[0][1]) for _, num in matches}
    print("Indice non trovato.")
    return None




def find_chapters(text):
# Cerca i capitoli nel testo utilizzando espressioni regolari.
    print("Cerco i capitoli...")
    chapter_starts = {}
    
    # Prima identifica tutti gli inizi di capitolo
    for match in re.finditer(r'\b(?:Capitolo|Chapter)\s+(\d+)\b', text, re.IGNORECASE):
        chapter_num = int(match.group(1))
        start_byte = match.start()
        chapter_starts[chapter_num] = start_byte        
        print(f"      - Testo: '{text[start_byte:start_byte+50]}...'")
    
    if not chapter_starts:        
        return None
    
    # Ordina i capitoli per posizione nel testo
    sorted_starts = sorted(chapter_starts.items(), key=lambda x: x[1])
    
    chapters = {}
    
    # Ora assegna l'inizio di ogni capitolo
    for i, (chapter_num, start_byte) in enumerate(sorted_starts):
        chapters[chapter_num] = start_byte
    
    if chapters:        
        return chapters 
    else:
        print("Capitoli non trovati.")
        return None




def divide_by_fixed_length(text):
# Divide il libro in sezioni di lunghezza fissa se non trova i capitoli.
    print(f"Suddivido manualmente ogni {DEFAULT_CHAPTER_LENGTH * PAGE_SIZE} byte")
    chapters = {}
    for i in range(0, len(text), DEFAULT_CHAPTER_LENGTH * PAGE_SIZE):
        chapter_num = i // (DEFAULT_CHAPTER_LENGTH * PAGE_SIZE) + 1
        chapters[chapter_num] = i
    return chapters




def calculate_page_ranges(chapters, text):
#Calcola i range di pagine per ogni capitolo.
    page_ranges = {}
    chapter_list = sorted(chapters.items())
    for i in range(len(chapter_list)):
        chapter_number, start_byte = chapter_list[i]
        end_byte = chapter_list[i + 1][1] if i + 1 < len(chapter_list) else len(text)
        
        start_page = start_byte // PAGE_SIZE + 1
        end_page = end_byte // PAGE_SIZE + 1
        
        page_ranges[chapter_number] = (start_page, end_page)
    return page_ranges

















# -------------------------------------------- FUNZIONI DI ANALISI --------------------------------------------
def analyze_emotions(text):
    """
    Analizza le emozioni nel testo usando Feel-it.
    Ritorna un dizionario con la classificazione delle emozioni e del sentimento.
    """
    try:
        # Dividi il testo in paragrafi per l'analisi
        paragraphs = [p for p in text.split('\n') if len(p.strip()) > 10]
        
        # Limita il numero di paragrafi per evitare sovraccarico
        max_paragraphs = 100
        if len(paragraphs) > max_paragraphs:
            # Prendi l'inizio, la fine, e alcuni paragrafi dal mezzo
            step = len(paragraphs) // (max_paragraphs // 2)
            selected_paragraphs = paragraphs[:max_paragraphs//4]
            selected_paragraphs += [paragraphs[i] for i in range(max_paragraphs//4, len(paragraphs)-max_paragraphs//4, step)]
            selected_paragraphs += paragraphs[-max_paragraphs//4:]
            paragraphs = selected_paragraphs[:max_paragraphs]
        
        # Classifica emozioni e sentimento
        emotions = emotion_classifier.predict(paragraphs)
        sentiments = sentiment_classifier.predict(paragraphs)
        
        # Conta la frequenza di ogni emozione e sentimento
        emotion_counts = Counter(emotions)
        sentiment_counts = Counter(sentiments)
        
        # Calcola percentuali
        total_paragraphs = len(paragraphs)
        emotion_percentages = {emotion: count/total_paragraphs*100 
                              for emotion, count in emotion_counts.items()}
        sentiment_percentages = {sentiment: count/total_paragraphs*100 
                                for sentiment, count in sentiment_counts.items()}
        
        return {
            "emotion_counts": dict(emotion_counts),
            "sentiment_counts": dict(sentiment_counts),
            "emotion_percentages": emotion_percentages,
            "sentiment_percentages": sentiment_percentages,
            "dominant_emotion": emotion_counts.most_common(1)[0][0],
            "dominant_sentiment": sentiment_counts.most_common(1)[0][0]
        }
    except Exception as e:
        logging.error(f"Errore nell'analisi delle emozioni: {e}")
        return {
            "error": str(e),
            "dominant_emotion": "unknown",
            "dominant_sentiment": "unknown"
        }




def classify_location_type(location, context=""):
    """Classifica il tipo di location utilizzando il modello fine-tuned."""
    try:
        # Carica il modello e il tokenizer
        loc_model = BertForSequenceClassification.from_pretrained("./bert_location_classifier")
        loc_tokenizer = BertTokenizerFast.from_pretrained("./bert_location_classifier")
        
        # Carica il mapping delle categorie
        with open("./bert_location_classifier/category_mapping.json", "r") as f:
            category_mapping = json.load(f)
        id_to_category = category_mapping["id_to_category"]
        
        # Converte gli id da string a int (json li salva come string)
        id_to_category = {int(k): v for k, v in id_to_category.items()}
        
        # Limita la lunghezza del contesto per evitare problemi
        if context and len(context) > 500:
            context = context[:500] + "..."
            
        # Prepara l'input
        inputs = loc_tokenizer(
            location,  
            context,   
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        )
        
        # Inferenza
        with torch.no_grad():
            outputs = loc_model(**inputs)
        
        # Ottieni la classe predetta
        predicted_class_id = outputs.logits.argmax().item()
        predicted_category = id_to_category[predicted_class_id]
        confidence = torch.softmax(outputs.logits, dim=1)[0, predicted_class_id].item()
        
        return {
            "category": predicted_category,
            "confidence": confidence
        }
    except Exception as e:
        logging.error(f"Errore nella classificazione della location {location}: {e}")
        return {
            "category": "sconosciuto",
            "confidence": 0.0
        }




def load_existing_analysis(file_name):
    """Carica i risultati di un'analisi esistente da file CSV."""
    try:
        if not os.path.exists(file_name):
            return None
        
        analysis_data = {}
        with open(file_name, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                    
                if row[0] == "Stato" and "completata" not in row[1]:
                    return None  # Analisi non completata
                
                try:    
                    if row[0] == "Entities":
                        # Gestisci attentamente la conversione
                        entity_data = ast.literal_eval(row[1])
                        analysis_data["entities"] = entity_data
                    elif row[0] == "Potential Locations":
                        analysis_data["locations"] = ast.literal_eval(row[1])
                    elif row[0] == "Emotions":
                        analysis_data["emotions"] = ast.literal_eval(row[1])
                except (SyntaxError, ValueError) as e:
                    logging.error(f"Errore di parsing: {e} per {row[0]}")
                    continue
                    
        return analysis_data if "entities" in analysis_data else None
    except Exception as e:
        logging.error(f"Errore nel caricamento dell'analisi esistente: {e}")
        return None




def select_main_location(locations, weights=None):
    """
    Seleziona la location principale in base ai pesi configurati.
    Permette di modificare i pesi senza rifare l'analisi.
    """
    if not weights:
        weights = LOCATION_WEIGHTS
        
    highest_score = -1
    main_location = None
    
    for loc_name, loc_data in locations.items():
        # Non considerare luoghi classificati come non_luogo con alta confidenza
        if loc_data["category"] == "non_luogo" and loc_data["confidence"] > 0.8:
            continue
            
        # Ricalcola il punteggio con i pesi attuali
        occurrence_score = loc_data["count"] / max([d["count"] for d in locations.values()], default=1)
        early_appearance_bonus = 1.0 if loc_data.get("early_appearance", False) else 0.0
        spacy_loc_bonus = 0.5 if loc_data.get("spacy_label", "") == "LOC" else 0.0
        
        priority_score = (
            weights["occurrence"] * occurrence_score + 
            weights["confidence"] * loc_data["confidence"] + 
            weights["early_appearance"] * early_appearance_bonus +
            weights["spacy_loc_bonus"] * spacy_loc_bonus
        )
        
        if priority_score > highest_score:
            highest_score = priority_score
            main_location = {
                "name": loc_name,
                "category": loc_data["category"],
                "spacy_label": loc_data.get("spacy_label", "unknown"),
                "confidence": loc_data["confidence"],
                "count": loc_data["count"],
                "priority_score": priority_score,
                "early_appearance": loc_data.get("early_appearance", False)
            }
    
    return main_location




def select_main_character(entities, weights=None):
    """
    Seleziona il personaggio principale in base ai pesi configurati.
    Permette di modificare i pesi senza rifare l'analisi.
    """
    if not weights:
        weights = CHARACTER_WEIGHTS
        
    # Filtra solo le entità che sono persone (PER)
    people = {}
    
    # Verifica il tipo di entities e processa di conseguenza
    if isinstance(entities, Counter):
        # Se è un oggetto Counter (risultato diretto di spaCy)
        for (entity, label), count in entities.items():
            if label == "PER":
                people[entity] = {
                    "count": count
                }
    elif isinstance(entities, dict) or isinstance(entities, list):
        # Se è un dizionario o una lista (caricato da CSV)
        try:
            # Prova a interpretare come dizionario se è stato serializzato
            if isinstance(entities, str):
                entities = ast.literal_eval(entities)
                
            if isinstance(entities, dict):
                # Se è un dizionario di entità
                for entity_key, entity_data in entities.items():
                    # Prova a interpretare la chiave come tupla (entità, label)
                    if isinstance(entity_key, str) and entity_key.startswith("('"):
                        # La chiave è una rappresentazione di stringa di una tupla
                        try:
                            entity_tuple = ast.literal_eval(entity_key)
                            entity, label = entity_tuple
                            count = entity_data
                            if label == "PER":
                                people[entity] = {"count": count}
                        except:
                            continue
            elif isinstance(entities, list):
                # Se è una lista di tuple/liste
                for item in entities:
                    if len(item) == 3:  # [entity, label, count]
                        entity, label, count = item
                        if label == "PER":
                            people[entity] = {"count": count}
                    elif len(item) == 2:  # [(entity, label), count]
                        key, count = item
                        if isinstance(key, tuple) and len(key) == 2:
                            entity, label = key
                            if label == "PER":
                                people[entity] = {"count": count}
        except Exception as e:
            logging.error(f"Errore nell'interpretazione delle entità: {e}")
            return None
    
    if not people:
        return None
    
    # Determina quali personaggi appaiono all'inizio (se disponibile nell'analisi)
    early_characters = set()  # Questo dovrebbe essere ottenuto da una precedente analisi
    
    # Calcola il punteggio di ogni personaggio
    highest_score = -1
    main_character = None
    
    for character, data in people.items():
        # Normalizza il punteggio di occorrenza rispetto al personaggio più frequente
        occurrence_score = data["count"] / max([d["count"] for d in people.values()])
        early_appearance_bonus = 1.0 if character in early_characters else 0.0
        
        priority_score = (
            weights["occurrence"] * occurrence_score + 
            weights["early_appearance"] * early_appearance_bonus
        )
        
        if priority_score > highest_score:
            highest_score = priority_score
            main_character = {
                "name": character,
                "count": data["count"],
                "early_appearance": character in early_characters,
                "priority_score": priority_score
            }
    
    return main_character




def analyze_chapter(book_name, chapter_num, chapter_text, output_dir):
    """
    Analizza un capitolo o carica i risultati esistenti.
    Quindi seleziona luogo e personaggio principale in base ai pesi configurati.
    """
    file_name = os.path.join(output_dir, f"{book_name}-capitolo{chapter_num}-analysis.csv")
    
    # Verifica se esiste già un'analisi completata
    existing_analysis = load_existing_analysis(file_name)
    
    if existing_analysis:
        print(f"Trovata analisi esistente per {book_name} capitolo {chapter_num}. Aggiorno solo la selezione di luogo e personaggio.")
        
        # Seleziona il luogo principale con i pesi attuali
        main_location = select_main_location(existing_analysis["locations"])
        
        # Seleziona il personaggio principale con i pesi attuali
        main_character = select_main_character(existing_analysis["entities"])
        
        # Aggiorna i risultati nel file esistente
        update_analysis_results(file_name, main_location, main_character)
        
        return
    
    # Se non esiste un'analisi completata, esegui l'analisi completa
    try:
        with open(file_name, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Stato", "Analisi in corso"])

        print(f"Analisi di {book_name} capitolo {chapter_num}")

        start_time = time.time()
        times = {}

        # Analisi spaCy
        start = time.time()
        chapter_doc = nlp(chapter_text)
        times["Analisi con spaCy"] = time.time() - start

        # Riconoscimento entità con spaCy
        start = time.time()
        spacy_results = [(ent.text, ent.label_) for ent in chapter_doc.ents]
        
        # Troviamo anche la posizione di ogni entità nel testo
        entity_positions = {}
        early_entities = []
        entity_count = 0
        
        # Consideriamo tutte le entità (LOC, MISC, PER)
        for ent in chapter_doc.ents:
            if ent.text not in entity_positions:
                entity_positions[ent.text] = {
                    "positions": [],
                    "label": ent.label_
                }
            entity_positions[ent.text]["positions"].append(ent.start_char)
            entity_count += 1
        
        # Calcola il 10% iniziale del testo per identificare entità all'inizio
        if entity_count > 0:
            early_text_threshold = int(len(chapter_doc.text) * 0.1)
            for entity_name, entity_data in entity_positions.items():
                if any(pos < early_text_threshold for pos in entity_data["positions"]):
                    early_entities.append(entity_name)
        
        # Conteggio standard per spaCy
        spacy_results = Counter(spacy_results)
        times["Riconoscimento entità con spaCy"] = time.time() - start
        
        # Analisi delle emozioni con Feel-it
        start = time.time()
        emotions_data = analyze_emotions(chapter_text)
        times["Analisi emozioni"] = time.time() - start
        
        # Identifica e classifica tutte le entità potenzialmente luoghi
        start = time.time()
        locations = {}
        
        # Esamina LOC, MISC e PER per trovare potenziali luoghi
        for (entity, label), count in spacy_results.items():
            # Verifichiamo se l'entità è un luogo con BERT, indipendentemente dalla categoria spaCy
            classification = classify_location_type(entity, f"Questa entità si trova nel libro {book_name}")
            
            # Se BERT dice che non è un luogo ma è etichettata come LOC da spaCy, classifichiamola comunque
            is_location = (classification["category"] != "non_luogo") or (label == "LOC")
            
            if is_location:
                # Salva i dati rilevanti
                locations[entity] = {
                    "category": classification["category"],
                    "confidence": classification["confidence"],
                    "spacy_label": label,
                    "count": count,
                    "early_appearance": entity in early_entities,
                    "positions": entity_positions.get(entity, {}).get("positions", [])
                }
                
        times["Classificazione delle location"] = time.time() - start

        # Seleziona il luogo principale
        main_location = select_main_location(locations)
        
        # Seleziona il personaggio principale
        main_character = select_main_character(spacy_results)

        total_time = time.time() - start_time
        times["Tempo totale"] = total_time

        # Genera sintesi
        summary = f"Il capitolo {chapter_num} di {book_name} presenta "
        if emotions_data.get("dominant_emotion"):
            summary += f"un tono emotivo predominante di '{emotions_data['dominant_emotion']}' "
            summary += f"e un sentimento generale '{emotions_data['dominant_sentiment']}'.\n\n"
        
        if main_character:
            summary += f"Il protagonista è probabilmente {main_character['name']}, "
            summary += f"che viene menzionato {main_character['count']} volte"
            if main_character.get("early_appearance"):
                summary += " e appare all'inizio del capitolo."
            else:
                summary += "."
            summary += "\n\n"
        
        if main_location:
            summary += f"L'ambientazione principale è {main_location['name']} " \
                       f"(tipo: {main_location['category']}, " \
                       f"riconosciuto da spaCy come: {main_location['spacy_label']}, " \
                       f"occorrenze: {main_location['count']}, " \
                       f"confidenza: {main_location['confidence']:.2f})"

        # Scrive i risultati nel CSV
        completion_time = datetime.datetime.now().strftime("%d/%m/%Y alle %H:%M:%S")
        with open(file_name, "a", newline='', encoding="utf-8") as f:
            print(f"\nScrittura dei risultati in {file_name}...\n")
            writer = csv.writer(f)
            writer.writerow(["Stato", f"Analisi completata il {completion_time}"])
            writer.writerow(["Sintesi", summary])
            writer.writerow(["Entities", spacy_results])
            writer.writerow(["Potential Locations", locations])
            writer.writerow(["Main Location", main_location])
            writer.writerow(["Main Character", main_character])
            writer.writerow(["Emotions", emotions_data])
            writer.writerow(["Tempi di analisi", times])

    except Exception as e:
        logging.error(f"Errore nell'analisi del capitolo {chapter_num}: {e}")
        with open(file_name, "a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Stato", "Analisi interrotta per errore"])
            writer.writerow(["Errore", str(e)])




def update_analysis_results(file_name, main_location, main_character):
    """Aggiorna i risultati di un'analisi esistente con le nuove selezioni."""
    try:
        # Leggi il file esistente
        with open(file_name, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Cerca le righe da aggiornare
        updated_rows = []
        summary_updated = False
        
        for row in rows:
            if len(row) < 2:
                updated_rows.append(row)
                continue
                
            if row[0] == "Main Location":
                updated_rows.append(["Main Location", main_location])
                continue
                
            if row[0] == "Main Character":
                updated_rows.append(["Main Character", main_character])
                continue
                
            if row[0] == "Sintesi" and not summary_updated:
                # Aggiorna la sintesi con le nuove informazioni
                summary = row[1]
                
                # Rimuovi le vecchie informazioni sul protagonista e l'ambientazione
                summary_lines = summary.split("\n\n")
                new_summary_lines = []
                
                for line in summary_lines:
                    if not line.startswith("Il protagonista è") and not line.startswith("L'ambientazione principale è"):
                        new_summary_lines.append(line)
                
                # Aggiungi le nuove informazioni
                if main_character:
                    protagonist_line = f"Il protagonista è probabilmente {main_character['name']}, "
                    protagonist_line += f"che viene menzionato {main_character['count']} volte"
                    if main_character.get("early_appearance"):
                        protagonist_line += " e appare all'inizio del capitolo."
                    else:
                        protagonist_line += "."
                    new_summary_lines.append(protagonist_line)
                
                if main_location:
                    location_line = f"L'ambientazione principale è {main_location['name']} " \
                                   f"(tipo: {main_location['category']}, " \
                                   f"riconosciuto da spaCy come: {main_location['spacy_label']}, " \
                                   f"occorrenze: {main_location['count']}, " \
                                   f"confidenza: {main_location['confidence']:.2f})"
                    new_summary_lines.append(location_line)
                
                updated_rows.append(["Sintesi", "\n\n".join(new_summary_lines)])
                summary_updated = True
                continue
            
            updated_rows.append(row)
        
        # Scrivi le righe aggiornate nel file
        with open(file_name, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(updated_rows)
            
        print(f"Risultati aggiornati per {file_name}")
        
    except Exception as e:
        logging.error(f"Errore nell'aggiornamento dei risultati: {e}")




def parallel_analysis(book_name, chapters, text, output_dir):
    print("Inizio analisi parallela...")
    num_workers = min(4, len(chapters))  # Limita il numero di processi a 4
    
    # Crea una lista di capitoli ordinati per posizione nel testo
    # Questo è fondamentale per determinare correttamente dove finisce ciascun capitolo
    complete_chapter_list = sorted(chapters.items(), key=lambda x: x[1])
    
    # Limita l'analisi ai primi capitoli per risparmiare tempo (ad esempio i primi 3)
    limited_chapter_list = complete_chapter_list[:3]  # Modifica il numero in base alle tue esigenze
    
    with mp.Pool(processes=num_workers) as pool:
        tasks = []

        for i in range(len(limited_chapter_list)):
            chapter_number, start_byte = limited_chapter_list[i]
            
            # Determina dove finisce questo capitolo
            # CORREZIONE: usa la lista completa per trovare dove inizia il prossimo capitolo
            
            # Trova la posizione dell'elemento corrente nella lista completa
            complete_idx = next((idx for idx, (num, _) in enumerate(complete_chapter_list) if num == chapter_number), None)
            
            if complete_idx is not None and complete_idx + 1 < len(complete_chapter_list):
                # Se c'è un capitolo successivo nella lista completa, usa il suo inizio come fine di questo
                _, end_byte = complete_chapter_list[complete_idx + 1]
            else:
                # Se questo è l'ultimo capitolo nel testo completo, va fino alla fine del testo
                end_byte = len(text)

            # Estrai il testo del capitolo corrente
            chapter_text = text[start_byte:end_byte]
            
            if chapter_text.strip():  # Controlla se il capitolo non è vuoto
                print(f"\nAvvio analisi del capitolo {chapter_number}...")
                print(f"Intervallo in byte: {start_byte} - {end_byte} ({end_byte-start_byte} byte)")
                print(f"Percentuale del testo totale: {len(chapter_text)/len(text)*100:.2f}%")
                print(f"Inizio capitolo: '{chapter_text[:100]}...'")
                
                # Utilizza apply_async per eseguire l'analisi in un processo separato
                tasks.append(pool.apply_async(analyze_chapter,
                    (book_name, chapter_number, chapter_text, output_dir)))
                
                print(f"Analisi del capitolo {chapter_number} avviata.")
            else:
                print(f"\nAttenzione\nCapitolo {chapter_number} vuoto, saltato.")

        # Attendi il completamento di tutti i processi
        for task in tasks:
            task.wait()

    print("Analisi parallela completata.")


































# -------------------- MAIN --------------------

def main():
    try:
        input_file = sys.argv
        
        if len(input_file) < 2:
            print("Errore: specificare il file da analizzare.")
            sys.exit(10)
        
        file_path = input_file[1]
        if not os.path.exists(file_path):
            print("Errore: file non trovato.")
            sys.exit(11)

        book_name = os.path.splitext(os.path.basename(file_path))[0]
        output_dir = os.path.join(os.getcwd(), "analyses", book_name)
        os.makedirs(output_dir, exist_ok=True)
        text = read_book(file_path)
  
        # Cerca prima l'indice
        index_sections = find_index_section(text)
        
        # Se non trova l'indice, cerca i capitoli
        chapters = find_chapters(text) if not index_sections else None

        # Se nessuno dei due metodi ha funzionato, divide manualmente
        final_chapters = index_sections or chapters or divide_by_fixed_length(text)

        print("Capitoli individuati")

        # Calcola i range delle pagine per ogni capitolo
        page_ranges = calculate_page_ranges(final_chapters, text)

        # Analisi parallela
        parallel_analysis(book_name, final_chapters, text, output_dir)

        # Creazione del file di riepilogo
        summary_file = os.path.join(output_dir, f"{book_name}-analysis.csv")
        with open(summary_file, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Capitolo", "Range Pagine"])
            for chapter, (start_page, end_page) in page_ranges.items():
                writer.writerow([chapter, f"{start_page}-{end_page}"])
                print(f"Capitolo {chapter}, pagine {start_page}-{end_page}, Byte iniziale {final_chapters[chapter]}, byte finale {final_chapters[chapter+1] if chapter+1 in final_chapters else len(text)}")

        print(f"Analisi completata. Riepilogo salvato in {summary_file}")
        sys.exit(0)
    except Exception as e:
        print(f"Errore durante l'esecuzione del programma principale: {e}")
        logging.error(f"Errore durante l'esecuzione del programma principale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()