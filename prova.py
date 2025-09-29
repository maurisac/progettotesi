"""
codice per provare il riconoscimento di entità con spaCy e la classificazione di luoghi con BERT.
"""

# Importa le librerie necessarie
import spacy
import fitz
import torch
import json
from transformers import BertTokenizerFast, BertForSequenceClassification
from collections import Counter
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
from transformers import pipeline

# Carica il modello spaCy per l'italiano
print("Caricamento modello spaCy...")
nlp = spacy.load("it_core_news_md")

# Carica il modello BERT per la classificazione dei luoghi
print("Caricamento modello BERT...")
model_name = "./bert_location_classifier"
bert_tokenizer = BertTokenizerFast.from_pretrained(model_name)
bert_model = BertForSequenceClassification.from_pretrained(model_name)

print("Caricamento modello osiria/bert-italian-cased-ner per NER...")
try:
    # Carica il modello BERT-NER italiano
    tokenizer_ner = AutoTokenizer.from_pretrained("osiria/bert-italian-cased-ner")
    model_ner = AutoModelForTokenClassification.from_pretrained("osiria/bert-italian-cased-ner")
    ner_pipeline = pipeline("ner", model=model_ner, tokenizer=tokenizer_ner, aggregation_strategy="simple")
    print("Modello NER caricato con successo")
except Exception as e:
    print(f"Errore nel caricamento del modello NER: {e}")
    ner_pipeline = None

# Carica il mapping delle categorie
try:
    with open(f"{model_name}/category_mapping.json", "r", encoding="utf-8") as f:
        category_mapping = json.load(f)
    id_to_category = {int(k): v for k, v in category_mapping["id_to_category"].items()}
except FileNotFoundError:
    print("File di mapping delle categorie non trovato. Impossibile classificare i luoghi.")
    exit(1)

# Funzione per classificare un luogo
def classify_location(location, context=""):
    """Classifica il tipo di location utilizzando il modello BERT."""
    try:
        # Prepara l'input
        inputs = bert_tokenizer(
            location,
            context,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        )
        
        # Inferenza
        with torch.no_grad():
            outputs = bert_model(**inputs)
        
        # Ottieni la classe predetta
        predicted_class_id = outputs.logits.argmax().item()
        predicted_category = id_to_category[predicted_class_id]
        confidence = torch.softmax(outputs.logits, dim=1)[0, predicted_class_id].item()
        
        return {
            "category": predicted_category,
            "confidence": confidence
        }
    except Exception as e:
        print(f"Errore nella classificazione della location {location}: {e}")
        return {"category": "sconosciuto", "confidence": 0.0}

# Funzione per dividere il testo in blocchi più piccoli per elaborazione spaCy
def process_text_in_chunks(text, chunk_size=100000):
    """Divide il testo in chunk per evitare limiti di memoria con spaCy."""
    chunks = []
    current_chunk = []
    current_size = 0
    
    for paragraph in text.split("\n"):
        # Se il paragrafo è troppo grande, dividerlo ulteriormente
        if len(paragraph) > chunk_size:
            for i in range(0, len(paragraph), chunk_size):
                chunks.append(paragraph[i:i+chunk_size])
        else:
            if current_size + len(paragraph) > chunk_size:
                chunks.append("\n".join(current_chunk))
                current_chunk = [paragraph]
                current_size = len(paragraph)
            else:
                current_chunk.append(paragraph)
                current_size += len(paragraph)
    
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    
    return chunks

# AGGIUNGIAMO I TEST SPECIFICI DA FINE-TUNE-DMBDZ-TO-HP.PY
print("\n=== TEST SPECIFICI DEL MODELLO ===")

