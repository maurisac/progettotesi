import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import re
import json
from matplotlib.gridspec import GridSpec

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

def generate_synthesis():
    print("Generazione immagine di sintesi dei risultati...")
    
    # Crea una figura con layout personalizzato
    fig = plt.figure(figsize=(20, 12))
    gs = GridSpec(2, 3, figure=fig)
    
    # Titolo principale
    fig.suptitle('Sintesi dei Risultati', fontsize=24, fontweight='bold', y=0.98)
    
    # 1. Performance BERT (alto a sinistra)
    ax1 = fig.add_subplot(gs[0, 0])
    generate_bert_performance(ax1)
    
    # 2. Tempi di elaborazione (alto centro e destra)
    ax2 = fig.add_subplot(gs[0, 1:])
    generate_processing_times(ax2)
    
    # 3. Coerenza contestuale (basso a sinistra)
    ax3 = fig.add_subplot(gs[1, 0])
    generate_coherence_summary(ax3)
    
    # 4. Statistiche token/capitoli (basso centro)
    ax4 = fig.add_subplot(gs[1, 1])
    generate_token_stats(ax4)
    
    # 5. Luoghi identificati (basso a destra)
    ax5 = fig.add_subplot(gs[1, 2])
    generate_location_stats(ax5)
    
    # Aggiungi note informative
    plt.figtext(0.5, 0.01, 
               "Sintesi dei principali risultati dell'analisi automatizzata di contesti narrativi su tre opere letterarie",
               ha="center", fontsize=12, bbox={"facecolor":"white", "alpha":0.5, "boxstyle":"round"})
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    
    # Salva l'immagine
    output_file = os.path.join(output_dir, "sintesi_risultati.png")
    plt.savefig(output_file, dpi=300)
    plt.close()
    print(f"Immagine di sintesi salvata in {output_file}")

