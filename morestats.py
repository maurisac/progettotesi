import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import re
import os
import ast
import json

# Directory base
results_dir = r"c:/Users/Maurizio/Desktop/progettotesi/analyses"
output_dir = r"c:/Users/Maurizio/Desktop/progettotesi/presentation_charts"
os.makedirs(output_dir, exist_ok=True)

# Libri analizzati
books = [
    "Harry Potter E la Pietra Filosofale (J. K. Rowling)",
    "Le Cronache Di Narnia. Il Leone La Strega e L’armadio (Lewis, C.S.)",
    "L’occhio del mondo (Jordan Robert)"
]
book_display_names = ["Harry Potter", "Narnia", "Ruota del Tempo"]
book_colors = ['#e74c3c', '#3498db', '#2ecc71']

# 1. Tempi di elaborazione per componente
def generate_processing_time_chart():
    print("Generazione grafico tempi di elaborazione per componente...")
    
    # Strutture dati per i tempi
    book_data = []
    
    for book in books:
        stats_file = os.path.join(results_dir, book, f"stats-{book}.csv")
        if not os.path.exists(stats_file):
            print(f"File non trovato: {stats_file}")
            continue
            
        with open(stats_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Estrai tempi di elaborazione
        times_pattern = r'"Tempi di analisi: Analisi con spaCy: ([\d\.]+)s, Riconoscimento entità con spaCy: ([\d\.]+)s, Analisi emozioni: ([\d\.]+)s, Classificazione delle location: ([\d\.]+)s'
        times_matches = re.findall(times_pattern, content)
        
        if not times_matches:
            print(f"Nessun dato sui tempi trovato per {book}")
            continue
            
        # Calcola media per ogni componente
        spacy_times = [float(t[0]) for t in times_matches]
        entity_times = [float(t[1]) for t in times_matches]
        emotion_times = [float(t[2]) for t in times_matches]
        location_times = [float(t[3]) for t in times_matches]
        
        # Aggiungi al dataset
        book_data.append({
            'book': book,
            'display_name': book_display_names[books.index(book)],
            'spacy': np.mean(spacy_times),
            'entity': np.mean(entity_times),
            'emotion': np.mean(emotion_times),
            'location': np.mean(location_times)
        })
    
    if not book_data:
        print("Nessun dato disponibile per generare il grafico")
        return
        
    # Crea un DataFrame
    df = pd.DataFrame(book_data)
    
    # Prepara i dati per il grafico
    components = ['spacy', 'entity', 'emotion', 'location']
    component_labels = ['Analisi con spaCy', 'Riconoscimento entità', 'Analisi emozioni', 'Classificazione luoghi']
    
    # Crea grafico a barre raggruppate
    fig, ax = plt.subplots(figsize=(12, 8))
    
    bar_width = 0.2
    index = np.arange(len(components))
    
    for i, row in enumerate(df.itertuples()):
        ax.bar(
            index + i * bar_width, 
            [row.spacy, row.entity, row.emotion, row.location], 
            bar_width, 
            label=row.display_name,
            color=book_colors[i]
        )
    
    # Personalizza il grafico
    ax.set_xlabel('Componente', fontsize=14)
    ax.set_ylabel('Tempo medio (secondi)', fontsize=14)
    ax.set_title('Tempi medi di elaborazione per componente', fontsize=16, fontweight='bold')
    ax.set_xticks(index + bar_width)
    ax.set_xticklabels(component_labels)
    ax.legend()
    
    # Scala logaritmica per meglio visualizzare le differenze
    ax.set_yscale('log')
    
    # Aggiunge etichette con i valori
    for i, row in enumerate(df.itertuples()):
        values = [row.spacy, row.entity, row.emotion, row.location]
        for j, v in enumerate(values):
            ax.text(
                j + i * bar_width,
                v * 1.1,
                f"{v:.2f}s",
                ha='center',
                rotation=90,
                fontsize=9
            )
    
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    # Salva il grafico
    output_file = os.path.join(output_dir, "tempi_elaborazione_componenti.png")
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"Grafico salvato in {output_file}")


