import sys
import re
import os
import fitz  # PyMuPDF per i PDF
import docx  # python-docx per i file Word
import multiprocessing
import csv
import datetime
import time

PAGE_SIZE = 3300  # Deve essere lo stesso della GUI
DEFAULT_CHAPTER_LENGTH = 12  # Se nessun capitolo viene trovato

# -------------------- FUNZIONI DI LETTURA --------------------

def read_txt(file_path):
    # Legge un file di testo e lo divide in pagine.
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    return [text[i:i+PAGE_SIZE] for i in range(0, len(text), PAGE_SIZE)]

def read_pdf(file_path):
    # Legge un file PDF ed estrae il testo.
    doc = fitz.open(file_path)
    text = "\n".join([page.get_text() for page in doc])
    return [text[i:i+PAGE_SIZE] for i in range(0, len(text), PAGE_SIZE)]

def read_docx(file_path):
    # Legge un file Word (.docx) ed estrae il testo.
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return [text[i:i+PAGE_SIZE] for i in range(0, len(text), PAGE_SIZE)]

def read_book(file_path):
    # Determina il formato del file e chiama il metodo di lettura appropriato.
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        return read_txt(file_path)
    elif ext == ".pdf":
        return read_pdf(file_path)
    elif ext == ".docx":
        return read_docx(file_path)
    else:
        print("Errore: formato file non supportato.")
        sys.exit(4)

# -------------------- FUNZIONI PER TROVARE I CAPITOLI --------------------

def find_index_section(pages):
   # Cerca un possibile indice del libro nelle prime pagine.
    print("Cerco l'indice...")
    for page_number, page in enumerate(pages[:5]):  # Cerca nelle prime 5 pagine
        matches = re.findall(r'(\b(?:Capitolo|Chapter)\s+\d+\b).*?(\d+)', page, re.IGNORECASE)
        if matches:
            return {int(num): int(matches[0][1]) for _, num in matches}  # Correzione dell'assegnazione della pagina
    return None

def find_chapters(pages):
# Cerca i capitoli nel testo usando pattern comuni.
    print("Indice non trovato, cerco i capitoli...")
    chapters = {}
    for page_number, page in enumerate(pages):
        matches = re.findall(r'\b(?:Capitolo|Chapter)\s+(\d+)\b', page, re.IGNORECASE)
        if matches:
            for match in matches:
                chapters[int(match)] = page
    return chapters if chapters else None

def divide_by_fixed_length(pages):
    # Divide il libro in sezioni di lunghezza fissa se non trova i capitoli.
    print(f"Capitoli non trovati, suddivido manualmente ogni {DEFAULT_CHAPTER_LENGTH} pagine")
    return {i+1: "\n".join(pages[i * DEFAULT_CHAPTER_LENGTH:(i + 1) * DEFAULT_CHAPTER_LENGTH]) 
            for i in range(len(pages) // DEFAULT_CHAPTER_LENGTH)}

# -------------------- ANALISI PARALLELA --------------------

def analyze_chapter(book_name, chapter_num, chapter_text):
    file_name = f"{book_name}-capitolo{chapter_num}-analysis.csv"
    
    # Scrive "Analisi non completa"
    with open(file_name, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Stato", "Analisi non completa"])

        writer.writerow(["Testo", chapter_text])

    # Scrive "Analisi completata"
    completion_time = datetime.datetime.now().strftime("%d/%m/%Y alle %H:%M:%S")
    with open(file_name, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Stato", f"Analisi completata il {completion_time}"])

def parallel_analysis(book_name, chapters):
    num_workers = min(multiprocessing.cpu_count(), len(chapters))
    with multiprocessing.Pool(processes=num_workers) as pool:
        tasks = [
            pool.apply_async(analyze_chapter, (book_name, chapter, text))
            for chapter, text in chapters.items()
        ]
        [task.wait() for task in tasks]  # Aspetta la fine di tutti i processi

# -------------------- MAIN --------------------

def main():
    input_file = sys.argv
    
    if len(input_file) < 2:
        print("Errore: specificare il file da analizzare.")
        sys.exit(1)
    
    file_path = input_file[1]
    if not os.path.exists(file_path):
        print("Errore: file non trovato.")
        sys.exit(2)

    book_name = os.path.splitext(os.path.basename(file_path))[0]
    pages = read_book(file_path)

    # Cerca prima l'indice
    index_sections = find_index_section(pages)
    
    # Se non trova l'indice, cerca i capitoli
    chapters = find_chapters(pages) if not index_sections else None

    # Se nessuno dei due metodi ha funzionato, divide manualmente
    final_chapters = index_sections or chapters or divide_by_fixed_length(pages)

    print("Capitoli individuati:")
    for chapter, _ in final_chapters.items():
        print(f"Capitolo {chapter}")

    # Analisi parallela
    parallel_analysis(book_name, final_chapters)

    # Creazione del file di riepilogo
    summary_file = f"{book_name}-analysis.csv"
    with open(summary_file, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Capitolo", "Stato"])
        for chapter in final_chapters.keys():
            chapter_file = f"{book_name}-capitolo{chapter}-analysis.csv"
            with open(chapter_file, "r", encoding="utf-8") as ch_f:
                reader = csv.reader(ch_f)
                next(reader)  # Salta l'intestazione
                status = next(reader)[1]  # Legge lo stato
                writer.writerow([chapter, status])

    print(f"Analisi completata. Riepilogo salvato in {summary_file}")
    sys.exit(0)

if __name__ == "__main__":
    main()

