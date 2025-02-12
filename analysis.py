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
    return text

def read_pdf(file_path):
    # Legge un file PDF ed estrae il testo.
    doc = fitz.open(file_path)
    text = "\n".join([page.get_text() for page in doc])
    return text

def read_docx(file_path):
    # Legge un file Word (.docx) ed estrae il testo.
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def read_book(file_path):
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

def find_index_section(text):
    # Cerca un possibile indice del libro nelle prime pagine.
    print("Cerco l'indice...")
    matches = re.findall(r'(\b(?:Capitolo|Chapter)\s+\d+\b).*?(\d+)', text[:PAGE_SIZE*5], re.IGNORECASE)
    if matches:
        return {int(num): int(matches[0][1]) for _, num in matches}
    return None

def find_chapters(text):
    # Cerca i capitoli nel testo usando pattern comuni.
    print("Indice non trovato, cerco i capitoli...")
    chapters = {}
    for match in re.finditer(r'\b(?:Capitolo|Chapter)\s+(\d+)\b', text, re.IGNORECASE):
        chapter_num = int(match.group(1))
        start_byte = match.start()
        chapters[chapter_num] = start_byte
    return chapters if chapters else None

def divide_by_fixed_length(text):
    # Divide il libro in sezioni di lunghezza fissa se non trova i capitoli.
    print(f"Capitoli non trovati, suddivido manualmente ogni {DEFAULT_CHAPTER_LENGTH * PAGE_SIZE} byte")
    chapters = {}
    for i in range(0, len(text), DEFAULT_CHAPTER_LENGTH * PAGE_SIZE):
        chapter_num = i // (DEFAULT_CHAPTER_LENGTH * PAGE_SIZE) + 1
        chapters[chapter_num] = i
    return chapters

# -------------------- ANALISI PARALLELA --------------------

def analyze_chapter(book_name, chapter_num, chapter_text, output_dir):
    file_name = os.path.join(output_dir, f"{book_name}-capitolo{chapter_num}-analysis.csv")
    
    # Scrive "Analisi non completa"
    with open(file_name, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Stato", "Analisi non completa"])
        time.sleep(5)

    # Scrive "Analisi completata"
    completion_time = datetime.datetime.now().strftime("%d/%m/%Y alle %H:%M:%S")
    with open(file_name, "a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Stato", f"Analisi completata il {completion_time}"])

def parallel_analysis(book_name, chapters, text, output_dir):
    num_workers = min(multiprocessing.cpu_count(), len(chapters))
    with multiprocessing.Pool(processes=num_workers) as pool:
        tasks = []
        chapter_list = sorted(chapters.items())  # Ordina i capitoli per numero

        for i in range(len(chapter_list)):
            chapter_number, start_byte = chapter_list[i]
            end_byte = chapter_list[i + 1][1] if i + 1 < len(chapter_list) else len(text)

            chapter_text = text[start_byte:end_byte]
            tasks.append(pool.apply_async(analyze_chapter, (book_name, chapter_number, chapter_text, output_dir)))

        [task.wait() for task in tasks] # Aspetta per tutti i processi

def calculate_page_ranges(chapters, text):
    page_ranges = {}
    chapter_list = sorted(chapters.items())
    for i in range(len(chapter_list)):
        chapter_number, start_byte = chapter_list[i]
        end_byte = chapter_list[i + 1][1] if i + 1 < len(chapter_list) else len(text)
        
        start_page = start_byte // PAGE_SIZE + 1
        end_page = end_byte // PAGE_SIZE + 1
        
        page_ranges[chapter_number] = (start_page, end_page)
    return page_ranges

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
    output_dir = os.path.join(os.getcwd(), "analyses", book_name)
    os.makedirs(output_dir, exist_ok=True)
    text = read_book(file_path)

    # Cerca prima l'indice
    index_sections = find_index_section(text)
    
    # Se non trova l'indice, cerca i capitoli
    chapters = find_chapters(text) if not index_sections else None

    # Se nessuno dei due metodi ha funzionato, divide manualmente
    final_chapters = index_sections or chapters or divide_by_fixed_length(text)

    print("Capitoli individuati:")
    for chapter, _ in final_chapters.items():
        print(f"Capitolo {chapter}")

    # Calcola i range delle pagine per ogni capitolo
    page_ranges = calculate_page_ranges(final_chapters, text)

    # Analisi parallela
    parallel_analysis(book_name, final_chapters, text, output_dir)

    # Creazione del file di riepilogo
    summary_file = os.path.join(output_dir, f"{book_name}-analysis.csv")
    with open(summary_file, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Capitolo", "Range Pagine"])
        for chapter, (start_page, end_page) in page_ranges.items():
            writer.writerow([chapter, f"{start_page}-{end_page}"])

    print(f"Analisi completata. Riepilogo salvato in {summary_file}")
    sys.exit(0)

if __name__ == "__main__":
    main()

