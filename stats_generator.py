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
    
    if not chapter_files:
        logging.error(f"Nessun file di analisi trovato per {book_name}")
        return None
        
    # Ordina i file per numero di capitolo
    chapter_files.sort(key=lambda x: int(x.split("capitolo")[1].split("-")[0]))
    
    try:
        # Crea il file di statistiche
        with open(stats_file, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            
            for chapter_file in chapter_files:
                try:
                    chapter_num = int(chapter_file.split("capitolo")[1].split("-")[0])
                    file_path = os.path.join(output_dir, chapter_file)
                    
                    # Carica i dati del capitolo
                    with open(file_path, 'r', encoding='utf-8') as cf:
                        reader = csv.reader(cf)
                        chapter_data = list(reader)
                    
                    # Estrai i dati necessari
                    main_location = None
                    locations = {}
                    times = {}
                    token_count = None
                    
                    for row in chapter_data:
                        if len(row) < 2:
                            continue
                            
                        if row[0] == "Main Location":
                            try:
                                main_location = ast.literal_eval(row[1]) if row[1] != "None" else None
                            except Exception as e:
                                logging.warning(f"Errore nell'interpretazione della location principale: {e}")
                                main_location = {"name": "Sconosciuto", "priority_score": 0}
                                
                        elif row[0] == "Potential Locations":
                            try:
                                locations = ast.literal_eval(row[1]) if row[1] != "None" else {}
                            except Exception as e:
                                logging.warning(f"Errore nell'interpretazione delle location potenziali: {e}")
                                locations = {}
                                
                        elif row[0] == "Tempi di analisi":
                            try:
                                times = ast.literal_eval(row[1]) if row[1] != "None" else {}
                            except Exception as e:
                                logging.warning(f"Errore nell'interpretazione dei tempi: {e}")
                                times = {}
                                
                        elif row[0] == "Token Count":
                            try:
                                token_count = int(row[1])
                            except Exception as e:
                                logging.warning(f"Errore nell'interpretazione del conteggio token: {e}")
                                token_count = 0
                    
                    # Calcola la dimensione del capitolo
                    num_pages = max(1, token_count // 500) if token_count else 1  # approssimazione: 500 token per pagina
                    
                    # Scrivi l'intestazione del capitolo
                    writer.writerow([f"Capitolo {chapter_num}:"])
                    writer.writerow([f"{token_count} token - {num_pages} pagine"])
                    
                    # Scrivi i tempi di analisi
                    times_str = ", ".join([f"{k}: {v:.2f}s" for k, v in times.items()]) if times else "Dati non disponibili"
                    writer.writerow([f"Tempi di analisi: {times_str}"])
                    
                    # Scrivi il luogo principale
                    if main_location and "name" in main_location:
                        writer.writerow([f"{main_location['name']}: {main_location.get('priority_score', 0):.2f}"])
                    else:
                        writer.writerow(["Luogo principale non identificato"])
                    
                    # Scrivi gli altri luoghi (fino a 10, ordinati per priority_score)
                    writer.writerow(["Altri luoghi:"])
                    
                    # Filtra i luoghi che non sono il luogo principale
                    other_locations = []
                    if locations:
                        main_loc_name = main_location.get("name") if main_location else None
                        for loc_name, loc_data in locations.items():
                            if loc_name != main_loc_name:
                                priority_score = loc_data.get("priority_score", 0)
                                other_locations.append((loc_name, priority_score))
                    
                        # Ordina per priority_score
                        other_locations.sort(key=lambda x: x[1], reverse=True)
                        
                        # Scrivi i primi 10 luoghi
                        for loc_name, priority_score in other_locations[:10]:
                            writer.writerow([f"[{loc_name}, {priority_score:.2f}]"])
                    else:
                        writer.writerow(["Nessun luogo alternativo trovato"])
                    
                    # Aggiungi una riga vuota tra i capitoli
                    writer.writerow([])
                    
                except Exception as e:
                    writer.writerow([f"Errore nell'elaborazione del capitolo {chapter_num}: {str(e)}"])
                    writer.writerow([])
                    logging.error(f"Errore nell'elaborazione del file di statistiche per il capitolo {chapter_num}: {e}")
        
        print(f"File di statistiche generato: {stats_file}")
        return stats_file
    except Exception as e:
        logging.error(f"Errore nella creazione del file di statistiche: {e}")
        return None



def count_tokens(text):
    """
    Conta il numero di token in un testo in modo approssimativo.
    Questa versione non usa spaCy per evitare dipendenze.
    """
    # Approssimazione rudimentale dei token (parole)
    return len(text.split())




# In analyze_token_metrics()
def analyze_token_metrics(book_name, output_dir):
    """
    Analizza la correlazione tra numero di token e qualità dell'analisi.
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
        try:
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
                        token_count = 0
                        
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
                token_count = 0
            
            # Estrai metriche rilevanti con controlli di sicurezza
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
        except Exception as e:
            logging.error(f"Errore nell'analisi del capitolo {chapter_file}: {e}")
    
    # Scrivi i dati nel file CSV
    if not metrics_data:
        logging.warning("Nessuna metrica trovata per generare il file token_metrics")
        return None

    try:
        with open(metrics_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ["chapter", "token_count", "tokens_per_second", "total_time", 
                         "spacy_time", "emotion_time", "location_time", 
                         "loc_confidence", "loc_score", "char_score", 
                         "dominant_emotion", "dominant_sentiment"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for data in metrics_data:
                writer.writerow(data)
        
        print(f"File di metriche dei token generato: {metrics_file}")
        
        # Genera i grafici in modo indipendente
        try:
            generate_token_analysis_charts(metrics_data, output_dir, book_name)
        except Exception as e:
            logging.error(f"Errore nella generazione dei grafici: {e}")
        
        return metrics_file
    except Exception as e:
        logging.error(f"Errore nella scrittura del file di metriche dei token: {e}")
        return None



def generate_token_analysis_charts(metrics_data, output_dir, book_name):
    """Genera grafici per l'analisi dei token"""
    if not metrics_data or len(metrics_data) == 0:
        logging.warning("Nessun dato disponibile per generare grafici")
        return
    
    try:
        # Estrai i dati dai dizionari per i grafici
        chapters = [d.get("chapter", 0) for d in metrics_data]
        token_counts = [d.get("token_count", 0) for d in metrics_data]
        tokens_per_second = [d.get("tokens_per_second", 0) for d in metrics_data]
        total_times = [d.get("total_time", 0) for d in metrics_data]
        spacy_times = [d.get("spacy_time", 0) for d in metrics_data]
        emotion_times = [d.get("emotion_time", 0) for d in metrics_data]
        location_times = [d.get("location_time", 0) for d in metrics_data]
        
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
    Valuta l'accuratezza del modello BERT fine-tuned per le location con metriche ML standard.
    
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
    
    # Prepara le liste per le metriche avanzate
    y_true = [p["true_category"] for p in predictions]
    y_pred = [p["predicted_category"] for p in predictions]
    
    # Import qui per evitare dipendenze non necessarie se la funzione non viene chiamata
    from sklearn.metrics import precision_recall_fscore_support, classification_report
    
    # Calcola precision, recall, f1-score per ogni categoria
    unique_categories = sorted(set(y_true + y_pred))
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average=None, 
        labels=unique_categories
    )
    
    # Calcola le metriche medie (weighted evita problemi con classi sbilanciate)
    avg_precision, avg_recall, avg_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average='weighted'
    )
    
    # Genera un report dettagliato
    report = classification_report(y_true, y_pred, output_dict=True)
    
    # Organizza i risultati
    results = {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "predictions": predictions,
        "confusion_matrix": confusion_matrix,
        "precision": precision.tolist(),
        "recall": recall.tolist(),
        "f1": f1.tolist(),
        "support": support.tolist(),
        "categories": unique_categories,
        "weighted_precision": avg_precision,
        "weighted_recall": avg_recall, 
        "weighted_f1": avg_f1,
        "classification_report": report
    }
    
    # Salva i risultati
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    result_file = f"bert_evaluation_{timestamp}.json"
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Genera un grafico della matrice di confusione
    try:
        generate_confusion_matrix_chart(confusion_matrix, unique_categories, f"bert_confusion_matrix_{timestamp}.png")
    except Exception as e:
        logging.error(f"Errore nella generazione della matrice di confusione: {e}")
    
    return results



