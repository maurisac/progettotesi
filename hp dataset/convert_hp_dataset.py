import json

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

# Caricamento del dataset HP-Dataset-Finetune.json
file_path = "HP-Dataset-Finetune.json"
with open(file_path, "r", encoding="utf-8") as f:
    json_dataset = json.load(f)

# Pulisce e converte i set di dati
cleaned_train = clean_dataset(json_dataset["train"])
cleaned_validation = clean_dataset(json_dataset["validation"])
cleaned_test = clean_dataset(json_dataset["test"])

check_unicode_ambiguity(cleaned_train)
check_unicode_ambiguity(cleaned_validation)
check_unicode_ambiguity(cleaned_test)

numeric_train = convert_labels_to_int(cleaned_train)
numeric_validation = convert_labels_to_int(cleaned_validation)
numeric_test = convert_labels_to_int(cleaned_test)

# Salva i set di dati convertiti
numeric_dataset = {
    "train": numeric_train,
    "validation": numeric_validation,
    "test": numeric_test
}

numeric_file_path = "HP-Dataset-Finetune-Numeric.json"
with open(numeric_file_path, "w", encoding="utf-8") as f:
    json.dump(numeric_dataset, f, indent=4, ensure_ascii=False)

print(f"✅ Dataset convertito e salvato in {numeric_file_path}")