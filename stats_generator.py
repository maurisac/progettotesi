# Per eseguire questo file, usare il comando 
# "python stats_generator.py --dir "analyses/libro" --book "nomelibro" --evaluate-bert --test-data "test_locations.json""

import os
import sys
import csv
import ast
import json
import datetime
import time
import argparse
import logging
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
try:
    import networkx as nx
except ImportError:
    print("Networkx non installato. I grafici della rete di luoghi non saranno generati.")
    
try:
    import torch
    from transformers import BertTokenizerFast, BertForSequenceClassification
except ImportError:
    print("PyTorch o Transformers non installati. La valutazione del modello BERT non sarà possibile.")

# Configura il logging
logging.basicConfig(
    filename="stats_generator.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Costanti
PAGE_SIZE = 3300  # Deve essere lo stesso della GUI e di analysis.py

# Configurazione dei pesi per la scelta del luogo principale (copiata da analysis.py)
LOCATION_WEIGHTS = {
    "occurrence": 0.3,    # Peso per il numero di occorrenze
    "confidence": 10,     # Peso per la confidenza di BERT
    "early_appearance": 3,  # Peso per l'apparizione all'inizio
    "spacy_loc_bonus": 0.2   # Bonus se riconosciuto come LOC da spaCy
}

# Configurazione dei pesi per la scelta del personaggio principale
CHARACTER_WEIGHTS = {
    "occurrence": 1,       # Peso per il numero di occorrenze
    "early_appearance": 2, # Peso per l'apparizione all'inizio
    "spacy_per_bonus": 0.5 # Bonus se riconosciuto come PER da spaCy
}










# -------------------------------------------- FUNZIONI DI RISULTATI E STATISTICHE --------------------------------------------
def count_tokens_from_csv(file_path):
    """
    Legge il conteggio dei token da un file CSV di analisi.
    
    Args:
        file_path: Percorso al file CSV di analisi
        
    Returns:
        int: Numero di token o None se non trovato
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[0] == "Token Count":
                    return int(row[1])
    except Exception as e:
        logging.error(f"Errore nella lettura del conteggio token da {file_path}: {e}")
    return None




def generate_stats_file(book_name, output_dir):
    """
    Genera un file CSV di statistiche aggregando i dati dei capitoli analizzati.
    """
    stats_file = os.path.join(output_dir, f"stats-{book_name}.csv")
    chapter_files = []
    
    # Trova tutti i file di analisi dei capitoli
    for file in os.listdir(output_dir):
        if file.startswith(f"{book_name}-capitolo") and file.endswith("-analysis.csv"):
            chapter_files.append(file)
    
    # Ordina i file per numero di capitolo
    chapter_files.sort(key=lambda x: int(x.split("capitolo")[1].split("-")[0]))
    
    # Crea il file di statistiche
    with open(stats_file, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        
        for chapter_file in chapter_files:
            chapter_num = int(chapter_file.split("capitolo")[1].split("-")[0])
            file_path = os.path.join(output_dir, chapter_file)
            
            try:
                # Carica i dati del capitolo
                with open(file_path, 'r', encoding='utf-8') as cf:
                    reader = csv.reader(cf)
                    chapter_data = list(reader)
                
                # Estrai i dati necessari
                main_location = None
                locations = {}
                times = {}
                
                for row in chapter_data:
                    if len(row) < 2:
                        continue
                        
                    if row[0] == "Main Location":
                        try:
                            main_location = ast.literal_eval(row[1])
                        except:
                            main_location = {"name": "Sconosciuto", "priority_score": 0}
                            
                    elif row[0] == "Potential Locations":
                        try:
                            locations = ast.literal_eval(row[1])
                        except:
                            locations = {}
                            
                    elif row[0] == "Tempi di analisi":
                        try:
                            times = ast.literal_eval(row[1])
                        except:
                            times = {}
                
                # Calcola la dimensione del capitolo
                chapter_path = os.path.join(output_dir, chapter_file)
                file_size = os.path.getsize(chapter_path)
                
                # Stima del numero di pagine (usando la costante PAGE_SIZE)
                num_pages = max(1, file_size // PAGE_SIZE)
                
                # Scrivi l'intestazione del capitolo
                writer.writerow([f"Capitolo {chapter_num}:"])
                writer.writerow([f"{file_size} byte - {num_pages} pagine"])
                
                # Scrivi i tempi di analisi
                times_str = ", ".join([f"{k}: {v:.2f}s" for k, v in times.items()])
                writer.writerow([f"Tempi di analisi: {times_str}"])
                
                # Scrivi il luogo principale
                if main_location and "name" in main_location and "priority_score" in main_location:
                    writer.writerow([f"{main_location['name']}: {main_location['priority_score']:.2f}"])
                else:
                    writer.writerow(["Luogo principale non identificato"])
                
                # Scrivi gli altri luoghi (fino a 10, ordinati per priority_score)
                writer.writerow(["Altri luoghi:"])
                
                # MODIFICATO: Assegna priority_score a tutti i luoghi che non ce l'hanno
                # Questo simula ciò che farebbe select_main_location ma solo per il calcolo dei punteggi
                main_loc_name = main_location.get("name") if main_location else None
                weights = LOCATION_WEIGHTS
                max_count = max([d["count"] for d in locations.values()], default=1)
                
                # Lista per tenere traccia di tutti i luoghi con punteggio
                scored_locations = []
                
                for loc_name, loc_data in locations.items():
                    # Salta il luogo principale che è già stato mostrato
                    if loc_name == main_loc_name:
                        continue
                        
                    # Se il luogo non ha già un priority_score, calcolalo
                    if "priority_score" not in loc_data:
                        # Calcola il punteggio come in select_main_location
                        occurrence_score = loc_data["count"] / max_count
                        early_appearance_bonus = 1.0 if loc_data.get("early_appearance", False) else 0.0
                        spacy_loc_bonus = 0.5 if loc_data.get("spacy_label", "") == "LOC" else 0.0
                        
                        # Usa valore binario per la confidenza
                        is_location = loc_data["category"] != "non_luogo"
                        location_confidence = 1.0 if is_location else 0.0
                        
                        priority_score = (
                            weights["occurrence"] * occurrence_score + 
                            weights["confidence"] * location_confidence +
                            weights["early_appearance"] * early_appearance_bonus +
                            weights["spacy_loc_bonus"] * spacy_loc_bonus
                        )
                    else:
                        priority_score = loc_data["priority_score"]
                    
                    # Aggiungi alla lista dei luoghi con punteggio
                    scored_locations.append((loc_name, priority_score))
                
                # Ordina per punteggio e prendi i primi 10
                scored_locations.sort(key=lambda x: x[1], reverse=True)
                
                for loc_name, score in scored_locations[:10]:
                    writer.writerow([f"[{loc_name}, {score:.2f}]"])
                
                # Aggiungi una riga vuota tra i capitoli
                writer.writerow([])
                
            except Exception as e:
                writer.writerow([f"Errore nell'elaborazione del capitolo {chapter_num}: {str(e)}"])
                writer.writerow([])
                logging.error(f"Errore nell'elaborazione del file di statistiche per il capitolo {chapter_num}: {e}")
    
    print(f"File di statistiche generato: {stats_file}")




def count_tokens(text):
    """
    Conta il numero di token in un testo in modo approssimativo.
    Questa versione non usa spaCy per evitare dipendenze.
    """
    # Approssimazione rudimentale dei token (parole)
    return len(text.split())




def analyze_token_metrics(book_name, output_dir):
    """
    Analizza la correlazione tra numero di token e qualità dell'analisi.
    Genera un file CSV e dati per grafici, usando i dati già elaborati.
    """
    metrics_file = os.path.join(output_dir, f"token_metrics-{book_name}.csv")
    chapter_files = []
    
    # Trova tutti i file di analisi dei capitoli
    for file in os.listdir(output_dir):
        if file.startswith(f"{book_name}-capitolo") and file.endswith("-analysis.csv"):
            chapter_files.append(file)
    
    # Ordina i file per numero di capitolo
    chapter_files.sort(key=lambda x: int(x.split("capitolo")[1].split("-")[0]))
    
    # Prepara i dati per il CSV
    metrics_data = []
    
    for chapter_file in chapter_files:
        chapter_num = int(chapter_file.split("capitolo")[1].split("-")[0])
        file_path = os.path.join(output_dir, chapter_file)
        
        # Carica le metriche di analisi
        main_location = None
        main_character = None
        emotion_data = None
        processing_times = None
        token_count = None
        
        with open(file_path, 'r', encoding='utf-8') as cf:
            reader = csv.reader(cf)
            chapter_data = list(reader)
        
        for row in chapter_data:
            if len(row) < 2:
                continue
                
            if row[0] == "Token Count":
                try:
                    token_count = int(row[1])
                except:
                    token_count = None
                    
            elif row[0] == "Main Location":
                try:
                    main_location = ast.literal_eval(row[1])
                except:
                    main_location = None
                    
            elif row[0] == "Main Character":
                try:
                    main_character = ast.literal_eval(row[1])
                except:
                    main_character = None
                    
            elif row[0] == "Emotions":
                try:
                    emotion_data = ast.literal_eval(row[1])
                except:
                    emotion_data = None
                    
            elif row[0] == "Tempi di analisi":
                try:
                    processing_times = ast.literal_eval(row[1])
                except:
                    processing_times = None
        
        # Se non abbiamo trovato un conteggio token, passiamo al prossimo capitolo
        if not token_count:
            logging.warning(f"Conteggio token non trovato per il capitolo {chapter_num}")
            continue
            
        # Estrai metriche rilevanti
        loc_confidence = main_location.get("confidence", 0) if main_location else 0
        loc_score = main_location.get("priority_score", 0) if main_location else 0
        char_score = main_character.get("priority_score", 0) if main_character else 0
        
        dominant_emotion = emotion_data.get("dominant_emotion", "unknown") if emotion_data else "unknown"
        dominant_sentiment = emotion_data.get("dominant_sentiment", "unknown") if emotion_data else "unknown"
        
        spacy_time = processing_times.get("Analisi con spaCy", 0) if processing_times else 0
        emotion_time = processing_times.get("Analisi emozioni", 0) if processing_times else 0
        location_time = processing_times.get("Classificazione delle location", 0) if processing_times else 0
        total_time = processing_times.get("Tempo totale", 0) if processing_times else 0
        
        # Calcola token per secondo
        tokens_per_second = token_count / total_time if total_time > 0 else 0
        
        # Aggiungi dati alle metriche
        metrics_data.append({
            "chapter": chapter_num,
            "token_count": token_count,
            "tokens_per_second": tokens_per_second,
            "total_time": total_time,
            "spacy_time": spacy_time,
            "emotion_time": emotion_time,
            "location_time": location_time,
            "loc_confidence": loc_confidence,
            "loc_score": loc_score,
            "char_score": char_score,
            "dominant_emotion": dominant_emotion,
            "dominant_sentiment": dominant_sentiment
        })
    
    # Scrivi i dati nel file CSV
    with open(metrics_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            "chapter", "token_count", "tokens_per_second", "total_time", 
            "spacy_time", "emotion_time", "location_time", 
            "loc_confidence", "loc_score", "char_score",
            "dominant_emotion", "dominant_sentiment"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for data in metrics_data:
            writer.writerow(data)
            
    # Genera grafici (richiede matplotlib)
    try:
        generate_token_analysis_charts(metrics_data, book_name, output_dir)
    except Exception as e:
        logging.error(f"Errore nella generazione dei grafici: {e}")
        
    return metrics_file




def generate_token_analysis_charts(metrics_data, book_name, output_dir):
    """
    Genera grafici per l'analisi dei token.
    Richiede matplotlib e pandas.
    """
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
        import numpy as np
        
        # Converti i dati in DataFrame
        df = pd.DataFrame(metrics_data)
        
        # 1. Grafico: Token per capitolo
        plt.figure(figsize=(12, 6))
        plt.bar(df['chapter'], df['token_count'])
        plt.title(f'Token per capitolo - {book_name}')
        plt.xlabel('Capitolo')
        plt.ylabel('Numero di token')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.savefig(os.path.join(output_dir, f'{book_name}-token_per_capitolo.png'))
        plt.close()
        
        # 2. Grafico: Tempo di analisi per token
        plt.figure(figsize=(12, 6))
        plt.plot(df['chapter'], df['tokens_per_second'], marker='o', linestyle='-')
        plt.title(f'Performance di analisi - {book_name}')
        plt.xlabel('Capitolo')
        plt.ylabel('Token al secondo')
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join(output_dir, f'{book_name}-performance_analisi.png'))
        plt.close()
        
        # 3. Grafico: Distribuzione tempo di analisi
        plt.figure(figsize=(14, 7))
        
        # Crea dati per grafico a barre impilate
        spacy_times = df['spacy_time'].values
        emotion_times = df['emotion_time'].values
        location_times = df['location_time'].values
        other_times = df['total_time'] - (spacy_times + emotion_times + location_times)
        
        # Posizioni delle barre
        ind = np.arange(len(df['chapter']))
        width = 0.6
        
        # Crea le barre impilate
        plt.bar(ind, spacy_times, width, label='spaCy')
        plt.bar(ind, emotion_times, width, bottom=spacy_times, label='Emozioni')
        plt.bar(ind, location_times, width, bottom=spacy_times+emotion_times, label='Luoghi')
        plt.bar(ind, other_times, width, bottom=spacy_times+emotion_times+location_times, label='Altro')
        
        plt.title(f'Distribuzione tempo di analisi - {book_name}')
        plt.xlabel('Capitolo')
        plt.ylabel('Tempo (secondi)')
        plt.legend()
        plt.xticks(ind, df['chapter'])
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        plt.savefig(os.path.join(output_dir, f'{book_name}-distribuzione_tempi.png'))
        plt.close()
        
        # 4. Grafico: Scatterplot token vs tempo
        plt.figure(figsize=(10, 8))
        plt.scatter(df['token_count'], df['total_time'])
        
        # Aggiunta linea di tendenza
        z = np.polyfit(df['token_count'], df['total_time'], 1)
        p = np.poly1d(z)
        plt.plot(df['token_count'], p(df['token_count']), "r--", alpha=0.8)
        
        plt.title(f'Relazione token-tempo - {book_name}')
        plt.xlabel('Numero di token')
        plt.ylabel('Tempo totale (secondi)')
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join(output_dir, f'{book_name}-token_vs_tempo.png'))
        plt.close()
        
        # 5. Grafico: Emozioni dominanti per capitolo
        emotion_counts = df['dominant_emotion'].value_counts()
        
        plt.figure(figsize=(10, 6))
        emotion_counts.plot(kind='pie', autopct='%1.1f%%')
        plt.title(f'Distribuzione emozioni - {book_name}')
        plt.ylabel('')
        plt.savefig(os.path.join(output_dir, f'{book_name}-emozioni.png'))
        plt.close()
        
        return True
    except Exception as e:
        logging.error(f"Errore nella generazione dei grafici: {e}")
        return False




def evaluate_bert_location_classifier(test_data_file=None):
    """
    Valuta l'accuratezza del modello BERT fine-tuned per le location.
    
    Args:
        test_data_file: Percorso al file di test. Se None, usa dati predefiniti.
    
    Returns:
        Dict con metriche di valutazione
    """
    if test_data_file is None:
        # Se non viene fornito un file di test, crea un piccolo dataset di test
        test_data = [
            {"location": "Hogwarts", "category": "scuola di magia"},
            {"location": "Foresta Proibita", "category": "foresta magica"},
            {"location": "Londra", "category": "città"},
            {"location": "La Tana", "category": "casa"},
            {"location": "Serpeverde", "category": "non_luogo"},
            {"location": "Tassorosso", "category": "non_luogo"},
            {"location": "Grifondoro", "category": "non_luogo"},
            {"location": "Corvonero", "category": "non_luogo"},
            {"location": "Ministero della Magia", "category": "ministero"},
            {"location": "Gringott", "category": "banca magica"},
            {"location": "Privet Drive", "category": "strada"},
            {"location": "Campo da Quidditch", "category": "campo"},
            {"location": "Diagon Alley", "category": "strada"},
            {"location": "Notturn Alley", "category": "strada"},
            {"location": "Hogsmeade", "category": "villaggio magico"}
        ]
    else:
        # Carica i dati di test dal file
        with open(test_data_file, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
    
    # Carica il modello e il tokenizer
    try:
        model = BertForSequenceClassification.from_pretrained("./bert_location_classifier")
        tokenizer = BertTokenizerFast.from_pretrained("./bert_location_classifier")
        
        # Carica il mapping delle categorie
        with open("./bert_location_classifier/category_mapping.json", "r") as f:
            category_mapping = json.load(f)
        id_to_category = {int(k): v for k, v in category_mapping["id_to_category"].items()}
        category_to_id = {v: int(k) for k, v in category_mapping["id_to_category"].items()}
    except Exception as e:
        logging.error(f"Errore nel caricamento del modello BERT: {e}")
        return {"error": str(e)}
    
    # Metriche di valutazione
    correct = 0
    total = 0
    predictions = []
    confusion_matrix = {}
    
    # Valuta ogni esempio
    for example in test_data:
        location = example["location"]
        true_category = example["category"]
        
        # Verifica se la categoria è presente nel mapping
        if true_category not in category_to_id:
            continue
            
        try:
            # Predizione
            inputs = tokenizer(
                location,
                "",  # Contesto vuoto per semplicità
                return_tensors="pt",
                truncation=True,
                padding=True
            )
            
            with torch.no_grad():
                outputs = model(**inputs)
            
            # Ottieni la categoria predetta
            predicted_class_id = outputs.logits.argmax().item()
            predicted_category = id_to_category[predicted_class_id]
            confidence = torch.softmax(outputs.logits, dim=1)[0, predicted_class_id].item()
            
            # Aggiorna le metriche
            total += 1
            if predicted_category == true_category:
                correct += 1
                
            # Salva la predizione
            predictions.append({
                "location": location,
                "true_category": true_category,
                "predicted_category": predicted_category,
                "confidence": confidence,
                "correct": predicted_category == true_category
            })
            
            # Aggiorna la matrice di confusione
            if true_category not in confusion_matrix:
                confusion_matrix[true_category] = {}
            if predicted_category not in confusion_matrix[true_category]:
                confusion_matrix[true_category][predicted_category] = 0
            confusion_matrix[true_category][predicted_category] += 1
            
        except Exception as e:
            logging.error(f"Errore nella valutazione dell'esempio {location}: {e}")
    
    # Calcola l'accuratezza
    accuracy = correct / total if total > 0 else 0
    
    # Organizza i risultati
    results = {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "predictions": predictions,
        "confusion_matrix": confusion_matrix
    }
    
    # Salva i risultati
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    result_file = f"bert_evaluation_{timestamp}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Genera un grafico della matrice di confusione
    try:
        generate_confusion_matrix_chart(confusion_matrix, f"bert_confusion_matrix_{timestamp}.png")
    except Exception as e:
        logging.error(f"Errore nella generazione della matrice di confusione: {e}")
    
    return results




def generate_confusion_matrix_chart(confusion_matrix, output_file):
    """
    Genera un grafico della matrice di confusione.
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        import seaborn as sns
        
        # Estrai tutte le categorie
        categories = set()
        for true_cat in confusion_matrix:
            categories.add(true_cat)
            for pred_cat in confusion_matrix[true_cat]:
                categories.add(pred_cat)
        
        categories = sorted(list(categories))
        n_categories = len(categories)
        
        # Crea la matrice
        matrix = np.zeros((n_categories, n_categories))
        
        # Riempi la matrice
        for i, true_cat in enumerate(categories):
            if true_cat in confusion_matrix:
                for j, pred_cat in enumerate(categories):
                    if pred_cat in confusion_matrix[true_cat]:
                        matrix[i, j] = confusion_matrix[true_cat][pred_cat]
        
        # Normalizza per riga (true label)
        row_sums = matrix.sum(axis=1, keepdims=True)
        norm_matrix = np.zeros_like(matrix, dtype=float)
        for i in range(n_categories):
            if row_sums[i] > 0:
                norm_matrix[i] = matrix[i] / row_sums[i]
        
        # Crea il grafico
        plt.figure(figsize=(12, 10))
        sns.heatmap(
            norm_matrix, 
            annot=True, 
            fmt=".2f", 
            xticklabels=categories, 
            yticklabels=categories,
            cmap="Blues"
        )
        plt.xlabel('Categoria predetta')
        plt.ylabel('Categoria reale')
        plt.title('Matrice di confusione normalizzata')
        plt.tight_layout()
        plt.savefig(output_file)
        plt.close()
        
        return True
    except Exception as e:
        logging.error(f"Errore nella generazione della matrice di confusione: {e}")
        return False




def analyze_context_consistency(book_name, output_dir):
    """
    Analizza la coerenza del contesto tra capitoli adiacenti.
    """
    context_file = os.path.join(output_dir, f"context_metrics-{book_name}.csv")
    chapter_files = []
    
    # Trova tutti i file di analisi dei capitoli
    for file in os.listdir(output_dir):
        if file.startswith(f"{book_name}-capitolo") and file.endswith("-analysis.csv"):
            chapter_files.append(file)
    
    # Ordina i file per numero di capitolo
    chapter_files.sort(key=lambda x: int(x.split("capitolo")[1].split("-")[0]))
    
    # Raccogliere dati per ogni capitolo
    chapters_data = []
    
    for chapter_file in chapter_files:
        chapter_num = int(chapter_file.split("capitolo")[1].split("-")[0])
        file_path = os.path.join(output_dir, chapter_file)
        
        main_location = None
        main_character = None
        dominant_emotion = None
        
        with open(file_path, 'r', encoding='utf-8') as cf:
            reader = csv.reader(cf)
            chapter_data = list(reader)
        
        for row in chapter_data:
            if len(row) < 2:
                continue
                
            if row[0] == "Main Location":
                try:
                    main_location = ast.literal_eval(row[1])
                except:
                    main_location = None
                    
            elif row[0] == "Main Character":
                try:
                    main_character = ast.literal_eval(row[1])
                except:
                    main_character = None
                    
            elif row[0] == "Emotions":
                try:
                    emotions = ast.literal_eval(row[1])
                    dominant_emotion = emotions.get("dominant_emotion", None)
                except:
                    dominant_emotion = None
        
        chapters_data.append({
            "chapter": chapter_num,
            "location": main_location.get("name") if main_location else None,
            "location_category": main_location.get("category") if main_location else None,
            "character": main_character.get("name") if main_character else None,
            "emotion": dominant_emotion
        })
    
    # Analizza la coerenza tra capitoli adiacenti
    context_metrics = []
    
    for i in range(1, len(chapters_data)):
        prev_chapter = chapters_data[i-1]
        curr_chapter = chapters_data[i]
        
        # Calcola metriche di coerenza
        location_continuity = prev_chapter["location"] == curr_chapter["location"]
        location_category_continuity = prev_chapter["location_category"] == curr_chapter["location_category"]
        character_continuity = prev_chapter["character"] == curr_chapter["character"]
        emotion_continuity = prev_chapter["emotion"] == curr_chapter["emotion"]
        
        # Calcola un punteggio complessivo di coerenza
        coherence_score = (
            (1 if location_continuity else 0) + 
            (0.5 if location_category_continuity and not location_continuity else 0) +
            (1 if character_continuity else 0) + 
            (0.5 if emotion_continuity else 0)
        ) / 3.0  # Normalizza a 0-1
        
        context_metrics.append({
            "prev_chapter": prev_chapter["chapter"],
            "curr_chapter": curr_chapter["chapter"],
            "location_continuity": location_continuity,
            "location_category_continuity": location_category_continuity,
            "character_continuity": character_continuity,
            "emotion_continuity": emotion_continuity,
            "coherence_score": coherence_score
        })
    
    # Salva le metriche di contesto
    with open(context_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            "prev_chapter", "curr_chapter", 
            "location_continuity", "location_category_continuity", 
            "character_continuity", "emotion_continuity",
            "coherence_score"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for data in context_metrics:
            writer.writerow(data)
    
    # Genera grafici di coerenza del contesto
    try:
        generate_context_charts(context_metrics, chapters_data, book_name, output_dir)
    except Exception as e:
        logging.error(f"Errore nella generazione dei grafici di contesto: {e}")
    
    return context_file




def generate_context_charts(context_metrics, chapters_data, book_name, output_dir):
    """
    Genera grafici per visualizzare la coerenza del contesto.
    """
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
        import networkx as nx
        
        # Converti i dati in DataFrame
        df_metrics = pd.DataFrame(context_metrics)
        df_chapters = pd.DataFrame(chapters_data)
        
        # 1. Grafico: Punteggi di coerenza tra capitoli
        plt.figure(figsize=(14, 6))
        plt.plot(df_metrics['curr_chapter'], df_metrics['coherence_score'], marker='o', linestyle='-')
        plt.axhline(y=0.5, color='r', linestyle='--', alpha=0.5)
        plt.title(f'Coerenza del contesto - {book_name}')
        plt.xlabel('Capitolo')
        plt.ylabel('Punteggio di coerenza')
        plt.grid(True, alpha=0.3)
        plt.ylim(0, 1.05)
        plt.savefig(os.path.join(output_dir, f'{book_name}-coerenza_contesto.png'))
        plt.close()
        
        # 2. Grafico: Rete delle transizioni tra luoghi
        plt.figure(figsize=(12, 10))
        G = nx.DiGraph()
        
        # Aggiungi i nodi per ogni luogo
        locations = {}
        for chapter in chapters_data:
            loc = chapter.get("location")
            if loc:
                if loc not in locations:
                    locations[loc] = 0
                locations[loc] += 1
                G.add_node(loc)
        
        # Aggiungi gli archi per le transizioni
        for i in range(1, len(chapters_data)):
            prev_loc = chapters_data[i-1].get("location")
            curr_loc = chapters_data[i].get("location")
            if prev_loc and curr_loc and prev_loc != curr_loc:
                if G.has_edge(prev_loc, curr_loc):
                    G[prev_loc][curr_loc]["weight"] += 1
                else:
                    G.add_edge(prev_loc, curr_loc, weight=1)
        
        # Determina le dimensioni dei nodi in base alla frequenza
        node_sizes = [locations[loc]*100 for loc in G.nodes()]
        
        # Determina le larghezze degli archi in base al peso
        edge_weights = [G[u][v]["weight"] for u, v in G.edges()]
        
        # Layout della rete
        pos = nx.spring_layout(G, seed=42)
        
        # Disegna la rete
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color="skyblue", alpha=0.8)
        nx.draw_networkx_edges(G, pos, width=edge_weights, alpha=0.5, edge_color="gray", arrows=True)
        nx.draw_networkx_labels(G, pos, font_size=8)
        
        plt.title(f'Rete di transizioni tra luoghi - {book_name}')
        plt.axis('off')
        plt.savefig(os.path.join(output_dir, f'{book_name}-transizioni_luoghi.png'))
        plt.close()
        
        # 3. Grafico: Distribuzione delle continuità
        categories = ["Location", "Category", "Character", "Emotion"]
        values = [
            df_metrics['location_continuity'].mean() * 100,
            df_metrics['location_category_continuity'].mean() * 100,
            df_metrics['character_continuity'].mean() * 100,
            df_metrics['emotion_continuity'].mean() * 100
        ]
        
        plt.figure(figsize=(10, 6))
        plt.bar(categories, values)
        plt.title(f'Percentuale di continuità tra capitoli - {book_name}')
        plt.ylabel('Percentuale (%)')
        plt.ylim(0, 100)
        
        # Aggiungi le percentuali sopra le barre
        for i, v in enumerate(values):
            plt.text(i, v + 2, f"{v:.1f}%", ha='center')
        
        plt.savefig(os.path.join(output_dir, f'{book_name}-continuita_percentuale.png'))
        plt.close()
        
        return True
    except Exception as e:
        logging.error(f"Errore nella generazione dei grafici di contesto: {e}")
        return False




def main():
    """
    Funzione principale che esegue l'analisi delle statistiche sui dati già elaborati.
    """
    # Analizza gli argomenti
    parser = argparse.ArgumentParser(description="Generatore di statistiche per analisi di libri")
    parser.add_argument("--dir", type=str, required=True,
                        help="Directory contenente i file di analisi")
    parser.add_argument("--book", type=str, required=True,
                        help="Nome del libro da analizzare")
    parser.add_argument("--evaluate-bert", action="store_true",
                        help="Valuta l'accuratezza del modello BERT per luoghi")
    parser.add_argument("--test-data", type=str,
                        help="File JSON con dati di test per BERT")
    
    args = parser.parse_args()
    
    print(f"Generazione statistiche per '{args.book}' in {args.dir}")
    
    try:
        # Genera il file di statistiche
        print("\n1. Generazione file di statistiche...")
        stats_file = generate_stats_file(args.book, args.dir)
        
        # Analizza le metriche dei token
        print("\n2. Analisi delle metriche dei token...")
        token_metrics_file = analyze_token_metrics(args.book, args.dir)
        
        # Analizza la coerenza del contesto
        print("\n3. Analisi della coerenza del contesto tra capitoli...")
        context_metrics_file = analyze_context_consistency(args.book, args.dir)
        
        # Valuta il modello BERT se richiesto
        if args.evaluate_bert:
            print("\n4. Valutazione del modello BERT per la classificazione dei luoghi...")
            results = evaluate_bert_location_classifier(args.test_data)
            print(f"   Accuratezza: {results['accuracy']:.2%}")
            print(f"   Predizioni corrette: {results['correct']}/{results['total']}")
            print(f"   Risultati dettagliati salvati in: {datetime.datetime.now().strftime('bert_evaluation_%Y%m%d-%H%M%S.json')}")
        
        print("\nGenerazione delle statistiche completata con successo!")
        
        return 0
    except Exception as e:
        print(f"Errore durante la generazione delle statistiche: {e}")
        logging.error(f"Errore durante la generazione delle statistiche: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())