import json
import torch
from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
from torch.utils.data import Dataset
import pandas as pd
from sklearn.model_selection import train_test_split
from collections import Counter

# Classe per il dataset
class LocationTypeDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

# Funzione per preparare il dataset
def prepare_location_dataset():
    # Carica i dati dai file JSON
    with open("output_locations/dataset/locations_for_manual_review_edited.json", 'r', encoding='utf-8') as f:
        manual_review = json.load(f)
    
    with open("output_locations/dataset/locations_uncertain_edited.json", 'r', encoding='utf-8') as f:
        uncertain = json.load(f)
    
    with open("output_locations/dataset/HP-Dataset-Finetune-Numeric_locations_edited.json", 'r', encoding='utf-8') as f:
        hp = json.load(f)
    
    # Combina i dati e crea un DataFrame
    data = []
    
    # Aggiungi esempi manuali per luoghi noti
    known_places = {
        "Londra": "città",
        "Hogwarts": "scuola di magia",
        "Hogsmeade": "villaggio magico",
        "Diagon Alley": "strada",
        "Tana": "casa",
        "Torre di Grifondoro": "torre",
        "Sala Grande": "sala",
        "Egitto": "paese",
        "Romania": "paese",
        "Albania": "paese",
        "Francia": "paese",
        "Germania": "paese"
    }
    
    for place, category in known_places.items():
        data.append({
            "location": place,
            "context": f"Questa location è {place} e si trova in Harry Potter",
            "category": category
        })
        # Aggiungi più esempi per bilanciare il dataset
        if category != "non_luogo":
            for i in range(5):  # Aggiungi ogni luogo 5 volte
                data.append({
                    "location": place,
                    "context": f"La location {place} è menzionata nel capitolo {i+1}",
                    "category": category
                })

    for loc_name, loc_data in manual_review.items():
        if "category" in loc_data.get("categorization", {}):
            category = loc_data["categorization"]["category"]
            context = f"Questa location si trova in Harry Potter"
            
            # Aggiunta di contesti più specifici e informativi
            if "wikipedia_info" in loc_data and loc_data["wikipedia_info"].get("found", False):
                context = loc_data["wikipedia_info"].get("snippet", context)
            
            data.append({
                "location": loc_name,
                "context": context,
                "category": category
            })
    
    for loc_name, loc_data in uncertain.items():
        if "category" in loc_data.get("categorization", {}):
            category = loc_data["categorization"]["category"]
            context = f"Questa location si trova in Harry Potter"
            
            # Aggiunta di contesti più specifici e informativi
            if "wikipedia_info" in loc_data and loc_data["wikipedia_info"].get("found", False):
                context = loc_data["wikipedia_info"].get("snippet", context)
            
            data.append({
                "location": loc_name,
                "context": context,
                "category": category
            })

    for loc_name, loc_data in hp.items():
        if "category" in loc_data.get("categorization", {}):
            category = loc_data["categorization"]["category"]
            context = f"Questa location si trova in Harry Potter"
            
            # Aggiunta di contesti più specifici e informativi
            if "wikipedia_info" in loc_data and loc_data["wikipedia_info"].get("found", False):
                context = loc_data["wikipedia_info"].get("snippet", context)
            
            data.append({
                "location": loc_name,
                "context": context,
                "category": category
            })

    
    df = pd.DataFrame(data)
    
    # Verifica ed equilibra le classi
    class_counts = df['category'].value_counts()
    print("Distribuzione delle classi prima del bilanciamento:")
    print(class_counts)

    # Rimuovi le categorie con un solo esempio
    # Questo evita errori nella stratificazione
    rare_categories = class_counts[class_counts < 2].index.tolist()
    if rare_categories:
        print(f"Rimozione di categorie con un solo esempio: {rare_categories}")
        df = df[~df['category'].isin(rare_categories)]
    
    # Mappa le categorie a numeri interi
    categories = df['category'].unique()
    category_to_id = {category: idx for idx, category in enumerate(categories)}
    id_to_category = {idx: category for category, idx in category_to_id.items()}
    
    # Converte le categorie in ID
    df['category_id'] = df['category'].map(category_to_id)
    
    # Suddivide in train e validation (stratificato per mantenere la proporzione delle classi)
    # Usa try-except per gestire il caso in cui ci siano ancora problemi con la stratificazione
    try:
        train_df, val_df = train_test_split(df, test_size=0.2, stratify=df['category'])
    except ValueError as e:
        print(f"Errore nella stratificazione: {e}")
        print("Eseguendo split senza stratificazione")
        train_df, val_df = train_test_split(df, test_size=0.2, random_state=42)
    
    print("\nDistribuzione delle classi dopo la divisione train/validation:")
    print("Train set:", Counter(train_df['category']))
    print("Validation set:", Counter(val_df['category']))
    
    return train_df, val_df, category_to_id, id_to_category

