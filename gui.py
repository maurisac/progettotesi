import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, Menu, ttk, simpledialog
import fitz  # PyMuPDF for PDF
import docx  # python-docx for Word
import configparser  # Per salvare le impostazioni
import os
import logging
import csv
import pandas as pd  # Per leggere i file CSV
import subprocess
from collections import Counter
import threading
import ast
import signal
import psutil
import threading
from sound_controller import SoundController
import pygame


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
analysis_process = None
analysis_running = False
sound_controller = None

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
    global text_pages, current_page, current_file, analysis_data, book_name, sound_controller
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

        # Modifica il percorso del file di analisi per cercarlo nella cartella "analyses"
        analysis_file = os.path.join("analyses", book_name, f"{book_name}-analysis.csv")
        
        # Carica le analisi
        load_analysis_data(analysis_file)
        
        show_page()

        # Inizializza il controller audio se non esiste già
        if not sound_controller:
            pygame.init()
            sound_controller = SoundController()
            sound_controller.start()
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
    global analysis_process, analysis_running
    
    if current_file:
        progress_bar.start()
        analysis_running = True
        stop_button.config(state=tk.NORMAL)
        
        def analyze():
            global analysis_process
            
            analysis_process = subprocess.Popen(
                ["python", "analysis.py", current_file],  # Cambiare "python" con "python3" su Linux
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Cattura l'output del processo
            stdout, stderr = analysis_process.communicate()

            # Stampa l'output nel terminale della GUI
            print(stdout)
            if stderr:
                print(stderr)

            status_code = analysis_process.returncode
            
            global analysis_running
            analysis_running = False
            progress_bar.stop()
            stop_button.config(state=tk.DISABLED)

            analysis_text.config(state=tk.NORMAL)
            analysis_text.delete("1.0", tk.END)

            match status_code:
                case 0:
                    messagebox.showinfo("Successo", f"Analisi completata. Riepilogo salvato nel file {book_name}-analysis.csv")
                case 10:
                    messagebox.showerror("Errore", "Errore: specificare il file da analizzare.")
                case 11:
                    messagebox.showerror("Errore", "Errore: file non trovato.")
                case _:
                    messagebox.showerror("Errore", f"Codice di errore sconosciuto: {status_code}")
                
            analysis_text.config(state=tk.DISABLED)
            load_analysis_data(os.path.join("analyses", book_name, f"{book_name}-analysis.csv"))  # Ricarica i dati di analisi

        # Esegui l'analisi in un thread separato
        analysis_thread = threading.Thread(target=analyze)
        analysis_thread.daemon = True
        analysis_thread.start()

def stop_analysis():
    global analysis_process, analysis_running
    
    if not analysis_running or not analysis_process:
        messagebox.showinfo("Info", "Nessuna analisi in corso.")
        return
    
    try:
        # Termina il processo principale
        parent_pid = analysis_process.pid
        parent = psutil.Process(parent_pid)
        
        # Termina prima tutti i processi figli
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except:
                pass
        
        # Termina il processo padre
        analysis_process.terminate()
        
        # Aggiorna l'interfaccia
        progress_bar.stop()
        analysis_running = False
        stop_button.config(state=tk.DISABLED)
        
        messagebox.showinfo("Info", "Analisi interrotta.")
    except Exception as e:
        messagebox.showerror("Errore", f"Impossibile interrompere l'analisi: {str(e)}")

def load_analysis_data(filepath):
    global analysis_data
    analysis_data = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            
            # Salta la prima riga (legenda)
            next(reader)
            
            for row in reader:
                if len(row) >= 2:
                    try:
                        chapter = row[0]
                        pages_range = row[1]  # Pagine in formato "start-end"
                        
                        # Estrai l'inizio e la fine dell'intervallo di pagine, assicurandoti che siano numeri
                        start_page, end_page = map(int, pages_range.split('-'))
                        # Aggiungi ogni pagina nell'intervallo al dizionario
                        for page in range(start_page, end_page + 1):
                            analysis_data[page] = chapter
                    except ValueError as e:
                        print(f"Errore nella conversione della pagina di inizio o fine: {row[1]} - {e}")
    else:
        print(f"File di analisi non trovato: {filepath}")  # Debug
    update_chapters_display()  # Aggiorna la visualizzazione dei capitoli

def update_analysis_display():
    """Legge i dati grezzi dal CSV e li formatta per la visualizzazione"""
    analysis_text.config(state=tk.NORMAL)
    analysis_text.delete("1.0", tk.END)
    
    # Trova il capitolo corrente
    current_chapter = None
    for start_page in sorted(analysis_data.keys(), reverse=True):
        if current_page + 1 >= start_page:
            current_chapter = analysis_data[start_page]
            break
            
    if not current_chapter:
        analysis_text.insert(tk.END, "Nessun capitolo trovato per questa pagina.")
        analysis_text.config(state=tk.DISABLED)
        return
    
    analysis_text.insert(tk.END, f"Capitolo {current_chapter}\n\n")
    
    # Leggi il contenuto del file di analisi del capitolo corrente
    analysis_file = os.path.join("analyses", book_name, f"{book_name}-capitolo{current_chapter}-analysis.csv")
    
    if not os.path.exists(analysis_file):
        analysis_text.insert(tk.END, "Analisi non trovata.")
        analysis_text.config(state=tk.DISABLED)
        return
    
    # Carica i dati dal file CSV
    raw_data = {}
    with open(analysis_file, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) >= 2:
                raw_data[row[0]] = row[1]
    
    # Verifica lo stato dell'analisi
    if "Stato" in raw_data and "completata" not in raw_data["Stato"]:
        analysis_text.insert(tk.END, "Analisi in corso o incompleta.\n")
        analysis_text.config(state=tk.DISABLED)
        return
    
    # Interpreta i dati e genera il riepilogo
    
    # 1. Emozioni e sentimenti
    if "Emotions" in raw_data:
        try:
            emotions_data = ast.literal_eval(raw_data["Emotions"])
            if isinstance(emotions_data, dict):
                dominant_emotion = emotions_data.get("dominant_emotion")
                dominant_sentiment = emotions_data.get("dominant_sentiment")
                
                if dominant_emotion and dominant_sentiment:
                    analysis_text.insert(tk.END, f"Tono emotivo: {dominant_emotion}\n")
                    analysis_text.insert(tk.END, f"Sentimento: {dominant_sentiment}\n\n")
                    
                    # Aggiungi percentuali se disponibili
                    if "emotion_percentages" in emotions_data:
                        analysis_text.insert(tk.END, "Distribuzione emozioni:\n")
                        for emotion, percentage in emotions_data["emotion_percentages"].items():
                            analysis_text.insert(tk.END, f"- {emotion}: {percentage:.1f}%\n")
                        analysis_text.insert(tk.END, "\n")
        except Exception as e:
            logging.error(f"Errore nell'interpretazione delle emozioni: {e}")
    
    # 2. Personaggio principale
    if "Main Character" in raw_data:
        try:
            character_data = ast.literal_eval(raw_data["Main Character"])
            if character_data and isinstance(character_data, dict):
                name = character_data.get("name")
                count = character_data.get("count")
                early_appearance = character_data.get("early_appearance", False)
                
                if name:
                    analysis_text.insert(tk.END, f"Protagonista: {name}\n")
                    analysis_text.insert(tk.END, f"Occorrenze: {count}\n")
                    if early_appearance:
                        analysis_text.insert(tk.END, "Appare all'inizio del capitolo\n")
                    analysis_text.insert(tk.END, "\n")
        except Exception as e:
            logging.error(f"Errore nell'interpretazione del personaggio principale: {e}")
    
    # 3. Ambientazione principale
    if "Main Location" in raw_data:
        try:
            location_data = ast.literal_eval(raw_data["Main Location"])
            if location_data and isinstance(location_data, dict):
                name = location_data.get("name")
                category = location_data.get("category")
                confidence = location_data.get("confidence")
                count = location_data.get("count")
                
                if name:
                    analysis_text.insert(tk.END, f"Ambientazione: {name}\n")
                    analysis_text.insert(tk.END, f"Tipo: {category}\n")
                    analysis_text.insert(tk.END, f"Confidenza: {confidence:.2f}\n")
                    analysis_text.insert(tk.END, f"Occorrenze: {count}\n\n")
                    
                    # Imposta i suoni per questa location
                    if sound_controller and category:
                        # Usa un thread per non bloccare la GUI
                        threading.Thread(target=sound_controller.set_location_sounds, 
                                         args=(category,), daemon=True).start()
        except Exception as e:
            logging.error(f"Errore nell'interpretazione dell'ambientazione: {e}")
    
    # 4. Entità riconosciute
    if "Entities" in raw_data:
        try:
            entities_data = ast.literal_eval(raw_data["Entities"])
            
            # Converti in Counter se è una lista
            if isinstance(entities_data, list):
                entities_data = Counter(entities_data)
                
            # Estrai persone e luoghi
            people = {}
            locations = {}
            
            for (entity, label), count in entities_data.items():
                if label == "PER":
                    people[entity] = count
                elif label == "LOC":
                    locations[entity] = count
            
            # Mostra le persone più frequenti
            if people:
                analysis_text.insert(tk.END, "Persone più frequenti:\n")
                for person, count in sorted(people.items(), key=lambda x: x[1], reverse=True)[:10]:  # Top 10
                    analysis_text.insert(tk.END, f"- {person}: {count}\n")
                analysis_text.insert(tk.END, "\n")
                
            # Mostra i luoghi più frequenti
            if locations:
                analysis_text.insert(tk.END, "Luoghi più frequenti:\n")
                for location, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10]:  # Top 10
                    analysis_text.insert(tk.END, f"- {location}: {count}\n")
                analysis_text.insert(tk.END, "\n")
        except Exception as e:
            logging.error(f"Errore nell'interpretazione delle entità: {e}")
    
    # 5. Tempi di esecuzione per debug/performance
    if "Tempi di analisi" in raw_data:
        try:
            times = ast.literal_eval(raw_data["Tempi di analisi"])
            if times and isinstance(times, dict):
                analysis_text.insert(tk.END, "Tempi di analisi:\n")
                total_time = times.get("Tempo totale", 0)
                analysis_text.insert(tk.END, f"Tempo totale: {total_time:.2f} s\n")
        except Exception as e:
            logging.error(f"Errore nell'interpretazione dei tempi: {e}")
    
    analysis_text.config(state=tk.DISABLED)

