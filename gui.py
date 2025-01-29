import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, Menu
import fitz  # PyMuPDF per PDF
import docx  # python-docx per Word
import configparser  # Per salvare le impostazioni
import os
import logging

# Configurazione logging
LOG_FILE = "error.log"
logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurazione iniziale
PAGE_SIZE = 3300
text_pages = []
current_page = 0
current_file = None
profile_file = "profile.ini"

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
    global text_pages, current_page, current_file
    try:
        if not filepath:
            filepath = filedialog.askopenfilename(filetypes=[
                ("Text Files", "*.txt"),
                ("PDF Files", "*.pdf"),
                ("Word Documents", "*.docx")
            ])
            
        if not filepath:
            return
        
        current_file = filepath
        if filepath.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as file:
                text = file.read()
        elif filepath.endswith(".pdf"):
            text = extract_text_from_pdf(filepath)
        elif filepath.endswith(".docx"):
            text = extract_text_from_docx(filepath)
        else:
            text = "Formato non supportato."

        text_pages = [text[i:i + PAGE_SIZE] for i in range(0, len(text), PAGE_SIZE)]
        current_page = 0
        show_page()
    except Exception as e:
        logging.error(str(e))
        messagebox.showerror("Errore", f"Errore: {str(e)}")


def extract_text_from_pdf(pdf_path):
    # Estrae il testo da un file PDF.
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text() for page in doc])


def extract_text_from_docx(docx_path):
    # Estrae il testo da un file DOCX.
    doc = docx.Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])


def show_page():
    # Mostra la pagina corrente.
    if text_pages:
        text_area.config(state=tk.NORMAL)
        text_area.delete("1.0", tk.END)
        text_area.insert(tk.END, text_pages[current_page])
        text_area.config(state=tk.DISABLED)
        page_label.config(text=f"Pagina {current_page + 1} di {len(text_pages)}")
        save_settings()

def next_page():
    # Mostra la pagina successiva.
    global current_page
    if current_page < len(text_pages) - 1:
        current_page += 1
        show_page()

def prev_page():
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
root.geometry(f"{window_width}x{window_height}")  # Imposta la dimensione salvata
root.state('zoomed')  # Avvio a schermo intero
root.resizable(True, True)

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
settings_menu.add_command(label="Pagina Successiva: Freccia Destra → ", command=next_page)
settings_menu.add_command(label="Pagina precedente: Freccia Sinistra ← ", command=prev_page)
menu_bar.add_cascade(label="Impostazioni", menu=settings_menu)

# sezione contatti
contacts_menu = Menu(menu_bar, tearoff=0)
contacts_menu.add_command(label="Contatti", command=show_contacts)
menu_bar.add_cascade(label="Contatti", menu=Menu(menu_bar, tearoff=0))

root.config(menu=menu_bar)


page_label = tk.Label(root, text="Pagina 1 di 1")
page_label.pack()

nav_frame = tk.Frame(root)
nav_frame.pack()

btn_prev = tk.Button(nav_frame, text="← Pagina Precedente", command=prev_page)
btn_prev.pack(side=tk.LEFT, padx=5)


btn_next = tk.Button(nav_frame, text="Pagina Successiva →", command=next_page)
btn_next.pack(side=tk.LEFT, padx=5)


# Area di testo
default_font = ("Arial", default_font_size)
text_area = scrolledtext.ScrolledText(root, width=60, height=20, state=tk.DISABLED, font=default_font)
text_area.pack(expand=True, fill='both', padx=10, pady=10)

# Bind per lo zoom con tastiera
root.bind("<Control-plus>", increase_font)
root.bind("<Control-minus>", decrease_font)
root.bind("<Right>", next_page)
root.bind("<Left>", prev_page)

# Ripristina ultimo file e pagina
if last_file and os.path.exists(last_file):
    open_file(last_file)
    current_page = min(last_page, len(text_pages) - 1)
    show_page()



root.protocol("WM_DELETE_WINDOW", lambda: (save_settings(), root.destroy()))
root.mainloop()
