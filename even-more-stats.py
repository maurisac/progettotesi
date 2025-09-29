import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import re
import json
import seaborn as sns
from sklearn.metrics import confusion_matrix
import networkx as nx
import glob

# Directory base
results_dir = r"c:/Users/Maurizio/Desktop/progettotesi"
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

# 1. Grafico token vs tempo (combinato)
def generate_combined_token_time():
    print("Generazione grafico token vs tempo combinato...")
    
    plt.figure(figsize=(12, 8))
    
    # Cerca i file CSV per ciascun libro
    for i, book in enumerate(books):
        stats_file = os.path.join(results_dir, "analyses", book, f"stats-{book}.csv")
        if not os.path.exists(stats_file):
            # Prova il percorso alternativo
            stats_file = os.path.join(results_dir, "results", book, f"stats-{book}.csv")
            if not os.path.exists(stats_file):
                print(f"File statistiche non trovato per {book}")
                continue
        
        # Estrai dati token e tempi
        tokens = []
        times = []
        
        with open(stats_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Estrai i dati usando regex
        pattern = r'Capitolo \d+:\n(\d+) token.*?Tempo totale: (\d+\.\d+)s'
        matches = re.findall(pattern, content)
        
        if not matches:
            print(f"Nessun dato trovato per {book}")
            continue
        
        for token_str, time_str in matches:
            tokens.append(int(token_str))
            times.append(float(time_str))
        
        # Crea scatter plot
        plt.scatter(tokens, times, label=book_display_names[i], color=book_colors[i], alpha=0.7, s=50)
        
        # Aggiungi linea di tendenza
        z = np.polyfit(tokens, times, 1)
        p = np.poly1d(z)
        plt.plot(tokens, p(tokens), color=book_colors[i], linestyle='--', alpha=0.7)
    
    # Personalizza il grafico
    plt.title('Relazione tra numero di token e tempo di elaborazione', fontsize=16, fontweight='bold')
    plt.xlabel('Numero di token', fontsize=14)
    plt.ylabel('Tempo di elaborazione (secondi)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    
    # Salva il grafico
    output_file = os.path.join(output_dir, "token_vs_time_combined.png")
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"Grafico salvato in {output_file}")

# 2. Matrice di confusione per BERT (combinata)
def generate_bert_confusion_matrix():
    print("Generazione matrice di confusione BERT...")
    
    # Trova il file di valutazione BERT
    bert_file = os.path.join(results_dir, "bert_evaluation.json")
    
    if not os.path.exists(bert_file):
        print(f"File valutazione BERT non trovato: {bert_file}")
        return
    
    try:
        with open(bert_file, 'r', encoding='utf-8') as f:
            bert_data = json.load(f)
        
        if "confusion_matrix" not in bert_data:
            print("Dati della matrice di confusione non trovati")
            return
        
        # Estrai matrice e etichette
        conf_matrix = np.array(bert_data["confusion_matrix"])
        labels = bert_data.get("labels", [])
        
        if len(labels) == 0:
            # Se non ci sono etichette, usa indici numerici
            labels = [str(i) for i in range(conf_matrix.shape[0])]
        
        # Seleziona le categorie principali (top 10 con più esempi)
        if conf_matrix.shape[0] > 10:
            totals = conf_matrix.sum(axis=1)
            top_indices = np.argsort(totals)[::-1][:10]
            conf_matrix = conf_matrix[top_indices][:, top_indices]
            labels = [labels[i] for i in top_indices]
        
        # Normalizza la matrice
        conf_matrix_norm = conf_matrix.astype('float') / conf_matrix.sum(axis=1)[:, np.newaxis]
        
        # Crea il grafico
        plt.figure(figsize=(14, 12))
        
        sns.heatmap(conf_matrix_norm, annot=True, fmt='.2f', cmap='YlGnBu',
                   xticklabels=labels, yticklabels=labels, cbar=True)
        
        plt.title('Matrice di confusione normalizzata per classificazione BERT', fontsize=16, fontweight='bold')
        plt.xlabel('Predetto', fontsize=14)
        plt.ylabel('Reale', fontsize=14)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        # Salva il grafico
        output_file = os.path.join(output_dir, "bert_confusion_matrix.png")
        plt.savefig(output_file, dpi=300)
        plt.close()
        print(f"Grafico salvato in {output_file}")
        
    except Exception as e:
        print(f"Errore nell'elaborazione della matrice di confusione: {e}")

# 3. Grafico combinato di coerenza contestuale
def generate_combined_coherence():
    print("Generazione grafico coerenza contestuale combinato...")
    
    plt.figure(figsize=(12, 8))
    at_least_one_found = False
    legend_handles = []  # Per raccogliere gli elementi della leggenda
    
    for i, book in enumerate(books):
        # Cerca i file di metriche di contesto
        context_file = os.path.join(results_dir, "analyses", book, f"context_metrics-{book}.csv")
        
        if not os.path.exists(context_file):
            # Prova il percorso alternativo
            context_file = os.path.join(results_dir, "results", book, f"context_metrics-{book}.csv")
            if not os.path.exists(context_file):
                # Cerca files con pattern simile
                pattern = os.path.join(results_dir, "**", f"*context*{book.split(' ')[0]}*.csv")
                files = glob.glob(pattern, recursive=True)
                if not files:
                    print(f"File metriche contesto non trovato per {book}")
                    continue
                context_file = files[0]
        
        try:
            # Leggi il file CSV
            df = pd.read_csv(context_file)
            
            # Se il file è vuoto o il formato non è quello atteso
            if df.empty or 'coherence_score' not in df.columns:
                print(f"Formato non valido per {book}")
                continue
            
            # Crea il grafico
            if 'prev_chapter' in df.columns and 'curr_chapter' in df.columns:
                # Calcola la posizione intermedia per ogni transizione
                mid_x = (df['prev_chapter'] + df['curr_chapter']) / 2
                
                # Disegna le linee per ogni transizione
                for j, row in df.iterrows():
                    plt.plot([row['prev_chapter'], row['curr_chapter']], 
                             [row['coherence_score'], row['coherence_score']],
                             color=book_colors[i], alpha=0.6)
                
                # Disegna i punti per i punteggi di coerenza e aggiungi alla leggenda una sola volta
                scatter = plt.scatter(mid_x, df['coherence_score'], 
                                     color=book_colors[i], s=50, alpha=0.8)
                
                if not any(h.get_label() == book_display_names[i] for h in legend_handles):
                    # Aggiungi solo se non esiste già
                    legend_handles.append(plt.Line2D([0], [0], marker='o', color=book_colors[i], 
                                                   label=book_display_names[i],
                                                   markersize=8, linestyle='', alpha=0.8))
                
                # Aggiungi etichette con i capitoli
                for j, row in df.iterrows():
                    plt.text(mid_x.iloc[j], row['coherence_score'] + 0.03,
                           f"{row['prev_chapter']}→{row['curr_chapter']}",
                           ha='center', fontsize=8, color=book_colors[i])
                
                at_least_one_found = True
        except Exception as e:
            print(f"Errore nell'elaborazione del file {context_file}: {e}")
    
    # Aggiungi linea tratteggiata alla leggenda
    legend_handles.append(plt.Line2D([0], [0], color='red', linestyle='--', alpha=0.5, 
                                    label='Soglia media'))
    
    # Personalizza il grafico
    plt.title('Coerenza contestuale tra capitoli', fontsize=16, fontweight='bold')
    plt.xlabel('Capitolo', fontsize=14)
    plt.ylabel('Punteggio di coerenza', fontsize=14)
    plt.ylim(0, 1.1)
    plt.axhline(y=0.5, color='red', linestyle='--', alpha=0.5)
    plt.grid(True, alpha=0.3)
    
    # Aggiungi la leggenda usando gli handle raccolti
    if at_least_one_found:
        plt.legend(handles=legend_handles, loc='upper right')
    
    plt.tight_layout()
    
    # Salva il grafico
    output_file = os.path.join(output_dir, "coerenza_contestuale_combinato.png")
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"Grafico salvato in {output_file}")

