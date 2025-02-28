import json
from datasets import load_dataset

# Carica il dataset WikiANN in italiano
dataset = load_dataset("wikiann", "it")
file_path = "wikiann_it.json"

# Dizionario di mapping per convertire le etichette testuali in numeri
label_mapping = {
    "O": 0,
    "B-LOC": 1, "I-LOC": 2,
    "B-PER": 3, "I-PER": 4,
    "B-ORG": 5, "I-ORG": 6,
}

def convert_labels_to_int(data):
    """
    Converte i tag NER da stringhe a numeri usando il dizionario di mapping.
    """
    converted_data = []
    for item in data:
        tokens = item["tokens"]
        labels = [label_mapping[label] for label in item["ner_tags"]]  # Converte le etichette

        converted_data.append({
            "tokens": tokens,
            "ner_tags": labels
        })

    return converted_data

def clean_dataset(dataset):
    """
    Rimuove gli esempi vuoti o non validi dal dataset.
    """
    cleaned_data = []
    for item in dataset:
        if "tokens" in item and "ner_tags" in item and item["tokens"] and item["ner_tags"]:
            cleaned_data.append(item)
        else:
            print(f"Rimosso esempio non valido: {item}")
    return cleaned_data

def check_unicode_ambiguity(data):
    """
    Verifica la presenza di caratteri Unicode ambigui nel dataset.
    """
    for item in data:
        for token in item["tokens"]:
            if any(ord(char) > 127 for char in token):
                print(f"Carattere Unicode ambiguo trovato nel token: {token}")

with open(file_path, "r", encoding="utf-8") as f:
    json_dataset = json.load(f)

# Pulisce il dataset
json_dataset["train"] = clean_dataset(json_dataset["train"])
json_dataset["validation"] = clean_dataset(json_dataset["validation"])
json_dataset["test"] = clean_dataset(json_dataset["test"])

# Verifica la presenza di caratteri Unicode ambigui
check_unicode_ambiguity(json_dataset["train"])
check_unicode_ambiguity(json_dataset["validation"])
check_unicode_ambiguity(json_dataset["test"])

# Converte i dati
numeric_json_dataset = {
    "train": convert_labels_to_int(json_dataset["train"]),
    "validation": convert_labels_to_int(json_dataset["validation"]),
    "test": convert_labels_to_int(json_dataset["test"])
}

# Verifica la struttura del dataset
for split in numeric_json_dataset:
    for item in numeric_json_dataset[split]:
        if isinstance(item["tokens"][0], list) or isinstance(item["ner_tags"][0], list):
            print(f"Esempio con struttura errata trovato: {item}")

# Salva il dataset convertito
numeric_file_path = "wikiann_it_numeric.json"
with open(numeric_file_path, "w", encoding="utf-8") as f:
    json.dump(numeric_json_dataset, f, indent=4, ensure_ascii=False)

print(f"✅ Dataset convertito e salvato in {numeric_file_path}")