def create_chapter_button(chapter, start_page):
    button = tk.Button(chapters_inner_frame, text=f"Capitolo {chapter}", command=lambda: show_page(start_page - 1), width=20)
    button.pack(fill="x", padx=5, pady=2)
    # print(f"Creato pulsante per Capitolo {chapter} - Pagina {start_page}")  # Debug

def update_chapters_display():
    for widget in chapters_inner_frame.winfo_children():
        widget.destroy()
    
    if not analysis_data:  # Se il dizionario è vuoto, vuol dire che non ha caricato nulla
        label = tk.Label(chapters_inner_frame, text="File di analisi non trovato.\nPremere 'Avvia Analisi' per generarlo.", font=("Arial", default_font_size))
        label.pack(fill="x", padx=5, pady=5)
    else:
        # Creare pulsanti solo per l'inizio di ogni capitolo
        created_chapters = set()
        for start_page in sorted(analysis_data.keys()):
            chapter = analysis_data[start_page]
            if chapter not in created_chapters:
                create_chapter_button(chapter, start_page)
                created_chapters.add(chapter)


def show_page(page_num=None):
    global book_name, analysis_data, current_page
    if page_num is not None:
        current_page = page_num
    # print(f"Mostra pagina {current_page}")  # Debug
    # Mostra la pagina corrente.
    if text_pages:
        text_area.config(state=tk.NORMAL)
        text_area.delete("1.0", tk.END)
        text_area.insert(tk.END, text_pages[current_page])
        text_area.config(state=tk.DISABLED)
        page_label.config(text=f"Pagina {current_page + 1} di {len(text_pages)}")
        if analysis_data:
            update_analysis_display()
        else:
            analysis_text.config(state=tk.NORMAL)
            analysis_text.delete("1.0", tk.END)
            analysis_text.insert(tk.END, f"Analisi non trovata per {book_name}")
            # print(f"Analisi non trovata per {book_name}")  # Debug
        save_settings()

