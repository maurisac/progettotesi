import sys
import re
import os
import fitz  # PyMuPDF per i PDF
import docx  # python-docx per i file Word
import multiprocessing
import csv
import datetime
import time
from transformers import BertTokenizer, BertModel, pipeline
import spacy
import torch
from collections import Counter

PAGE_SIZE = 3300  # Deve essere lo stesso della GUI
DEFAULT_CHAPTER_LENGTH = 12  # Se nessun capitolo viene trovato
MAX_TEXT_LENGTH = 512  # Lunghezza massima del testo per l'analisi del sentiment

# Caricare il modello pre-addestrato
MODEL_NAME = "dbmdz/bert-base-italian-xxl-cased"
tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)
model = BertModel.from_pretrained(MODEL_NAME)

# Caricare il modello spaCy per l'italiano
nlp = spacy.load("it_core_news_md")

# Caricare il modello di sentiment analysis per l'italiano
sentiment_model = pipeline("sentiment-analysis", model="MilaNLProc/feel-it-italian-sentiment", top_k=None)

# Mappatura delle emozioni di Ekman
emotion_mapping = {
    "POSITIVE": "gioia",
    "NEGATIVE": "tristezza",
    "NEUTRAL": "neutro",
    "ANGER": "rabbia",
    "DISGUST": "disgusto",
    "FEAR": "paura",
    "SURPRISE": "sorpresa"
}

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

def analyze_text_with_bert(text):
    try:
        print("Inizio analisi con BERT...")
        # Tokenizzazione del testo
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        
        # Esegui il modello per ottenere embedding
        with torch.no_grad():
            outputs = model(**inputs)

        # L'output è una rappresentazione vettoriale del testo (usata per NLP avanzato)
        embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
        
        print("Analisi con BERT completata.")
        return embeddings  # Questi vettori possono essere usati per analisi più complesse
    except Exception as e:
        print(f"Errore durante l'analisi con BERT: {e}")
        return None

def analyze_text_with_spacy(text):
    try:
        print("Inizio analisi con spaCy...")
        # Analizza il testo con spaCy per estrarre entità e altre informazioni linguistiche
        doc = nlp(text)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        entity_counts = Counter(entities)
        print("Analisi con spaCy completata.")
        return entity_counts
    except Exception as e:
        print(f"Errore durante l'analisi con spaCy: {e}")
        return None

def are_entities_synonyms(entity1, entity2):
    try:
        print(f"Verifica se {entity1} e {entity2} sono sinonimi...")
        # Verifica se due entità sono sinonimi utilizzando BERT
        inputs = tokenizer([entity1, entity2], return_tensors="pt", truncation=True, max_length=512, padding=True)
        with torch.no_grad():
            outputs = model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
        similarity = torch.cosine_similarity(embeddings[0], embeddings[1], dim=0)
        print(f"Similarità tra {entity1} e {entity2}: {similarity.item()}")
        return similarity.item() > 0.8  # Soglia di similarità
    except Exception as e:
        print(f"Errore durante la verifica dei sinonimi: {e}")
        return False

def split_text(text, max_length):
    # Divide il testo in parti più piccole di lunghezza massima max_length
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def analyze_emotions(text):
    try:
        print("Inizio analisi delle emozioni...")
        # Divide il testo in parti più piccole
        text_parts = split_text(text, MAX_TEXT_LENGTH)
        emotion_counts = Counter()
        for part in text_parts:
            sentiment_scores = sentiment_model(part)
            for score in sentiment_scores:
                for sentiment in score:
                    emotion = emotion_mapping.get(sentiment['label'], "neutro")
                    emotion_counts[emotion] += sentiment['score']
        main_emotion = emotion_counts.most_common(1)[0][0]
        print(f"Emozione predominante: {main_emotion}")
        return main_emotion
    except Exception as e:
        print(f"Errore durante l'analisi delle emozioni: {e}")
        return "neutro"

def generate_summary(entity_counts, main_emotion):
    try:
        print("Inizio generazione della sintesi...")
        # Genera una sintesi basata sulle entità trovate e l'emozione principale
        summary = []
        people = [ent for ent, label in entity_counts if label == "PER"]
        locations = [ent for ent, label in entity_counts if label == "LOC"]
        
        # Verifica se alcune entità sono sinonimi
        for i, person1 in enumerate(people):
            for person2 in people[i+1:]:
                if are_entities_synonyms(person1, person2):
                    people = [person2 if p == person1 else p for p in people]
        
        for i, location1 in enumerate(locations):
            for location2 in locations[i+1:]:
                if are_entities_synonyms(location1, location2):
                    locations = [location2 if l == location1 else l for l in locations]
        
        if people:
            main_character = max(set(people), key=lambda x: (people.count(x), -people.index(x)))
            summary.append(f"Il protagonista di questo capitolo è probabilmente {main_character}.")
        
        if locations:
            main_location = max(set(locations), key=lambda x: (locations.count(x), -locations.index(x)))
            summary.append(f"L'ambientazione principale è probabilmente {main_location}.")
        
        summary.append(f"L'emozione predominante in questo capitolo è {main_emotion}.")
        
        print("Generazione della sintesi completata.")
        return "\n".join(summary)
    except Exception as e:
        print(f"Errore durante la generazione della sintesi: {e}")
        return "Errore durante la generazione della sintesi."

def analyze_chapter(book_name, chapter_num, chapter_text, output_dir):
    try:
        print(f"Inizio analisi del capitolo {chapter_num}...")
        file_name = os.path.join(output_dir, f"{book_name}-capitolo{chapter_num}-analysis.csv")
        
        # Scrive "Analisi non completa"
        with open(file_name, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Stato", "Analisi non completa"])
            time.sleep(5)

        # Esegui l'analisi delle emozioni
        main_emotion = analyze_emotions(chapter_text)
        
        # Scrive "Analisi completata"
        completion_time = datetime.datetime.now().strftime("%d/%m/%Y alle %H:%M:%S")
        with open(file_name, "a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Stato", f"Analisi completata il {completion_time}"])
            writer.writerow(["Emozione predominante", main_emotion])

        print(f"Analisi del capitolo {chapter_num} completata.")
    except Exception as e:
        print(f"Errore durante l'analisi del capitolo {chapter_num}: {e}")

def parallel_analysis(book_name, chapters, text, output_dir):
    try:
        print("Inizio analisi parallela...")
        num_workers = min(multiprocessing.cpu_count(), len(chapters))
        with multiprocessing.Pool(processes=num_workers) as pool:
            tasks = []
            chapter_list = sorted(chapters.items())  # Ordina i capitoli per numero

            # Limita l'analisi ai primi due capitoli per risparmiare tempo
            # chapter_list = chapter_list[:2]

            for i in range(len(chapter_list)):
                chapter_number, start_byte = chapter_list[i]
                end_byte = chapter_list[i + 1][1] if i + 1 < len(chapter_list) else len(text)

                chapter_text = text[start_byte:end_byte]
                tasks.append(pool.apply_async(analyze_chapter, (book_name, chapter_number, chapter_text, output_dir)))

            [task.wait() for task in tasks] # Aspetta per tutti i processi

        print("Analisi parallela completata.")
    except Exception as e:
        print(f"Errore durante l'analisi parallela: {e}")

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
    try:
        print("Inizio esecuzione del programma principale...")
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
    except Exception as e:
        print(f"Errore durante l'esecuzione del programma principale: {e}")

if __name__ == "__main__":
    main()