test_locations = [
    ("Hogwarts", "Questa è una scuola di magia"),
    ("Londra", "La capitale dell'Inghilterra"),
    ("Grifondoro", "Una delle quattro case di Hogwarts"),
    ("Sala Grande", "Il luogo dove i maghi mangiano a Hogwarts"),
    ("Harry", "Il protagonista della storia"),
    # Aggiungiamo altri esempi interessanti
    ("Ministero della Magia", "Un edificio governativo per maghi"),
    ("La Tana", "La casa dei Weasley"),
    ("Foresta Proibita", "Un bosco pericoloso vicino a Hogwarts"),
    ("Azkaban", "La prigione dei maghi"),
    ("King's Cross", "Una stazione ferroviaria a Londra"),
    ("Platform 9¾", "Il binario magico a King's Cross"),
    ("Hogsmeade", "Un villaggio magico vicino a Hogwarts"),
    ("Diagon Alley", "Una strada magica con negozi"),
    ("Gringotts", "La banca dei maghi"),
    ("Pozione Polisucco", "Una pozione che trasforma l'aspetto"),
    ("Silente", "Il preside di Hogwarts"),
    ("Mago", "Una persona con poteri magici"),
    ("Privet Drive", "al numero 4 di Privet Drive"),
]

print("Esecuzione test di classificazione...")
bert_model.eval()

test_results = []
for location, context in test_locations:
    result = classify_location(location, context)
    confidence_percentage = result["confidence"] * 100
    print(f"Location: {location:<20} - Categoria: {result['category']:<20} - Confidenza: {confidence_percentage:.2f}%")
    test_results.append((location, result["category"], result["confidence"]))

print("\nEsecuzione di test aggiuntivi con diversi contesti...")

# Test con contesti variabili per verificare la sensibilità al contesto
context_test_locations = [
    ("Londra", "Si trova in Harry Potter", "città"),
    ("Londra", "È la città dove si trova King's Cross", "città"),
    ("Hogwarts", "È una scuola in Harry Potter", "scuola"),
    ("Hogwarts", "È il castello dove studiano i maghi", "castello"),
    ("Harry", "È un personaggio in Harry Potter", "non_luogo"),
    ("Harry", "È un posto dove va Harry Potter", "luogo"),
    ("Sala Grande", "È una stanza di Hogwarts", "sala"),
    ("Sala Grande", "È dove si svolgono i banchetti", "edificio")
]

for location, context, expected in context_test_locations:
    result = classify_location(location, context)
    confidence_percentage = result["confidence"] * 100
    match = "✓" if result["category"] == expected else "✗"
    print(f"Location: {location:<15} - Contesto: {context:<35} - Predetto: {result['category']:<15} - Atteso: {expected:<15} - {match} ({confidence_percentage:.2f}%)")

# Aggiungi questa funzione per eseguire il NER
def analyze_with_bert_ner(text):
    """Analizza il testo con il modello BERT NER italiano."""
    if ner_pipeline is None:
        return []
    
    try:
        # Esegui il NER
        results = ner_pipeline(text)
        return results
    except Exception as e:
        print(f"Errore nell'analisi NER: {e}")
        return []

# Modifica la sezione di test per aggiungere il confronto
print("\n=== CONFRONTO TRA MODELLI ===")
test_phrases = [
    "Hogwarts è una scuola di magia in Scozia.",
    "Harry Potter vive al numero 4 di Privet Drive.",
    "La Foresta Proibita è un luogo pericoloso vicino a Hogwarts.",
    "Silente è il preside della Scuola di Magia e Stregoneria di Hogwarts.",
    "La famiglia Weasley vive nella Tana, una casa storta.",
    "Il Ministero della Magia ha sede a Londra.",
    "Gringott è la banca dei maghi gestita dai goblin.",
]

for phrase in test_phrases:
    spacy_doc = nlp(phrase)
    bert_ner_results = analyze_with_bert_ner(phrase)
    
    print(f"\nFrase: {phrase}")
    print("Risultati spaCy:")
    for ent in spacy_doc.ents:
        print(f"  - {ent.text} ({ent.label_})")
    
    print("Risultati BERT NER:")
    for ent in bert_ner_results:
        print(f"  - {ent['word']} ({ent['entity_group']})")

