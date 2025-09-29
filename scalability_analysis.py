import matplotlib.pyplot as plt
import pandas as pd
import re
import os
import numpy as np
from matplotlib.lines import Line2D

# Funzione per estrarre dati dai file CSV
def extract_data(csv_path):
    with open(csv_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Estrazione dei dati per ogni capitolo
    chapter_pattern = r'Capitolo (\d+):\n(\d+) token - \d+ pagine\n"Tempi di analisi:.*?Tempo totale: (\d+\.\d+)s"'
    chapters = re.findall(chapter_pattern, content)
    
    # Conversione in DataFrame
    data = []
    for chapter, tokens, time in chapters:
        data.append({
            'chapter': int(chapter),
            'tokens': int(tokens),
            'time': float(time)
        })
    
    return pd.DataFrame(data)

# Percorsi dei file CSV
results_dir = r"c:/Users/Maurizio/Desktop/progettotesi/results"
hp_path = os.path.join(results_dir, "Harry Potter E la Pietra Filosofale (J. K. Rowling)/stats-Harry Potter E la Pietra Filosofale (J. K. Rowling).csv")
narnia_path = os.path.join(results_dir, "Le Cronache Di Narnia. Il Leone La Strega e L’armadio (Lewis, C.S.)/stats-Le Cronache Di Narnia. Il Leone La Strega e L’armadio (Lewis, C.S.).csv")
wheel_path = os.path.join(results_dir, "L’occhio del mondo (Jordan Robert)/stats-L’occhio del mondo (Jordan Robert).csv")

# Estrazione dati
hp_data = extract_data(hp_path)
narnia_data = extract_data(narnia_path)
wheel_data = extract_data(wheel_path)

# Capitoli selezionati per l'analisi
hp_selected = [3, 12, 17]
narnia_selected = [3, 9, 12]
wheel_selected = [3, 21, 43]

# Configurazione del grafico
plt.figure(figsize=(12, 8))

# Plot di tutti i dati con trasparenza
plt.scatter(hp_data['tokens'], hp_data['time'], color='red', alpha=0.3, label='Harry Potter')
plt.scatter(narnia_data['tokens'], narnia_data['time'], color='blue', alpha=0.3, label='Narnia')
plt.scatter(wheel_data['tokens'], wheel_data['time'], color='green', alpha=0.3, label='Ruota del Tempo')

# Evidenzia i capitoli selezionati
hp_selected_data = hp_data[hp_data['chapter'].isin(hp_selected)]
narnia_selected_data = narnia_data[narnia_data['chapter'].isin(narnia_selected)]
wheel_selected_data = wheel_data[wheel_data['chapter'].isin(wheel_selected)]

# Aggiungi etichette per i capitoli selezionati
for _, row in hp_selected_data.iterrows():
    plt.annotate(f"HP Cap.{int(row['chapter'])}", 
                (row['tokens'], row['time']),
                xytext=(10, 5), textcoords='offset points',
                color='darkred', fontweight='bold')
    plt.scatter(row['tokens'], row['time'], color='red', s=100, edgecolor='black', zorder=5)

for _, row in narnia_selected_data.iterrows():
    plt.annotate(f"Narnia Cap.{int(row['chapter'])}", 
                (row['tokens'], row['time']),
                xytext=(10, 5), textcoords='offset points',
                color='darkblue', fontweight='bold')
    plt.scatter(row['tokens'], row['time'], color='blue', s=100, edgecolor='black', zorder=5)

for _, row in wheel_selected_data.iterrows():
    plt.annotate(f"RT Cap.{int(row['chapter'])}", 
                (row['tokens'], row['time']),
                xytext=(10, 5), textcoords='offset points',
                color='darkgreen', fontweight='bold')
    plt.scatter(row['tokens'], row['time'], color='green', s=100, edgecolor='black', zorder=5)

# Aggiungi linee di regressione per vedere la tendenza
def add_trendline(x, y, color):
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    plt.plot(x, p(x), color=color, linestyle='--', alpha=0.7)

add_trendline(hp_data['tokens'], hp_data['time'], 'red')
add_trendline(narnia_data['tokens'], narnia_data['time'], 'blue')
add_trendline(wheel_data['tokens'], wheel_data['time'], 'green')

# Configurazione degli assi e delle etichette
plt.xlabel('Numero di Token', fontsize=14)
plt.ylabel('Tempo di Elaborazione (secondi)', fontsize=14)
plt.title('Relazione tra Numero di Token e Tempo di Elaborazione', fontsize=16)
plt.grid(True, linestyle='--', alpha=0.7)

# Crea una legenda personalizzata
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='Harry Potter'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='Narnia'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='Ruota del Tempo'),
    Line2D([0], [0], linestyle='--', color='black', label='Linea di tendenza')
]

# Aggiungi la legenda
plt.legend(handles=legend_elements, loc='upper left')

# Salva il grafico
output_path = os.path.join(results_dir, 'token_vs_time_comparison.png')
plt.tight_layout()
plt.savefig(output_path, dpi=300)
plt.show()

print(f"Grafico salvato in: {output_path}")