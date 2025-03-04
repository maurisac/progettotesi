import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class LocationEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Location Editor")
        self.root.geometry("1200x700")
        
        # Variabili per tenere traccia dei dati
        self.locations_data = {}
        self.current_location = None
        self.location_keys = []
        self.current_index = 0
        self.modified = set()  # Tiene traccia delle location modificate
        self.output_file = None
        
        # Dizionario con le modifiche
        self.edited_data = {}
        
        # Flag per mostrare solo location non modificate manualmente
        self.show_unedited_only = tk.BooleanVar(value=True)
        
        # Flag per avanzare automaticamente alla prossima location
        self.auto_advance = tk.BooleanVar(value=False)
        
        # Tieni traccia del formato del file: "standard" o "hp_dataset"
        self.file_format = "standard"
        
        # Inizializza l'interfaccia
        self.create_ui()
        
        # Binding per i tasti freccia
        self.root.bind('<Left>', lambda event: self.prev_location())
        self.root.bind('<Right>', lambda event: self.next_location())
        self.root.bind('<Up>', lambda event: self.mark_not_place())
    
    def create_ui(self):
        # Frame principale diviso in due colonne
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Colonna sinistra: informazioni sulla location
        left_frame = ttk.LabelFrame(main_frame, text="Informazioni Location", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Colonna destra: categorizzazione
        right_frame = ttk.LabelFrame(main_frame, text="Categorizzazione", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Informazioni sulla location
        self.location_info_frame = ttk.Frame(left_frame)
        self.location_info_frame.pack(fill=tk.BOTH, expand=True)
        
        # Nome location
        ttk.Label(self.location_info_frame, text="Nome Location:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.location_name = ttk.Label(self.location_info_frame, text="", font=("Arial", 12, "bold"))
        self.location_name.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Occorrenze
        ttk.Label(self.location_info_frame, text="Occorrenze Totali:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.location_occurrences = ttk.Label(self.location_info_frame, text="")
        self.location_occurrences.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Contesto (frase o libri in cui appare)
        ttk.Label(self.location_info_frame, text="Contesto:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.location_context = ttk.Label(self.location_info_frame, text="", wraplength=400)
        self.location_context.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Info Wikipedia
        ttk.Label(self.location_info_frame, text="Wikipedia:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.wiki_info = tk.Text(self.location_info_frame, height=10, width=50, wrap=tk.WORD)
        self.wiki_info.grid(row=3, column=1, sticky=tk.W+tk.E+tk.N+tk.S, pady=5)
        self.wiki_info.config(state=tk.DISABLED)
        
        # Categorie trovate
        ttk.Label(self.location_info_frame, text="Categoria Attuale:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.current_category = ttk.Label(self.location_info_frame, text="", font=("Arial", 11, "bold"))
        self.current_category.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Confidenza
        ttk.Label(self.location_info_frame, text="Confidenza:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.confidence = ttk.Label(self.location_info_frame, text="")
        self.confidence.grid(row=5, column=1, sticky=tk.W, pady=5)
        
        # Checkbox per mostrare solo location non modificate manualmente
        self.filter_check = ttk.Checkbutton(
            self.location_info_frame, 
            text="Mostra solo location non modificate manualmente", 
            variable=self.show_unedited_only,
            command=self.apply_filter
        )
        self.filter_check.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Checkbox per avanzare automaticamente
        self.advance_check = ttk.Checkbutton(
            self.location_info_frame, 
            text="Avanza automaticamente alla prossima location dopo la scelta", 
            variable=self.auto_advance
        )
        self.advance_check.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Shortcut info
        shortcut_frame = ttk.LabelFrame(self.location_info_frame, text="Scorciatoie tastiera")
        shortcut_frame.grid(row=8, column=0, columnspan=2, sticky=tk.W+tk.E, pady=10)
        ttk.Label(shortcut_frame, text="← Precedente").pack(side=tk.LEFT, padx=10)
        ttk.Label(shortcut_frame, text="→ Successiva").pack(side=tk.LEFT, padx=10)
        ttk.Label(shortcut_frame, text="↑ Segna come NON LUOGO").pack(side=tk.LEFT, padx=10)
        
        # Categorie disponibili
        self.category_frame = ttk.Frame(right_frame)
        self.category_frame.pack(fill=tk.BOTH, expand=True)
        
        # Etichetta per la sezione delle categorie
        ttk.Label(self.category_frame, text="Seleziona la categoria corretta:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # Creiamo uno scrollable frame per le categorie
        # Contenitore per il canvas e la scrollbar
        scrollable_container = ttk.Frame(self.category_frame)
        scrollable_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas che conterrà i pulsanti
        self.canvas = tk.Canvas(scrollable_container)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar verticale
        scrollbar = ttk.Scrollbar(scrollable_container, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Collega la scrollbar al canvas
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Frame interno per i pulsanti delle categorie
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Crea finestra nel canvas che contiene il frame
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configura il canvas per scrollare con la rotellina del mouse
        self.canvas.bind_all("<MouseWheel>", lambda event: self.canvas.yview_scroll(int(-1*(event.delta/120)), "units"))
        
        # Aggiorna la regione scrollabile quando cambia la dimensione del frame interno
        self.scrollable_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Pulsante NON È UN LUOGO posizionato in alto e in evidenza
        not_place_frame = ttk.Frame(self.scrollable_frame)
        not_place_frame.pack(fill=tk.X, pady=5)
        
        not_place_btn = ttk.Button(
            not_place_frame, 
            text="NON È UN LUOGO (↑)", 
            style="NotPlace.TButton",
            command=self.mark_not_place
        )
        not_place_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Style per il pulsante NON È UN LUOGO
        style = ttk.Style()
        style.configure("NotPlace.TButton", font=("Arial", 11, "bold"), background="red")
        
        # Categorie di luoghi predefinite
        self.categories = [
            "città", "paese", "villaggio", "castello", "palazzo", "scuola", "casa", 
            "università", "montagna", "lago", "fiume", "mare", "oceano", "sala",
            "foresta", "bosco", "parco", "piazza", "strada", "edificio", "veicolo",
            "chiesa", "cattedrale", "tempio", "ristorante", "hotel", "negozio", 
            "teatro", "cinema", "museo", "biblioteca", "ospedale", "stazione", "libreria",
            "aeroporto", "porto", "isola", "spiaggia", "deserto", "giardino",
            "taverna", "bar", "caffetteria", "discoteca", "pub", "centro commerciale",
            "supermercato", "mercato", "fattoria", "mulino", "miniera", "fortezza", 
            "accademia", "osservatorio", "laboratorio", "bunker", "caserma", "prigione", 
            "manicomio", "cimitero", "stadio", "arena", "campo da battaglia", 
            "base militare", "monastero", "santuario", "oasi", "ghiacciaio", 
            "vulcano", "grotta", "gola", "cascata", "baia", "diga", "faro", 
            "nave pirata", "sommergibile", "dirigibile", "spazioporto",
            "stazione spaziale", "pianeta alieno", "dimensione parallela", "regno sommerso", 
            "città volante", "labirinto", "castello incantato", "foresta oscura", 
            "tempio sommerso", "villaggio maledetto", "biblioteca proibita", "terreno naturale"
        ]
        
        # Aggiungiamo le categorie del mondo di Harry Potter
        harry_potter_categories = [
            "scuola di magia", "villaggio magico", "luogo magico", "negozio magico",
            "edificio magico", "stazione magica", "foresta magica", "lago magico",
            "passaggio segreto", "stanza segreta", "ospedale magico", "carcere magico",
            "stadio magico", "ministero", "banca magica", "sala magica", "pub magico", "veicolo magico",
            "torre", "sotterraneo", "dormitorio", "aula", "ufficio", "campo", "tana", "capanna"
        ]
        
        self.categories.extend(harry_potter_categories)
        self.categories.sort()
        
        # Bottoni per ogni categoria
        self.category_buttons = {}
        
        for i, category in enumerate(self.categories):
            frame = ttk.Frame(self.scrollable_frame)
            frame.pack(fill=tk.X, pady=2)
            
            # Bottoni per prima, seconda e terza scelta
            self.category_buttons[category] = []
            
            # Label categoria
            ttk.Label(frame, text=category, width=20).pack(side=tk.LEFT, padx=(0, 10))
            
            # Bottoni scelta
            btn1 = ttk.Button(frame, text="Prima scelta", 
                             command=lambda cat=category: self.set_category(cat, 0.9))
            btn1.pack(side=tk.LEFT, padx=5)
            self.category_buttons[category].append(btn1)
            
            btn2 = ttk.Button(frame, text="Seconda scelta", 
                             command=lambda cat=category: self.set_category(cat, 0.6))
            btn2.pack(side=tk.LEFT, padx=5)
            self.category_buttons[category].append(btn2)
            
            btn3 = ttk.Button(frame, text="Terza scelta", 
                             command=lambda cat=category: self.set_category(cat, 0.3))
            btn3.pack(side=tk.LEFT, padx=5)
            self.category_buttons[category].append(btn3)
        
        # Barra di navigazione inferiore
        nav_frame = ttk.Frame(self.root, padding=10)
        nav_frame.pack(fill=tk.X)
        
        # Contatore locazioni
        self.counter_label = ttk.Label(nav_frame, text="0/0 location")
        self.counter_label.pack(side=tk.LEFT, padx=10)
        
        # Contatore delle location non modificate manualmente
        self.unedited_counter = ttk.Label(nav_frame, text="(0 da revisionare)")
        self.unedited_counter.pack(side=tk.LEFT, padx=10)
        
        # Progress bar
        self.progress = ttk.Progressbar(nav_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Bottoni di navigazione
        button_frame = ttk.Frame(nav_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.load_standard_btn = ttk.Button(button_frame, text="Carica Standard", command=self.load_standard_data)
        self.load_standard_btn.pack(side=tk.LEFT, padx=5)
        
        self.load_hp_btn = ttk.Button(button_frame, text="Carica HP Dataset", command=self.load_hp_dataset)
        self.load_hp_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Precedente", command=self.prev_location).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Successiva", command=self.next_location).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Salva Modifiche", command=self.save_changes).pack(side=tk.LEFT, padx=5)
    
    def mark_not_place(self):
        """Scorciatoia per marcare una location come NON LUOGO"""
        self.set_category("non_luogo", 1.0)
    
    def is_location_edited(self, loc_key):
        """Controlla se una location è già stata modificata manualmente"""
        return loc_key in self.edited_data
    
    def apply_filter(self):
        """Applica il filtro per mostrare solo location non modificate manualmente"""
        if not self.locations_data:
            return
        
        # Ricostruisci la lista delle chiavi in base al filtro
        if self.show_unedited_only.get():
            # Mostra solo location non modificate manualmente
            self.location_keys = [key for key in self.locations_data.keys() 
                                 if not self.is_location_edited(key)]
        else:
            # Mostra tutte le location
            self.location_keys = list(self.locations_data.keys())
        
        # Aggiorna i contatori
        self.update_counters()
        
        # Resetta l'indice e mostra la prima location
        if self.location_keys:
            self.current_index = 0
            self.show_current_location()
        else:
            # Se non ci sono location da mostrare
            self.clear_location_info()
            messagebox.showinfo("Info", "Nessuna location da mostrare con il filtro corrente")
    
    def clear_location_info(self):
        """Pulisce i campi informativi quando non ci sono location da mostrare"""
        self.location_name.config(text="")
        self.location_occurrences.config(text="")
        self.location_context.config(text="")
        self.wiki_info.config(state=tk.NORMAL)
        self.wiki_info.delete(1.0, tk.END)
        self.wiki_info.config(state=tk.DISABLED)
        self.current_category.config(text="")
        self.confidence.config(text="")
    
    def update_counters(self):
        """Aggiorna i contatori delle location"""
        total_locations = len(self.locations_data)
        edited = len(self.edited_data)
        unedited = total_locations - edited
        
        self.unedited_counter.config(text=f"({unedited} da revisionare)")
        
        if self.location_keys:
            self.counter_label.config(text=f"{self.current_index + 1}/{len(self.location_keys)} location")
            self.progress['maximum'] = len(self.location_keys)
            self.progress['value'] = self.current_index + 1
        else:
            self.counter_label.config(text="0/0 location")
            self.progress['maximum'] = 1
            self.progress['value'] = 0
    
    def load_standard_data(self):
        """Carica dataset in formato standard (locations_for_manual_review_edited.json)"""
        file_path = filedialog.askopenfilename(
            title="Seleziona il file JSON con le location",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.locations_data = json.load(f)
            
            self.file_format = "standard"
            
            # Crea il nome del file di output
            dirname, filename = os.path.split(file_path)
            base_filename, ext = os.path.splitext(filename)
            self.output_file = os.path.join(dirname, f"{base_filename}_edited{ext}")
            
            # Carica i dati già modificati se esistono
            self.load_edited_data()
            
            # Applica il filtro per mostrare solo location non modificate manualmente
            self.apply_filter()
            
            if self.location_keys:
                messagebox.showinfo("Successo", f"Caricate {len(self.locations_data)} location totali, {len(self.location_keys)} da revisionare")
            else:
                messagebox.showinfo("Info", "Nessuna location da revisionare. Tutte le location sono già state modificate manualmente.")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare il file: {str(e)}")
    
    def load_hp_dataset(self):
        """Carica dataset in formato HP-Dataset-finetune.json"""
        file_path = filedialog.askopenfilename(
            title="Seleziona il file JSON del dataset HP",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                hp_data = json.load(f)
            
            self.file_format = "hp_dataset"
            
            # Estrai tutte le location dai dati di addestramento
            self.locations_data = {}
            
            # Processa train, validation e test
            for section in ['train', 'validation', 'test']:
                if section in hp_data:
                    for example in hp_data[section]:
                        tokens = example.get("tokens", [])
                        ner_tags = example.get("ner_tags", [])
                        
                        if not tokens or not ner_tags or len(tokens) != len(ner_tags):
                            continue
                        
                        # Ottieni la frase originale
                        sentence = " ".join(tokens)
                        
                        # Estrai le location
                        i = 0
                        while i < len(tokens):
                            # Se è una location (tag B-LOC o numerici 1 per B-LOC)
                            if (isinstance(ner_tags[i], str) and ner_tags[i] in ["B-LOC", "B-ORG"]) or \
                               (isinstance(ner_tags[i], int) and ner_tags[i] in [1, 5]):
                                
                                # Crea la location con contesto
                                location = tokens[i]
                                start_idx = i
                                i += 1
                                
                                # Se ci sono tag I-LOC successivi, aggiungi anche quelli
                                while i < len(ner_tags) and \
                                     ((isinstance(ner_tags[i], str) and ner_tags[i] in ["I-LOC", "I-ORG"]) or \
                                      (isinstance(ner_tags[i], int) and ner_tags[i] in [2, 6])):
                                    location += " " + tokens[i]
                                    i += 1
                                
                                # Aggiungi questa location al dizionario
                                if location not in self.locations_data:
                                    self.locations_data[location] = {
                                        "location": location,
                                        "occurrences": 0,
                                        "sentences": [],
                                        "categorization": {
                                            "category": "sconosciuto",
                                            "confidence": 0.0
                                        }
                                    }
                                
                                self.locations_data[location]["occurrences"] += 1
                                
                                # Aggiungi la frase al contesto
                                if sentence not in self.locations_data[location]["sentences"]:
                                    self.locations_data[location]["sentences"].append(sentence)
                            else:
                                i += 1
            
            # Crea il nome del file di output
            dirname, filename = os.path.split(file_path)
            base_filename, ext = os.path.splitext(filename)
            self.output_file = os.path.join(dirname, f"{base_filename}_locations_edited{ext}")
            
            # Carica i dati già modificati se esistono
            self.load_edited_data()
            
            # Applica il filtro per mostrare solo location non modificate manualmente
            self.apply_filter()
            
            if self.location_keys:
                messagebox.showinfo("Successo", f"Caricate {len(self.locations_data)} location totali dal dataset HP, {len(self.location_keys)} da revisionare")
            else:
                messagebox.showinfo("Info", "Nessuna location da revisionare. Tutte le location sono già state modificate manualmente.")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare il file HP dataset: {str(e)}")
    
    def load_edited_data(self):
        """Carica i dati già modificati se esistono"""
        if not self.output_file or not os.path.exists(self.output_file):
            self.edited_data = {}
            return
            
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                self.edited_data = json.load(f)
            messagebox.showinfo("Info", f"Caricate {len(self.edited_data)} location già modificate")
        except Exception as e:
            messagebox.showwarning("Attenzione", f"Impossibile caricare le modifiche precedenti: {str(e)}")
            self.edited_data = {}
    
    def show_current_location(self):
        if not self.location_keys:
            self.clear_location_info()
            return
        
        # Ottieni la chiave della location corrente
        loc_key = self.location_keys[self.current_index]
        self.current_location = loc_key
        
        # Ottieni i dati della location
        loc_data = self.locations_data[loc_key]
        
        # Aggiorna le informazioni visualizzate
        self.location_name.config(text=loc_key)
        self.location_occurrences.config(text=str(loc_data.get('occurrences', 'N/A')))
        
        # Visualizza il contesto in base al formato
        if self.file_format == "standard":
            # Formatta i libri
            books_text = ""
            for book in loc_data.get('books', []):
                if isinstance(book, dict) and 'name' in book and 'occurrences' in book:
                    books_text += f"{book['name']} ({book['occurrences']} occorrenze)\n"
                elif isinstance(book, dict) and 'occurrences' in book:
                    books_text += f"Libro non specificato ({book['occurrences']} occorrenze)\n"
            self.location_context.config(text=books_text)
            
            # Informazioni Wikipedia
            self.wiki_info.config(state=tk.NORMAL)
            self.wiki_info.delete(1.0, tk.END)
            wiki_info = loc_data.get('wikipedia_info', {})
            if wiki_info.get('found', False):
                wiki_text = f"Titolo: {wiki_info.get('title', '')}\n\n"
                wiki_text += wiki_info.get('snippet', '')
                self.wiki_info.insert(tk.END, wiki_text)
            else:
                self.wiki_info.insert(tk.END, "Nessuna informazione trovata su Wikipedia")
            self.wiki_info.config(state=tk.DISABLED)
        else:  # hp_dataset
            # Mostra le frasi di esempio
            sentences = loc_data.get('sentences', [])
            context_text = "\n\n".join(sentences[:3])  # Mostra max 3 frasi
            self.location_context.config(text=context_text)
            
            # Nessuna info Wikipedia per questo formato
            self.wiki_info.config(state=tk.NORMAL)
            self.wiki_info.delete(1.0, tk.END)
            self.wiki_info.insert(tk.END, "Non disponibile per il formato dataset HP")
            self.wiki_info.config(state=tk.DISABLED)
        
        # Categoria attuale
        categorization = loc_data.get('categorization', {})
        category = categorization.get('category', 'N/A')
        confidence = categorization.get('confidence', 0)
        
        # Usa i dati modificati se disponibili
        if loc_key in self.edited_data:
            edited_categorization = self.edited_data[loc_key].get('categorization', {})
            category = edited_categorization.get('category', category)
            confidence = edited_categorization.get('confidence', confidence)
        
        self.current_category.config(text=category)
        self.confidence.config(text=f"{confidence:.2f}")
        
        # Aggiorna contatore e progress bar
        self.update_counters()
        
        # Evidenzia se questa location è stata modificata
        if loc_key in self.modified:
            self.location_name.config(foreground="green")
        else:
            self.location_name.config(foreground="black")
    
    def set_category(self, category, confidence):
        if not self.current_location:
            return
        
        # Caso speciale per "non_luogo"
        if category == "non_luogo":
            # Creiamo una nuova categorizzazione che indica che non è un luogo
            new_categorization = {
                "category": "non_luogo",
                "confidence": 1.0,
                "all_categories": [
                    {"label": "non_luogo", "score": 1.0}
                ]
            }
        else:
            # Per le altre categorie, creiamo una nuova categorizzazione 
            # che PRESERVA le precedenti scelte e permette categorizzazioni multiple
            old_data = self.locations_data[self.current_location]
            old_categorization = old_data.get('categorization', {})
            
            # Se esistono dati modificati, usa quelli
            if self.current_location in self.edited_data:
                old_categorization = self.edited_data[self.current_location].get('categorization', old_categorization)
                
            old_all_categories = old_categorization.get('all_categories', [])
            
            # Crea una nuova lista di categorie
            new_all_categories = []
            category_exists = False
            
            # Verifica se la categoria esiste già
            for cat_info in old_all_categories:
                if isinstance(cat_info, dict) and 'label' in cat_info:
                    if cat_info['label'] == category:
                        # Aggiorna solo la confidenza per categoria esistente
                        new_all_categories.append({"label": category, "score": confidence})
                        category_exists = True
                    else:
                        # Mantieni le altre categorie invariate
                        new_all_categories.append(cat_info)
            
            # Aggiungi la nuova categoria se non esisteva
            if not category_exists:
                new_all_categories.append({"label": category, "score": confidence})
            
            # Ordina per punteggio decrescente
            new_all_categories.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # Usa la categoria con il punteggio più alto come principale
            main_category = new_all_categories[0]['label'] if new_all_categories else category
            main_confidence = new_all_categories[0]['score'] if new_all_categories else confidence
            
            new_categorization = {
                "category": main_category,
                "confidence": main_confidence,
                "all_categories": new_all_categories
            }
        
        # Crea o aggiorna la voce nel dizionario edited_data
        if self.file_format == "standard":
            if self.current_location not in self.edited_data:
                # Copia solo i dati essenziali
                self.edited_data[self.current_location] = {
                    "location": self.current_location,
                    "occurrences": self.locations_data[self.current_location].get('occurrences', 0),
                    "books": self.locations_data[self.current_location].get('books', []),
                    "categorization": new_categorization
                }
                
                # Aggiungi anche le informazioni di Wikipedia se disponibili
                if 'wikipedia_info' in self.locations_data[self.current_location]:
                    self.edited_data[self.current_location]['wikipedia_info'] = self.locations_data[self.current_location]['wikipedia_info']
            else:
                # Aggiorna solo la categorizzazione
                self.edited_data[self.current_location]['categorization'] = new_categorization
        else:  # hp_dataset
            if self.current_location not in self.edited_data:
                # Copia solo i dati essenziali
                self.edited_data[self.current_location] = {
                    "location": self.current_location,
                    "occurrences": self.locations_data[self.current_location].get('occurrences', 0),
                    "sentences": self.locations_data[self.current_location].get('sentences', []),
                    "categorization": new_categorization
                }
            else:
                # Aggiorna solo la categorizzazione
                self.edited_data[self.current_location]['categorization'] = new_categorization
        
        # Aggiungi alla lista delle modificate
        self.modified.add(self.current_location)
        
        # Auto-salva dopo ogni modifica
        self.save_changes(auto=True)
        
        # Mostra la location aggiornata con le nuove categorie
        self.show_current_location()
        
        # IMPORTANTE: NON avanza automaticamente a meno che non sia esplicitamente richiesto
        # Questo permette di assegnare più categorie alla stessa location
        if self.auto_advance.get():
            self.next_location()
    
    def next_location(self):
        if not self.location_keys:
            return
        
        if self.current_index < len(self.location_keys) - 1:
            self.current_index += 1
            self.show_current_location()
    
    def prev_location(self):
        if not self.location_keys:
            return
        
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current_location()
    
    def save_changes(self, auto=False):
        if not self.output_file or not self.edited_data:
            if not auto:
                messagebox.showwarning("Attenzione", "Nessuna modifica da salvare o nessun file di output specificato")
            return
        
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.edited_data, f, ensure_ascii=False, indent=4)
            
            if not auto:
                messagebox.showinfo("Successo", f"Modifiche salvate in {self.output_file}")
        except Exception as e:
            if not auto:
                messagebox.showerror("Errore", f"Impossibile salvare le modifiche: {str(e)}")

    def on_frame_configure(self, event):
        """Aggiorna la regione scrollabile quando il frame interno cambia dimensione"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """Ridimensiona la finestra interna quando il canvas cambia dimensione"""
        width = event.width
        self.canvas.itemconfig(self.canvas_window, width=width)

def main():
    root = tk.Tk()
    app = LocationEditorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()