# Calcola pesi per il bilanciamento delle classi
def calculate_class_weights(labels):
    class_counts = Counter(labels)
    total = len(labels)
    class_weights = {cls: total / count for cls, count in class_counts.items()}
    return class_weights

# Prepara il dataset
train_df, val_df, category_to_id, id_to_category = prepare_location_dataset()

# Carica il tokenizer e tokenizza i dati
tokenizer = BertTokenizer.from_pretrained("dbmdz/bert-base-italian-xxl-cased")

# Prepara i dati di input per il modello
train_encodings = tokenizer(
    train_df['location'].tolist(),
    train_df['context'].tolist(),
    truncation=True,
    padding=True,
    max_length=128
)

val_encodings = tokenizer(
    val_df['location'].tolist(),
    val_df['context'].tolist(),
    truncation=True,
    padding=True,
    max_length=128
)

# Calcola i pesi delle classi per l'addestramento bilanciato
train_labels = train_df['category_id'].tolist()
class_weights = calculate_class_weights(train_labels)

# Crea i dataset per il training
train_dataset = LocationTypeDataset(train_encodings, train_df['category_id'].tolist())
val_dataset = LocationTypeDataset(val_encodings, val_df['category_id'].tolist())

# Carica il modello con class_weights
model = BertForSequenceClassification.from_pretrained(
    "dbmdz/bert-base-italian-xxl-cased",
    num_labels=len(category_to_id)
)

# Configura il training con strategie per dataset sbilanciati
training_args = TrainingArguments(
    output_dir="./bert_location_classifier",
    num_train_epochs=10,  # Aumentato il numero di epoche
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    warmup_steps=500,
    weight_decay=0.01,
    logging_dir="./logs",
    logging_steps=10,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    learning_rate=2e-5,  # Un learning rate leggermente più basso
)

# Definizione della classe Trainer personalizzata che supporta i pesi delle classi
class CustomTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        
        # Ricreare i pesi per il loss
        device = logits.device
        class_weights_tensor = torch.tensor([class_weights[i] for i in range(len(category_to_id))], device=device)
        
        # Cross-entropy loss con pesi
        loss_fct = torch.nn.CrossEntropyLoss(weight=class_weights_tensor)
        loss = loss_fct(logits.view(-1, model.config.num_labels), labels.view(-1))
        
        return (loss, outputs) if return_outputs else loss

# Crea il trainer e avvia il training
trainer = CustomTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
)

print("Inizio del training del modello...")
trainer.train()

# Salva il modello e il mapping delle categorie
model.save_pretrained("./bert_location_classifier")
tokenizer.save_pretrained("./bert_location_classifier")

with open("./bert_location_classifier/category_mapping.json", "w") as f:
    json.dump({
        "id_to_category": id_to_category, 
        "category_to_id": category_to_id,
        "class_weights": {str(k): v for k, v in class_weights.items()}
    }, f)

print("✅ Modello addestrato e salvato!")

# Test del modello su alcuni esempi
test_locations = [
    ("Hogwarts", "Questa è una scuola di magia"),
    ("Londra", "La capitale dell'Inghilterra"),
    ("Grifondoro", "Una delle quattro case di Hogwarts"),
    ("Sala Grande", "Il luogo dove i maghi mangiano a Hogwarts"),
    ("Harry", "Il protagonista della storia"),
    ("privet drive", "Numero 4 di Privet Drive")
]

model.eval()
for location, context in test_locations:
    inputs = tokenizer(location, context, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    
    predicted_class_id = outputs.logits.argmax().item()
    predicted_category = id_to_category[predicted_class_id]
    print(f"Location: {location} - Categoria predetta: {predicted_category}")