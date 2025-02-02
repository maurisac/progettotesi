import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, Menu, ttk
import fitz  # PyMuPDF per PDF
import docx  # python-docx per Word
import configparser  # Per salvare le impostazioni
import os
import logging
import csv
import pandas as pd  # Per leggere i file CSV
import subprocess


# Configurazione logging
LOG_FILE = "error.log"
logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurazione iniziale
PAGE_SIZE = 3300
text_pages = []
current_page = 0
current_file = None
profile_file = "profile.ini"
analysis_data = {}
book_name = ""

# Lettura delle impostazioni salvate
config = configparser.ConfigParser()
if os.path.exists(profile_file):
    config.read(profile_file)
else:
    config["Settings"] = {"font_size": "16", "window_width": "1920", "window_height": "1080", "last_file": "", "last_page": "0"}

# Impostazioni iniziali
default_font_size = int(config["Settings"].get("font_size", "16"))
window_width = int(config["Settings"].get("window_width", "1920"))
window_height = int(config["Settings"].get("window_height", "1080"))
last_file = config["Settings"].get("last_file", "")
last_page = int(config["Settings"].get("last_page", "0"))


def save_settings():
    # Salva le impostazioni nel file profile.ini.
    config["Settings"]["font_size"] = str(text_area["font"].split()[1])
    config["Settings"]["window_width"] = str(root.winfo_width())
    config["Settings"]["window_height"] = str(root.winfo_height())
    config["Settings"]["last_file"] = current_file if current_file else ""
    config["Settings"]["last_page"] = str(current_page)
    
    with open(profile_file, "w") as file:
        config.write(file)


def open_file(filepath=None):
    # Apre un file TXT, PDF o DOCX, lo divide in pagine e mostra la prima pagina.
    global text_pages, current_page, current_file, analysis_data, book_name
    try:
        if not filepath:
            filepath = filedialog.askopenfilename(filetypes=[
                ("PDF Files", "*.pdf"),
                ("Text Files", "*.txt"),
                ("Word Documents", "*.docx")
            ])
            
        if not filepath:
            return
        
        current_file = filepath
        book_name, _ = os.path.splitext(os.path.basename(filepath))
        
        root.title(f"Book Analyzer - {book_name}")

        if filepath.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as file:
                text = file.read()
        elif filepath.endswith(".pdf"):
            text = extract_text_from_pdf(filepath)
        elif filepath.endswith(".docx"):
            text = extract_text_from_docx(filepath)
        else:
            text = "Formato non supportato."

        # Dividi il testo in pagine
        text_pages = [text[i:i + PAGE_SIZE] for i in range(0, len(text), PAGE_SIZE)]
        current_page = 0

        analysis_file = os.path.join(os.path.dirname(filepath), f"{book_name}-analysis.csv")
        
        # Carica le analisi (aggiungi questa chiamata)
        load_analysis_data(analysis_file)
        
        show_page()
    except Exception as e:
        logging.error(str(e))
        messagebox.showerror("Errore", f"Errore: {str(e)}")

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text() for page in doc])

def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])

def run_analysis():
    if not current_file:
        messagebox.showwarning("Attenzione", "Apri prima un file da analizzare.")
        return
    
    progress_bar.start(10)  # Avvia la barra di avanzamento
    try:
        subprocess.run(["python", "analysis.py", current_file], check=True)
        messagebox.showinfo("Successo", "Analisi completata!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Errore", f"Errore durante l'analisi: {e}")
    finally:
        progress_bar.stop()  # Ferma la barra di avanzamento


def load_analysis_data(filepath):
    global analysis_data
    analysis_data = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            
            # Salta la prima riga (legenda)
            next(reader)
            
            for row in reader:
                if len(row) >= 3:
                    try:
                        chapter = row[0]
                        pages_range = row[1]  # Pagine in formato "start-end"
                        results = row[2]
                        
                        # Estrai l'inizio e la fine dell'intervallo di pagine, assicurandoti che siano numeri
                        start_page, end_page = map(int, pages_range.split('-'))
                        # Aggiungi ogni pagina nell'intervallo al dizionario
                        for page in range(start_page, end_page + 1):
                            analysis_data[page] = (chapter, results)
                            print(f"Added analysis for page {page}: {chapter} - {results}")
                    except ValueError as e:
                        print(f"Errore nella conversione della pagina di inizio o fine: {row[1]} - {e}")



def update_analysis_display():
    analysis_text.config(state=tk.NORMAL)
    analysis_text.delete("1.0", tk.END)
    for start_page in sorted(analysis_data.keys(), reverse=True):
        if current_page + 1 >= start_page:
            chapter, results = analysis_data[start_page]
            analysis_text.insert(tk.END, f"{chapter}\n{results}")
            break
    analysis_text.config(state=tk.DISABLED)