def next_page(event=None):
    # Mostra la pagina successiva.
    global current_page
    if current_page < len(text_pages) - 1:
        current_page += 1
        show_page(current_page)

def prev_page(event=None):
    # Mostra la pagina precedente.
    global current_page
    if current_page > 0:
        current_page -= 1
        show_page(current_page)


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



def go_to_page():
    global current_page
    page_num = simpledialog.askinteger("Vai a pagina", "Inserisci il numero della pagina:", minvalue=1, maxvalue=len(text_pages))
    if page_num:
        current_page = page_num - 1
        show_page()



def show_contacts():
    # Mostra la finestra con i contatti e i crediti.
    messagebox.showinfo("Contatti", "Sviluppato da Sacca' Maurizio\nEmail: mauriziosacc4@gmail.com")



# Creazione GUI
root = tk.Tk()
root.title("Caricamento Libro a Pagine")
root.geometry(f"{window_width}x{window_height}")
root.state('normal')

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
settings_menu.add_separator()
settings_menu.add_command(label="Vai a pagina", command=go_to_page)
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

stop_button = tk.Button(analysis_frame, text="Ferma Analisi", command=stop_analysis, state=tk.DISABLED)
stop_button.pack(side=tk.RIGHT, padx=5)


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

right_frame = tk.Frame(main_frame)
right_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=20, pady=10)

# Frame per i capitoli (superiore destra)
chapters_frame = tk.Frame(right_frame, relief=tk.GROOVE, borderwidth=2)
chapters_frame.pack(fill="x")