"""
# Apre il file PDF e legge il testo
print("\n=== ANALISI DEL DOCUMENTO ===")
print("Lettura file...")
file_path = "C:/Users/Maurizio/Desktop/progettotesi/libri/capitolo1.txt"
with open(file_path, "r", encoding="utf-8") as file:
    text = file.read()
book_name = file_path.split("/")[-1].split(".")[0]

# Divide il testo in chunk e processa con spaCy
print("Analisi del testo con spaCy...")
entities_counter = Counter()
locations = {}

chunks = process_text_in_chunks(text)
total_chunks = len(chunks)

for i, chunk in enumerate(chunks):
    print(f"Elaborazione chunk {i+1}/{total_chunks}...")
    doc = nlp(chunk)
    
    # Estrai entità
    for ent in doc.ents:
        entities_counter[(ent.text, ent.label_)] += 1
        
        # Se è un luogo (LOC), MISC o PER, preparalo per la classificazione
        # Consideriamo tutte le entità come potenziali luoghi per BERT
        if ent.text not in locations:
            locations[ent.text] = {
                "count": 0,
                "label": ent.label_
            }
        locations[ent.text]["count"] += 1

# Classifica i luoghi trovati
print("Classificazione dei luoghi...")
classified_locations = {}

for location, data in locations.items():
    classification = classify_location(location, f"Questa entità si trova nel libro {book_name}")
    classified_locations[location] = {
        "category": classification["category"],
        "count": data["count"],
        "confidence": classification["confidence"],
        "spacy_label": data["label"]
    }

# Scrive risultati in un file
output_file = "spacy_bert_locations.txt"
print(f"Scrittura risultati in {output_file}...")

with open(output_file, "w", encoding="utf-8") as f:
    # Prima sezione: statistiche generali
    f.write("=== STATISTICHE GENERALI ===\n")
    total_entities = sum(entities_counter.values())
    f.write(f"Totale entità riconosciute: {total_entities}\n")
    
    per_count = sum(1 for (_, label), _ in entities_counter.items() if label == "PER")
    loc_count = sum(1 for (_, label), _ in entities_counter.items() if label == "LOC")
    org_count = sum(1 for (_, label), _ in entities_counter.items() if label == "ORG")
    misc_count = sum(1 for (_, label), _ in entities_counter.items() if label == "MISC")
    
    f.write(f"Persone (PER): {per_count}\n")
    f.write(f"Luoghi (LOC): {loc_count}\n")
    f.write(f"Organizzazioni (ORG): {org_count}\n")
    f.write(f"Miscellanea (MISC): {misc_count}\n\n")
    
    # Seconda sezione: luoghi classificati
    f.write("=== LUOGHI CLASSIFICATI ===\n")
    
    # Ordina i luoghi per conteggio, dal più frequente al meno frequente
    sorted_locations = sorted(classified_locations.items(), key=lambda x: x[1]['count'], reverse=True)
    
    for location, data in sorted_locations:
        f.write(f"{location} ({data['spacy_label']}): {data['category']} - {data['count']} occorrenze - {data['confidence']:.4f} confidenza\n")
    
    # Terza sezione: tutte le entità riconosciute da spaCy
    f.write("\n=== TUTTE LE ENTITÀ (spaCy) ===\n")
    
    # Raggruppa per tipo di entità
    grouped = {}
    for (text, label), count in entities_counter.items():
        if label not in grouped:
            grouped[label] = []
        grouped[label].append((text, count))
    
    # Scrive per ogni tipo
    for label, entities in grouped.items():
        f.write(f"\n--- {label} ---\n")
        # Ordina per conteggio
        for text, count in sorted(entities, key=lambda x: x[1], reverse=True)[:50]:  # Limita a 50 per tipo
            f.write(f"{text}: {count}\n")
    
    # Quarta sezione: risultati dei test specifici
    f.write("\n=== RISULTATI DEI TEST SPECIFICI ===\n")
    for location, category, confidence in test_results:
        f.write(f"{location}: {category} ({confidence:.4f})\n")

print(f"Analisi completata! I risultati sono disponibili nel file '{output_file}'")
"""