# 4. Grafico combinato transizioni luoghi
def generate_combined_location_transitions():
    print("Generazione grafico combinato transizioni luoghi...")
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    for i, book in enumerate(books):
        # Cerca i file con le transizioni di luoghi
        network_files = glob.glob(os.path.join(results_dir, "**", f"*{book.split(' ')[0]}*transizioni_luoghi.png"), recursive=True)
        
        if not network_files:
            print(f"File transizioni luoghi non trovato per {book}")
            # Crea un grafico vuoto
            axes[i].set_title(f"{book_display_names[i]}\n(Dati non disponibili)")
            axes[i].axis('off')
            continue
        
        # Crea un nuovo grafo semplificato per la presentazione
        try:
            # Carica i dati
            context_file = os.path.join(results_dir, "analyses", book, f"context_metrics-{book}.csv")
            
            if not os.path.exists(context_file):
                # Prova il percorso alternativo
                context_file = os.path.join(results_dir, "results", book, f"context_metrics-{book}.csv")
                
            if not os.path.exists(context_file):
                print(f"File metriche contesto non trovato per {book}")
                # Usa l'immagine esistente invece
                img = plt.imread(network_files[0])
                axes[i].imshow(img)
                axes[i].set_title(f"Transizioni luoghi - {book_display_names[i]}")
                axes[i].axis('off')
                continue
            
            # Cerca il file di statistiche per ottenere i luoghi principali
            stats_file = os.path.join(results_dir, "analyses", book, f"stats-{book}.csv")
            if not os.path.exists(stats_file):
                stats_file = os.path.join(results_dir, "results", book, f"stats-{book}.csv")
                if not os.path.exists(stats_file):
                    print(f"File statistiche non trovato per {book}")
                    continue
            
            # Estrai i luoghi principali dai file di statistiche
            locations = {}
            with open(stats_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Estrai luoghi principali
            location_pattern = r'Capitolo (\d+):\n\d+ token.*?\n.*?\n([\w\s]+): ([\d\.]+)'
            loc_matches = re.findall(location_pattern, content)
            
            for chapter, loc, score in loc_matches:
                if loc and loc != "Nessun luogo alternativo trovato":
                    locations[chapter] = loc
            
            # Crea il grafo di transizioni
            G = nx.DiGraph()
            prev_loc = None
            prev_chapter = None
            
            # Ordina i capitoli per numero
            sorted_chapters = sorted(locations.keys(), key=lambda x: int(x) if x.isdigit() else 0)
            
            for chapter in sorted_chapters:
                curr_loc = locations.get(chapter)
                if curr_loc and prev_loc and curr_loc != prev_loc:
                    if not G.has_node(prev_loc):
                        G.add_node(prev_loc)
                    if not G.has_node(curr_loc):
                        G.add_node(curr_loc)
                    
                    if G.has_edge(prev_loc, curr_loc):
                        G[prev_loc][curr_loc]['weight'] += 1
                    else:
                        G.add_edge(prev_loc, curr_loc, weight=1)
                
                prev_loc = curr_loc
                prev_chapter = chapter
            
            # Disegna il grafo
            if G.nodes():
                pos = nx.spring_layout(G, seed=42)
                
                # Calcola la dimensione dei nodi in base alla frequenza
                node_sizes = {}
                for loc in G.nodes():
                    count = sum(1 for chapter, l in locations.items() if l == loc)
                    node_sizes[loc] = max(300, count * 100)
                
                # Disegna i nodi
                nx.draw_networkx_nodes(G, pos, 
                                     ax=axes[i],
                                     node_size=[node_sizes[n] for n in G.nodes()],
                                     node_color=book_colors[i],
                                     alpha=0.7)
                
                # Disegna gli archi
                edges = G.edges()
                weights = [G[u][v]['weight'] for u, v in edges]
                nx.draw_networkx_edges(G, pos,
                                     ax=axes[i],
                                     width=[w * 0.5 for w in weights],
                                     alpha=0.7,
                                     edge_color='gray',
                                     arrows=True,
                                     arrowsize=15)
                
                # Disegna le etichette
                nx.draw_networkx_labels(G, pos,
                                      ax=axes[i],
                                      font_size=9,
                                      font_weight='bold')
            
            axes[i].set_title(f"Transizioni luoghi - {book_display_names[i]}", fontsize=14)
            axes[i].axis('off')
            
        except Exception as e:
            print(f"Errore nella generazione del grafo per {book}: {e}")
            if network_files:
                # Usa l'immagine esistente
                img = plt.imread(network_files[0])
                axes[i].imshow(img)
                axes[i].set_title(f"Transizioni luoghi - {book_display_names[i]}")
                axes[i].axis('off')
    
    plt.tight_layout()
    
    # Salva il grafico
    output_file = os.path.join(output_dir, "transizioni_luoghi_combinato.png")
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"Grafico salvato in {output_file}")

# Esegui le funzioni
if __name__ == "__main__":
    generate_combined_token_time()
    generate_bert_confusion_matrix()
    generate_combined_coherence()
    generate_combined_location_transitions()
    print("Generazione grafici combinati completata!")