def show_page():
    global book_name, analysis_data
    # Mostra la pagina corrente.
    if text_pages:
        text_area.config(state=tk.NORMAL)
        text_area.delete("1.0", tk.END)
        text_area.insert(tk.END, text_pages[current_page])
        text_area.config(state=tk.DISABLED)
        page_label.config(text=f"Pagina {current_page + 1} di {len(text_pages)}")
        if analysis_data is not None:
            update_analysis_display()
        else:
            analysis_text.config(state=tk.NORMAL)
            analysis_text.delete("1.0", tk.END)
            analysis_text.insert(tk.END, f"Analisi non trovata per {book_name}")
        save_settings()

def next_page(event=None):
    # Mostra la pagina successiva.
    global current_page
    if current_page < len(text_pages) - 1:
        current_page += 1
        show_page()

def prev_page(event=None):
    # Mostra la pagina precedente.
    global current_page
    if current_page > 0:
        current_page -= 1
        show_page()


def increase_font(event=None):
    # Aumenta la dimensione del testo e della pagina interna.
    size = int(text_area["font"].split()[1]) + 2
    text_area.config(font=("Arial", size))
    text_area.pack_configure(expand=True, fill='both')
    save_settings()


def decrease_font(event=None):
    # Diminuisce la dimensione del testo e della pagina interna.
    size = max(8, int(text_area["font"].split()[1]) - 2)
    text_area.config(font=("Arial", size))
    text_area.pack_configure(expand=True, fill='both')
    save_settings()

def show_contacts():
    # Mostra la finestra con i contatti e i crediti.
    messagebox.showinfo("Contatti", "Sviluppato da Sacca' Maurizio\nEmail: mauriziosacc4@gmail.com")



# Creazione GUI
root = tk.Tk()
root.title("Caricamento Libro a Pagine")
root.geometry(f"{window_width}x{window_height}")
root.state('zoomed')

# Menu principale
menu_bar = Menu(root)

# sezione file
file_menu = Menu(menu_bar, tearoff=0)
file_menu.add_command(label="Apri File", command=open_file)
file_menu.add_separator()
file_menu.add_command(label="Esci", command=root.quit)
menu_bar.add_cascade(label="File", menu=file_menu)

# sezione impostazioni
settings_menu = Menu(menu_bar, tearoff=0)
settings_menu.add_command(label="Aumenta Zoom: ctrl + ", command=increase_font)
settings_menu.add_command(label="Diminuisci Zoom: ctrl - ", command=decrease_font)
settings_menu.add_separator()
settings_menu.add_command(label="Pagina Successiva: Freccia Destra → ", command=next_page)
settings_menu.add_command(label="Pagina precedente: Freccia Sinistra ← ", command=prev_page)
menu_bar.add_cascade(label="Impostazioni", menu=settings_menu)

# sezione contatti
contacts_menu = Menu(menu_bar, tearoff=0)
contacts_menu.add_command(label="Contatti", command=show_contacts)
menu_bar.add_cascade(label="Contatti", menu=contacts_menu)

root.config(menu=menu_bar)

nav_frame = tk.Frame(root)
nav_frame.pack(fill='x')

# Frame per i pulsanti di navigazione (centrali)
nav_buttons_frame = tk.Frame(nav_frame)
nav_buttons_frame.pack(side=tk.LEFT, expand=True)

tk.Button(nav_buttons_frame, text="← Pagina Precedente", command=prev_page).pack(side=tk.LEFT, padx=5)

page_label = tk.Label(nav_buttons_frame, text="Pagina 1 di 1")
page_label.pack(side=tk.LEFT, padx=10)

tk.Button(nav_buttons_frame, text="Pagina Successiva →", command=next_page).pack(side=tk.LEFT, padx=5)


# Frame per la barra di avanzamento e il pulsante di analisi (destra)
analysis_frame = tk.Frame(nav_frame)
analysis_frame.pack(side=tk.RIGHT, padx=10)

progress_bar = ttk.Progressbar(analysis_frame, mode='indeterminate')
progress_bar.pack(side=tk.RIGHT, padx=5)

analyze_button = tk.Button(analysis_frame, text="Avvia Analisi", command=run_analysis)
analyze_button.pack(side=tk.RIGHT, padx=5)


# Bind per lo zoom con tastiera
root.bind("<Control-plus>", increase_font)
root.bind("<Control-minus>", decrease_font)

# Bind per il cambio pagina con le freccette
root.bind("<Right>", next_page)
root.bind("<Left>", prev_page)

main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True)

text_area = scrolledtext.ScrolledText(main_frame, width=60, height=20, state=tk.DISABLED, font=("Arial", default_font_size))
text_area.pack(side=tk.LEFT, expand=True, fill='both', padx=10, pady=10)

analysis_text = scrolledtext.ScrolledText(main_frame, width=30, height=20, state=tk.DISABLED, font=("Arial", default_font_size))
analysis_text.pack(side=tk.RIGHT, expand=True, fill='both', padx=10, pady=10)


# Ripristina ultimo file e pagina
if last_file and os.path.exists(last_file):
    open_file(last_file)
    current_page = min(last_page, len(text_pages) - 1)
    show_page()



root.protocol("WM_DELETE_WINDOW", lambda: (save_settings(), root.destroy()))
root.mainloop()