def generate_confusion_matrix_chart(confusion_matrix, categories, output_file):
    """
    Genera un grafico dettagliato della matrice di confusione.
    
    Args:
        confusion_matrix: Dizionario a due livelli con conteggi
        categories: Lista di tutte le categorie
        output_file: Percorso dove salvare l'immagine
    """
    try:
        # Crea la matrice
        matrix = np.zeros((len(categories), len(categories)))
        
        # Riempi la matrice
        for i, true_cat in enumerate(categories):
            if true_cat in confusion_matrix:
                for j, pred_cat in enumerate(categories):
                    if pred_cat in confusion_matrix[true_cat]:
                        matrix[i, j] = confusion_matrix[true_cat][pred_cat]
        
        # Normalizza per riga (true label)
        row_sums = matrix.sum(axis=1, keepdims=True)
        norm_matrix = np.zeros_like(matrix, dtype=float)
        for i in range(len(categories)):
            if row_sums[i] > 0:
                norm_matrix[i] = matrix[i] / row_sums[i]
        
        # Crea il grafico
        plt.figure(figsize=(14, 12))
        
        # Heatmap con valori assoluti
        plt.subplot(1, 2, 1)
        sns.heatmap(
            matrix, 
            annot=True, 
            fmt="d", 
            xticklabels=categories, 
            yticklabels=categories,
            cmap="Blues"
        )
        plt.xlabel('Categoria predetta')
        plt.ylabel('Categoria reale')
        plt.title('Matrice di confusione (valori assoluti)')
        
        # Heatmap normalizzata
        plt.subplot(1, 2, 2)
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
        plt.savefig(output_file, dpi=300)
        plt.close()
        
        return True
    except Exception as e:
        logging.error(f"Errore nella generazione della matrice di confusione: {e}")
        return False