# 2. Frequenza dei luoghi/contesti estratti
def generate_locations_frequency_chart():
    print("Generazione grafico frequenza dei luoghi identificati...")
    
    all_locations = {}
    
    for book, display_name in zip(books, book_display_names):
        stats_file = os.path.join(results_dir, book, f"stats-{book}.csv")
        if not os.path.exists(stats_file):
            print(f"File non trovato: {stats_file}")
            continue
            
        with open(stats_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Estrai luoghi principali
        location_pattern = r'Capitolo \d+:[\s\S]+?(\w+(?:\s+\w+)*): ([\d\.]+)'
        locations = re.findall(location_pattern, content)
        
        if not locations:
            print(f"Nessun dato sui luoghi trovato per {book}")
            continue
        
        # Conta la frequenza
        loc_counts = {}
        for loc, score in locations:
            # Filtra luoghi non validi o errori di classificazione
            if loc.lower() in ['natale', 'harry potter', 'scopa'] or len(loc) < 2:
                continue
                
            loc_counts[loc] = loc_counts.get(loc, 0) + 1
        
        # Prendi i 5 luoghi più frequenti
        top_locations = sorted(loc_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        all_locations[display_name] = dict(top_locations)
    
    if not all_locations:
        print("Nessun dato disponibile per generare il grafico")
        return
        
    # Crea grafico a barre
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Posizioni per ogni gruppo di barre
    x_pos = np.arange(len(book_display_names))
    width = 0.15  # Larghezza delle barre
    
    # Per ogni libro
    for i, book in enumerate(book_display_names):
        if book not in all_locations:
            continue
        
        locations = all_locations[book]
        locations_list = list(locations.keys())
        counts = list(locations.values())
        
        # Crea barre per le prime 5 location
        for j in range(min(len(locations_list), 5)):
            ax.bar(
                x_pos[i] + (j - 2) * width,  # Posizionamento centrato
                counts[j],
                width,
                label=f"{locations_list[j]} ({book})" if i == 0 or j == 0 else "_nolegend_",
                color=plt.cm.tab10(j),
                alpha=0.7
            )
            
            # Aggiungi etichette sopra le barre
            ax.text(
                x_pos[i] + (j - 2) * width,
                counts[j] + 0.1,
                locations_list[j],
                ha='center',
                fontsize=8,
                rotation=45
            )
    
    # Personalizza il grafico
    ax.set_ylabel('Frequenza', fontsize=14)
    ax.set_title('Luoghi più frequentemente identificati', fontsize=16, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(book_display_names)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    # Salva il grafico
    output_file = os.path.join(output_dir, "frequenza_luoghi.png")
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"Grafico salvato in {output_file}")


# 3. Carica i dati di valutazione di BERT se disponibili
def generate_bert_performance_chart():
    print("Generazione grafico performance BERT...")
    
    # Percorso diretto al file BERT
    bert_file = r"c:/Users/Maurizio/Desktop/progettotesi/bert_evaluation.json"
    
    if not os.path.exists(bert_file):
        print(f"File di valutazione BERT non trovato: {bert_file}")
        return
        
    try:
        with open(bert_file, 'r', encoding='utf-8') as f:
            bert_data = json.load(f)
            
        # Estrai dati dal classification_report
        if "classification_report" not in bert_data:
            print("Formato dati BERT non valido")
            return
            
        report = bert_data["classification_report"]
        categories = []
        precision = []
        recall = []
        f1 = []
        support = []
        
        # Estrai dati per ogni categoria
        for category, metrics in report.items():
            # Salta voci che non sono categorie
            if category in ["accuracy", "macro avg", "weighted avg"]:
                continue
                
            # Verifica che metrics sia un dizionario prima di accedere
            if isinstance(metrics, dict) and "f1-score" in metrics:
                categories.append(category)
                precision.append(metrics.get("precision", 0))
                recall.append(metrics.get("recall", 0))
                f1.append(metrics.get("f1-score", 0))
                support.append(metrics.get("support", 0))
        
        # Filtra categorie con almeno un esempio
        valid_indices = [i for i, s in enumerate(support) if s > 0]
        categories = [categories[i] for i in valid_indices]
        precision = [precision[i] for i in valid_indices]
        recall = [recall[i] for i in valid_indices]
        f1 = [f1[i] for i in valid_indices]
        
        # Ordina per F1-score
        sorted_indices = np.argsort(f1)[::-1]
        categories = [categories[i] for i in sorted_indices[:10]]  # Top 10
        precision = [precision[i] for i in sorted_indices[:10]]
        recall = [recall[i] for i in sorted_indices[:10]]
        f1 = [f1[i] for i in sorted_indices[:10]]
        
        # Crea grafico
        fig, ax = plt.subplots(figsize=(12, 8))
        
        x = np.arange(len(categories))
        width = 0.25
        
        ax.bar(x - width, precision, width, label='Precisione', color='#3498db')
        ax.bar(x, recall, width, label='Richiamo', color='#2ecc71')
        ax.bar(x + width, f1, width, label='F1-score', color='#e74c3c')
        
        # Personalizza il grafico
        ax.set_xlabel('Categoria', fontsize=14)
        ax.set_ylabel('Punteggio', fontsize=14)
        ax.set_title('Performance di classificazione BERT per categoria', fontsize=16, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend()
        ax.set_ylim(0, 1)
        
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        # Aggiungi l'accuratezza complessiva come testo
        accuracy = bert_data.get("accuracy", 0)
        ax.text(0.98, 0.02, f"Accuratezza complessiva: {accuracy:.2%}", 
                ha='right', va='bottom', transform=ax.transAxes,
                bbox=dict(facecolor='white', alpha=0.8, boxstyle='round'))
        
        # Salva il grafico
        output_file = os.path.join(output_dir, "bert_performance.png")
        plt.savefig(output_file, dpi=300)
        plt.close()
        print(f"Grafico salvato in {output_file}")
        
    except Exception as e:
        print(f"Errore nell'elaborazione del file BERT: {e}")
        import traceback
        traceback.print_exc()
        
# Esegui le funzioni
if __name__ == "__main__":
    generate_processing_time_chart()
    generate_locations_frequency_chart()
    generate_bert_performance_chart()
    print("Generazione grafici completata!")