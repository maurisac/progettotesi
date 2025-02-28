import json
import torch
from transformers import (
    BertTokenizerFast, BertForTokenClassification,
    TrainingArguments, Trainer, pipeline
)
from datasets import Dataset as HFDataset, DatasetDict

# 📂 1. Caricamento del Dataset JSON
file_path = "wikiann_it_numeric.json"
with open(file_path, "r", encoding="utf-8") as f:
    json_dataset = json.load(f)

# 📌 2. Conversione in Hugging Face Dataset
def convert_json_to_hf(dataset):
    return HFDataset.from_list(dataset)

hf_dataset = DatasetDict({
    "train": convert_json_to_hf(json_dataset["train"]),
    "validation": convert_json_to_hf(json_dataset["validation"]),
    "test": convert_json_to_hf(json_dataset["test"])
})

# 🔠 3. Tokenizzazione con BERT
MODEL_NAME = "dbmdz/bert-base-italian-cased"
tokenizer = BertTokenizerFast.from_pretrained(MODEL_NAME)

# Funzione per allineare etichette ai token di BERT
def align_labels_with_tokens(labels, word_ids):
    new_labels = []
    prev_word = None
    for word_id in word_ids:
        if word_id is None:
            new_labels.append(-100)  # Ignora token speciali
        elif word_id != prev_word:
            new_labels.append(labels[word_id])  # Primo token della parola
        else:
            new_labels.append(labels[word_id])  # Mantieni lo stesso tag per token spezzati
        prev_word = word_id
    return new_labels

# Tokenizzazione e allineamento delle etichette
def tokenize_and_align_labels(examples):
    tokenized_inputs = tokenizer(
        examples["tokens"], truncation=True, padding="max_length", max_length=128, is_split_into_words=True
    )
    word_ids = tokenized_inputs.word_ids()
    tokenized_inputs["labels"] = align_labels_with_tokens(examples["ner_tags"], word_ids)
    return tokenized_inputs

# Applicare la tokenizzazione al dataset
tokenized_dataset = hf_dataset.map(tokenize_and_align_labels)

# 🎯 4. Caricamento del modello BERT per NER
id2label = {0: "O", 1: "B-LOC", 2: "I-LOC", 3: "B-PER", 4: "I-PER", 5: "B-ORG", 6: "I-ORG"}
label2id = {v: k for k, v in id2label.items()}

model = BertForTokenClassification.from_pretrained(
    MODEL_NAME, num_labels=len(id2label), id2label=id2label, label2id=label2id
)

# 📌 5. Configurazione dei parametri di addestramento
training_args = TrainingArguments(
    output_dir="./bert_ner_results",
    evaluation_strategy="epoch",
    save_strategy="epoch",
    logging_strategy="epoch",
    learning_rate=5e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss"
)

# Creazione del Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["validation"],
    tokenizer=tokenizer
)

# 🚀 6. Avvio dell'addestramento
trainer.train()

# ✅ 7. Salvataggio del modello
trainer.save_model("./bert_ner_trained")
tokenizer.save_pretrained("./bert_ner_trained")
print("✅ Modello addestrato e salvato!")

# 🔍 8. Test del Modello
ner_pipeline = pipeline("ner", model="./bert_ner_trained", tokenizer="./bert_ner_trained")

# Frase di test
testo = "Harry Potter è nato a Londra e ha studiato a Hogwarts."

# Esegui il riconoscimento delle entità
risultati = ner_pipeline(testo)

print("📌 Risultati del NER:")
print(risultati)