def analyze_context_consistency(book_name, output_dir):
    """
    Analizza la coerenza del contesto tra capitoli adiacenti.
    """
    metrics_file = os.path.join(output_dir, f"context_metrics-{book_name}.csv")
    chapter_files = []
    
    # Trova tutti i file di analisi dei capitoli
    for file in os.listdir(output_dir):
        if file.startswith(f"{book_name}-capitolo") and file.endswith("-analysis.csv"):
            chapter_files.append(file)
    
    # Ordina i file per numero di capitolo
    chapter_files.sort(key=lambda x: int(x.split("capitolo")[1].split("-")[0]))
    
    # Prepara i dati per il CSV
    metrics_data = []
    
    # Carica i dati di ogni capitolo
    chapter_data_dict = {}
    for chapter_file in chapter_files:
        try:
            chapter_num = int(chapter_file.split("capitolo")[1].split("-")[0])
            file_path = os.path.join(output_dir, chapter_file)
            
            # Carica le metriche di analisi
            main_location = None
            main_character = None
            emotion_data = None
            
            with open(file_path, 'r', encoding='utf-8') as cf:
                reader = csv.reader(cf)
                content = list(reader)
            
            for row in content:
                if len(row) < 2:
                    continue
                    
                if row[0] == "Main Location":
                    try:
                        main_location = ast.literal_eval(row[1])
                    except:
                        main_location = {"name": "unknown", "category": "unknown"}
                        
                elif row[0] == "Main Character":
                    try:
                        main_character = ast.literal_eval(row[1])
                    except:
                        main_character = {"name": "unknown"}
                        
                elif row[0] == "Emotions":
                    try:
                        emotion_data = ast.literal_eval(row[1])
                    except:
                        emotion_data = {"dominant_emotion": "unknown"}
            
            # Salva i dati del capitolo
            chapter_data_dict[chapter_num] = {
                "location": main_location.get("name") if main_location else "unknown",
                "location_category": main_location.get("category") if main_location else "unknown",
                "character": main_character.get("name") if main_character else "unknown",
                "emotion": emotion_data.get("dominant_emotion") if emotion_data else "unknown"
            }
        except Exception as e:
            logging.error(f"Errore nell'analisi del capitolo {chapter_file}: {e}")
    
    # Calcola le metriche di coerenza tra capitoli adiacenti
    chapter_nums = sorted(chapter_data_dict.keys())
    
    for i in range(len(chapter_nums) - 1):
        prev_chapter = chapter_nums[i]
        curr_chapter = chapter_nums[i + 1]
        
        try:
            prev_data = chapter_data_dict[prev_chapter]
            curr_data = chapter_data_dict[curr_chapter]
            
            # Calcola la continuità
            location_continuity = 1.0 if prev_data["location"] == curr_data["location"] else 0.0
            location_category_continuity = 1.0 if prev_data["location_category"] == curr_data["location_category"] else 0.0
            character_continuity = 1.0 if prev_data["character"] == curr_data["character"] else 0.0
            emotion_continuity = 1.0 if prev_data["emotion"] == curr_data["emotion"] else 0.0
            
            # Calcola un punteggio di coerenza complessivo
            coherence_score = (location_continuity * 0.4 + 
                              location_category_continuity * 0.2 + 
                              character_continuity * 0.3 + 
                              emotion_continuity * 0.1)
            
            # Aggiungi i dati alle metriche
            metrics_data.append({
                "prev_chapter": prev_chapter,
                "curr_chapter": curr_chapter,
                "location_continuity": location_continuity,
                "location_category_continuity": location_category_continuity,
                "character_continuity": character_continuity,
                "emotion_continuity": emotion_continuity,
                "coherence_score": coherence_score
            })
        except KeyError:
            logging.error(f"Dati mancanti per i capitoli {prev_chapter} o {curr_chapter}")
    
    # Scrivi i dati nel file CSV
    if not metrics_data:
        logging.warning("Nessuna metrica di contesto trovata da generare")
        return None

    try:
        with open(metrics_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ["prev_chapter", "curr_chapter", "location_continuity", 
                        "location_category_continuity", "character_continuity", 
                        "emotion_continuity", "coherence_score"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for data in metrics_data:
                writer.writerow(data)
        
        print(f"File di metriche di contesto generato: {metrics_file}")
        
        # Genera i grafici in modo indipendente
        try:
            generate_context_charts(metrics_data, chapter_data_dict, output_dir, book_name)
        except Exception as e:
            logging.error(f"Errore nella generazione dei grafici di contesto: {e}")
        
        return metrics_file
    except Exception as e:
        logging.error(f"Errore nella scrittura del file di metriche di contesto: {e}")
        return None



def generate_context_charts(metrics_data, chapter_data_dict, output_dir, book_name):
    """Genera grafici per l'analisi della coerenza del contesto"""
    if not metrics_data or len(metrics_data) == 0:
        logging.warning("Nessun dato disponibile per generare grafici di contesto")
        return
        
    try:
        # Estrai i dati dai dizionari per i grafici
        prev_chapters = [d.get("prev_chapter", 0) for d in metrics_data]
        curr_chapters = [d.get("curr_chapter", 0) for d in metrics_data]
        coherence_scores = [d.get("coherence_score", 0) for d in metrics_data]
        
        # Converti i dati in DataFrame
        df_metrics = pd.DataFrame(metrics_data)
        
        # Verifica che chapter_data_dict sia un dizionario e non una lista di dizionari
        if not isinstance(chapter_data_dict, dict):
            logging.error("chapter_data_dict non è un dizionario")
            return False
            
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
        for chapter_num, chapter_data in chapter_data_dict.items():
            loc = chapter_data.get("location", "unknown")
            if loc not in locations:
                locations[loc] = 0
            locations[loc] += 1
            G.add_node(loc)
        
        # Aggiungi gli archi per le transizioni
        chapters = sorted(chapter_data_dict.keys())
        for i in range(1, len(chapters)):
            prev_chapter = chapters[i-1]
            curr_chapter = chapters[i]
            
            prev_loc = chapter_data_dict[prev_chapter].get("location", "unknown")
            curr_loc = chapter_data_dict[curr_chapter].get("location", "unknown")
            
            if prev_loc != curr_loc:
                if G.has_edge(prev_loc, curr_loc):
                    G[prev_loc][curr_loc]["weight"] += 1
                else:
                    G.add_edge(prev_loc, curr_loc, weight=1)
        
        # Determina le dimensioni dei nodi in base alla frequenza
        node_sizes = [locations.get(loc, 1)*100 for loc in G.nodes()]
        
        # Determina le larghezze degli archi in base al peso
        edge_weights = [G[u][v].get("weight", 1) for u, v in G.edges()]
        
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