def generate_bert_performance(ax):
    """Genera il grafico di performance di BERT"""
    bert_file = os.path.join(results_dir, "bert_evaluation.json")
    
    if not os.path.exists(bert_file):
        ax.set_title("Performance del modello BERT", fontsize=16)
        ax.text(0.5, 0.5, "Dati non disponibili", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return
    
    try:
        with open(bert_file, 'r', encoding='utf-8') as f:
            bert_data = json.load(f)
        
        accuracy = bert_data.get("accuracy", 0) * 100
        
        # Crea un grafico semplice che mostra l'accuratezza
        ax.bar(["Accuratezza BERT"], [accuracy], color="#3498db", width=0.4)
        ax.set_title('Performance del modello BERT', fontsize=16, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.set_ylabel('Percentuale (%)', fontsize=12)
        ax.text(0, accuracy + 2, f"{accuracy:.1f}%", ha='center', fontsize=12, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        # Aggiungi dettagli sulle categorie principali se disponibili
        if "category_metrics" in bert_data:
            metrics = bert_data["category_metrics"]
            top_categories = sorted(metrics.items(), key=lambda x: x[1].get("f1-score", 0), reverse=True)[:5]
            
            y_pos = np.arange(len(top_categories))
            f1_scores = [cat[1].get("f1-score", 0) * 100 for cat in top_categories]
            labels = [cat[0] for cat in top_categories]
            
            ax_inset = ax.inset_axes([0.55, 0.1, 0.4, 0.8])
            ax_inset.barh(y_pos, f1_scores, color='#2ecc71', alpha=0.7)
            ax_inset.set_yticks(y_pos)
            ax_inset.set_yticklabels(labels, fontsize=8)
            ax_inset.set_xlabel('F1-score (%)', fontsize=10)
            ax_inset.set_title('Top 5 Categorie', fontsize=10)
            ax_inset.set_xlim(0, 100)
            ax_inset.grid(axis='x', alpha=0.3)
            
    except Exception as e:
        print(f"Errore nel grafico BERT: {e}")
        ax.set_title("Performance del modello BERT", fontsize=16)
        ax.text(0.5, 0.5, f"Dati parziali: Accuratezza {accuracy:.1f}%", ha='center', va='center', fontsize=12)

def generate_processing_times(ax):
    """Genera il grafico dei tempi di elaborazione"""
    # Dati riassuntivi dei tempi di elaborazione
    data = {}
    
    for book in books:
        stats_file = os.path.join(results_dir, "analyses", book, f"stats-{book}.csv")
        if not os.path.exists(stats_file):
            stats_file = os.path.join(results_dir, "results", book, f"stats-{book}.csv")
            if not os.path.exists(stats_file):
                print(f"File statistiche non trovato per {book}")
                continue
                
        with open(stats_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Estrazione tempi di elaborazione
        times_pattern = r'"Tempi di analisi: Analisi con spaCy: ([\d\.]+)s, Riconoscimento entità con spaCy: ([\d\.]+)s, Analisi emozioni: ([\d\.]+)s, Classificazione delle location: ([\d\.]+)s'
        times_matches = re.findall(times_pattern, content)
        
        if not times_matches:
            continue
            
        # Calcola media per ogni componente
        spacy_avg = np.mean([float(t[0]) for t in times_matches])
        entity_avg = np.mean([float(t[1]) for t in times_matches])
        emotion_avg = np.mean([float(t[2]) for t in times_matches])
        location_avg = np.mean([float(t[3]) for t in times_matches])
        
        data[book_display_names[books.index(book)]] = {
            'spaCy': spacy_avg,
            'Entità': entity_avg,
            'Emozioni': emotion_avg,
            'Luoghi': location_avg
        }
    
    if not data:
        ax.set_title("Tempi di elaborazione per componente", fontsize=16)
        ax.text(0.5, 0.5, "Dati non disponibili", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return
    
    # Crea il DataFrame
    df = pd.DataFrame(data).T
    
    # Plot stacked bars
    df_perc = df.div(df.sum(axis=1), axis=0) * 100
    df.plot(kind='bar', stacked=True, ax=ax, 
           colormap='viridis', rot=0, width=0.7)
    
    # Aggiungi etichette di percentuale
    for c in df.columns:
        for i, (idx, row) in enumerate(df_perc.iterrows()):
            if row[c] > 5:  # Solo se la percentuale è significativa
                ax.text(i, df.loc[idx, :c].sum() - df.loc[idx, c]/2, 
                       f"{row[c]:.0f}%", ha='center', va='center',
                       fontsize=9, color='white', fontweight='bold')
    
    # Aggiungi valori assoluti sopra le barre
    for i, (idx, row) in enumerate(df.iterrows()):
        total = row.sum()
        ax.text(i, total + 1, f"{total:.1f}s", ha='center', fontsize=10)
    
    ax.set_title('Tempi di elaborazione per componente', fontsize=16, fontweight='bold')
    ax.set_ylabel('Tempo (secondi)', fontsize=12)
    ax.legend(title="Componente", loc='upper left', bbox_to_anchor=(1, 1))
    ax.grid(axis='y', alpha=0.3)

def generate_coherence_summary(ax):
    """Genera un sommario sulla coerenza contestuale"""
    # Dati aggregati di coerenza
    coherence_data = {}
    
    for book in books:
        context_file = os.path.join(results_dir, "analyses", book, f"context_metrics-{book}.csv")
        if not os.path.exists(context_file):
            context_file = os.path.join(results_dir, "results", book, f"context_metrics-{book}.csv")
            if not os.path.exists(context_file):
                print(f"File metriche contesto non trovato per {book}")
                continue
                
        try:
            df = pd.read_csv(context_file)
            if df.empty or 'coherence_score' not in df.columns:
                continue
                
            coherence_data[book_display_names[books.index(book)]] = {
                'media': df['coherence_score'].mean(),
                'min': df['coherence_score'].min(),
                'max': df['coherence_score'].max(),
                'location_cont': df['location_continuity'].mean() if 'location_continuity' in df.columns else 0,
                'character_cont': df['character_continuity'].mean() if 'character_continuity' in df.columns else 0
            }
        except Exception as e:
            print(f"Errore nell'elaborazione coerenza per {book}: {e}")
    
    if not coherence_data:
        ax.set_title("Coerenza narrativa tra capitoli", fontsize=16)
        ax.text(0.5, 0.5, "Dati non disponibili", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return
    
    # Crea il grafico
    df_coherence = pd.DataFrame({
        'Media': [d['media'] for d in coherence_data.values()],
        'Min': [d['min'] for d in coherence_data.values()],
        'Max': [d['max'] for d in coherence_data.values()]
    }, index=coherence_data.keys())
    
    df_coherence.plot(kind='bar', ax=ax, rot=0, width=0.7,
                     color=['#2ecc71', '#e74c3c', '#3498db'])
    
    # Aggiungi continuità media di luoghi e personaggi
    for i, book in enumerate(coherence_data.keys()):
        # Aggiungi etichetta di continuità sopra le barre
        loc_cont = coherence_data[book]['location_cont'] * 100
        char_cont = coherence_data[book]['character_cont'] * 100
        
        ax.text(i, 1.05, 
               f"Cont. luoghi: {loc_cont:.0f}%\nCont. personaggi: {char_cont:.0f}%",
               ha='center', fontsize=8, bbox=dict(facecolor='white', alpha=0.7, boxstyle='round'))
    
    ax.set_title('Coerenza narrativa tra capitoli', fontsize=16, fontweight='bold')
    ax.set_ylabel('Punteggio di coerenza', fontsize=12)
    ax.set_ylim(0, 1.3)
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, label='Soglia media')
    ax.legend(loc='upper right')

def generate_token_stats(ax):
    """Genera statistiche sui token e capitoli"""
    # Raccolta statistiche token
    token_stats = {}
    
    for book in books:
        stats_file = os.path.join(results_dir, "analyses", book, f"stats-{book}.csv")
        if not os.path.exists(stats_file):
            stats_file = os.path.join(results_dir, "results", book, f"stats-{book}.csv")
            if not os.path.exists(stats_file):
                print(f"File statistiche non trovato per {book}")
                continue
                
        with open(stats_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Estrai token per capitolo
        tokens = []
        chapters_pattern = r'Capitolo (\d+):\n(\d+) token'
        matches = re.findall(chapters_pattern, content)
        
        if not matches:
            continue
            
        tokens = [int(t) for _, t in matches]
        
        token_stats[book_display_names[books.index(book)]] = {
            'total_tokens': sum(tokens),
            'num_chapters': len(tokens),
            'avg_tokens': np.mean(tokens),
            'min_tokens': np.min(tokens),
            'max_tokens': np.max(tokens)
        }
    
    if not token_stats:
        ax.set_title("Statistiche token/capitoli", fontsize=16)
        ax.text(0.5, 0.5, "Dati non disponibili", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return
    
    # Crea le barre principali per token totali
    bars = ax.bar(token_stats.keys(), 
                [stats['total_tokens'] for stats in token_stats.values()],
                color=[book_colors[i] for i in range(len(token_stats))])
    
    # Personalizza il grafico
    ax.set_title('Statistiche token/capitoli', fontsize=16, fontweight='bold')
    ax.set_ylabel('Numero totale token', fontsize=12)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    # Aggiungi etichette con numero capitoli
    for i, (book, stats) in enumerate(token_stats.items()):
        ax.text(i, stats['total_tokens'] + stats['total_tokens']*0.03, 
               f"{stats['num_chapters']} capitoli",
               ha='center', va='bottom', fontsize=10)
        
        # Aggiungi min/max/avg in una tabella sotto la barra
        info_text = f"Min: {stats['min_tokens']:.0f}\n" \
                   f"Media: {stats['avg_tokens']:.0f}\n" \
                   f"Max: {stats['max_tokens']:.0f}"
                   
        ax.text(i, -stats['total_tokens']*0.1, 
               info_text, ha='center', va='top', fontsize=9,
               bbox=dict(facecolor='white', alpha=0.7, boxstyle='round'))

def generate_location_stats(ax):
    """Genera statistiche sui luoghi identificati"""
    # Raccolta statistiche luoghi
    location_stats = {}
    
    for book in books:
        stats_file = os.path.join(results_dir, "analyses", book, f"stats-{book}.csv")
        if not os.path.exists(stats_file):
            stats_file = os.path.join(results_dir, "results", book, f"stats-{book}.csv")
            if not os.path.exists(stats_file):
                print(f"File statistiche non trovato per {book}")
                continue
                
        with open(stats_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Estrai luoghi principali
        locations = {}
        location_pattern = r'Capitolo \d+:[\s\S]+?(\w+(?:\s+\w+)*): ([\d\.]+)'
        loc_matches = re.findall(location_pattern, content)
        
        for loc, score in loc_matches:
            # Filtra luoghi non validi o errori di classificazione
            if loc.lower() in ['natale', 'harry potter', 'scopa'] or len(loc) < 2:
                continue
                
            locations[loc] = locations.get(loc, 0) + 1
        
        # Prendi i 5 luoghi più frequenti
        top_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]
        
        location_stats[book_display_names[books.index(book)]] = {
            'unique_locations': len(locations),
            'top_locations': dict(top_locations)
        }
    
    if not location_stats:
        ax.set_title("Luoghi identificati", fontsize=16)
        ax.text(0.5, 0.5, "Dati non disponibili", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return
    
    # Crea un grafico a barre per luoghi unici
    ax.bar(location_stats.keys(), 
          [stats['unique_locations'] for stats in location_stats.values()],
          color=[book_colors[i] for i in range(len(location_stats))],
          alpha=0.7)
    
    # Personalizza il grafico
    ax.set_title('Luoghi identificati', fontsize=16, fontweight='bold')
    ax.set_ylabel('Numero di luoghi unici', fontsize=12)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    # Aggiungi etichette con i luoghi principali
    for i, (book, stats) in enumerate(location_stats.items()):
        if stats['top_locations']:
            # Crea una stringa con i primi 3 luoghi
            top_locs = list(stats['top_locations'].items())[:3]
            loc_text = "\n".join([f"{loc}: {count}" for loc, count in top_locs])
            
            ax.text(i, stats['unique_locations'] * 0.5, 
                   f"Top luoghi:\n{loc_text}",
                   ha='center', va='center', fontsize=9,
                   bbox=dict(facecolor='white', alpha=0.8, boxstyle='round'))

if __name__ == "__main__":
    generate_synthesis()
    print("Generazione immagine di sintesi completata!")