chapter_label = tk.Label(chapters_frame, text="Capitoli Trovati", font=("Arial", default_font_size, "bold"))
chapter_label.pack()

# Aggiungi una scrollbar per i pulsanti dei capitoli
chapters_canvas = tk.Canvas(chapters_frame)
chapters_scrollbar = tk.Scrollbar(chapters_frame, orient="vertical", command=chapters_canvas.yview)
chapters_inner_frame = tk.Frame(chapters_canvas)

chapters_inner_frame.bind(
    "<Configure>",
    lambda e: chapters_canvas.configure(
        scrollregion=chapters_canvas.bbox("all")
    )
)

chapters_canvas.create_window((0, 0), window=chapters_inner_frame, anchor="nw")
chapters_canvas.configure(yscrollcommand=chapters_scrollbar.set)

chapters_canvas.pack(side="left", fill="both", expand=True)
chapters_scrollbar.pack(side="right", fill="y")

# Frame per l'analisi (centrale/inferiore destra)
analysis_text = scrolledtext.ScrolledText(right_frame, width=30, height=15, state=tk.DISABLED)
analysis_text.pack(fill="both", expand=True, padx=10, pady=10)

# Aggiungi questo codice dopo la creazione di analysis_text in gui.py

# Frame per il controllo audio
audio_frame = tk.LabelFrame(right_frame, text="Audio Ambientale", padx=5, pady=5)
audio_frame.pack(fill="x", padx=10, pady=5)

# Variabile per tracciare lo stato audio
audio_enabled = tk.BooleanVar(value=True)

# Controllo volume principale
master_volume_frame = tk.Frame(audio_frame)
master_volume_frame.pack(fill="x", pady=5)

tk.Label(master_volume_frame, text="Volume principale:").pack(side=tk.LEFT)
master_volume = tk.Scale(master_volume_frame, from_=0, to=100, orient=tk.HORIZONTAL)
master_volume.set(50)  # Imposta al 50% inizialmente
master_volume.pack(side=tk.LEFT, fill="x", expand=True, padx=5)

def update_master_volume(event=None):
    if sound_controller:
        sound_controller.set_master_volume(master_volume.get() / 100.0)
        
master_volume.bind("<ButtonRelease-1>", update_master_volume)

# Pulsanti di controllo audio
audio_buttons_frame = tk.Frame(audio_frame)
audio_buttons_frame.pack(fill="x", pady=5)

def toggle_audio():
    if sound_controller:
        if audio_enabled.get():
            sound_controller.resume_all()
            toggle_button.config(text="Pausa")
        else:
            sound_controller.pause_all()
            toggle_button.config(text="Riprendi")

toggle_button = tk.Button(audio_buttons_frame, text="Pausa", command=lambda: [audio_enabled.set(not audio_enabled.get()), toggle_audio()])
toggle_button.pack(side=tk.LEFT, padx=5)

# Lista suoni attivi (viene aggiornata dinamicamente)
sounds_list_frame = tk.Frame(audio_frame)
sounds_list_frame.pack(fill="both", expand=True, pady=5)

sounds_list = tk.Listbox(sounds_list_frame, height=3)
sounds_list.pack(fill="both", expand=True, side=tk.LEFT)

sounds_scrollbar = tk.Scrollbar(sounds_list_frame, orient=tk.VERTICAL, command=sounds_list.yview)
sounds_scrollbar.pack(side=tk.RIGHT, fill="y")
sounds_list.config(yscrollcommand=sounds_scrollbar.set)

# Funzione per aggiornare la lista di suoni attivi
def update_sounds_list():
    if sound_controller:
        sounds_list.delete(0, tk.END)
        active_sounds = sound_controller.get_active_sounds()
        for sound in active_sounds:
            status = "▶️" if sound['is_playing'] else "⏸️"
            sounds_list.insert(tk.END, f"{status} {sound['filename']} ({int(sound['volume']*100)}%)")
    
    # Aggiorna ogni secondo
    root.after(1000, update_sounds_list)

# Avvia l'aggiornamento della lista
root.after(1000, update_sounds_list)

# Aggiungi anche la pulizia del controller audio quando si chiude la finestra
def on_closing():
    save_settings()
    if sound_controller:
        sound_controller.cleanup()
    root.destroy()
    
root.protocol("WM_DELETE_WINDOW", on_closing)

# Ripristina ultimo file e pagina
if last_file and os.path.exists(last_file):
    open_file(last_file)
    current_page = min(last_page, len(text_pages) - 1)
    show_page(current_page)

root.protocol("WM_DELETE_WINDOW", lambda: (save_settings(), root.destroy()))
root.mainloop()
