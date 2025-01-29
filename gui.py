import tkinter as tk
from tkinter import filedialog, scrolledtext
import fitz  # PyMuPDF per PDF
import docx  # python-docx per Word

# Configurazione
PAGE_SIZE = 2500  # Numero di caratteri per pagina
text_pages = []  # Lista di pagine
current_page = 0  # Indice della pagina attuale

def open_file():
    """Apre un file TXT, PDF o DOCX, lo divide in pagine e mostra la prima pagina."""
    global text_pages, current_page
    filepath = filedialog.askopenfilename(filetypes=[
        ("Text Files", "*.txt"),
        ("PDF Files", "*.pdf"),
        ("Word Documents", "*.docx")
    ])
    
    if not filepath:
        return

    # Lettura del file
    if filepath.endswith(".txt"):
        with open(filepath, "r", encoding="utf-8") as file:
            text = file.read()
    elif filepath.endswith(".pdf"):
        text = extract_text_from_pdf(filepath)
    elif filepath.endswith(".docx"):
        text = extract_text_from_docx(filepath)
    else:
        text = "Formato non supportato."

    # Dividere il testo in pagine
    text_pages = [text[i:i + PAGE_SIZE] for i in range(0, len(text), PAGE_SIZE)]
    current_page = 0

    # Mostrare la prima pagina
    show_page()

def extract_text_from_pdf(pdf_path):
    """Estrae il testo da un file PDF."""
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text() for page in doc])
    return text

def extract_text_from_docx(docx_path):
    """Estrae il testo da un file DOCX."""
    doc = docx.Document(docx_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def show_page():
    """Mostra la pagina corrente."""
    if text_pages:
        text_area.config(state=tk.NORMAL)
        text_area.delete("1.0", tk.END)
        text_area.insert(tk.END, text_pages[current_page])
        text_area.config(state=tk.DISABLED)
        page_label.config(text=f"Pagina {current_page + 1} di {len(text_pages)}")

def next_page():
    """Mostra la pagina successiva."""
    global current_page
    if current_page < len(text_pages) - 1:
        current_page += 1
        show_page()

def prev_page():
    """Mostra la pagina precedente."""
    global current_page
    if current_page > 0:
        current_page -= 1
        show_page()

# Creazione GUI
root = tk.Tk()
root.title("Caricamento Libro a Pagine")

btn_open = tk.Button(root, text="Seleziona File", command=open_file)
btn_open.pack(pady=10)

text_area = scrolledtext.ScrolledText(root, width=60, height=20, state=tk.DISABLED)
text_area.pack(pady=10)

# Controlli di navigazione
nav_frame = tk.Frame(root)
nav_frame.pack()

btn_prev = tk.Button(nav_frame, text="← Pagina Precedente", command=prev_page)
btn_prev.pack(side=tk.LEFT, padx=5)

page_label = tk.Label(nav_frame, text="Pagina 0 di 0")
page_label.pack(side=tk.LEFT, padx=5)

btn_next = tk.Button(nav_frame, text="Pagina Successiva →", command=next_page)
btn_next.pack(side=tk.LEFT, padx=5)

root.mainloop()
