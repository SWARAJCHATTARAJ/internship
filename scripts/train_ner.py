import os
import spacy
from spacy.training.example import Example
from spacy.matcher import PhraseMatcher
import random
import sys

# Add root project to sys.path to import tools
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.data_loader import DataLoader

DATASET_PATH = os.path.join(os.path.dirname(__file__), '..', 'dataset')
MODEL_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'models', 'custom_medical_ner')

# Enable GPU Acceleration
is_using_gpu = spacy.prefer_gpu()
if is_using_gpu:
    print("[GPU] GPU acceleration enabled!")
else:
    print("[WARNING] No compatible GPU found by SpaCy. Falling back to CPU. (Make sure CUDA toolkit and cupy are installed!)")

# 1. We start with a blank spacy model for fast, local execution
print("Initializing blank English model...")
nlp = spacy.blank("en")

# We use PhraseMatcher for "Weak Supervision"
print("Setting up weak-supervision dictionaries...")
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
medications = ["metformin", "aspirin", "ibuprofen", "lisinopril", "amoxicillin", "atorvastatin"]
diagnoses = ["diabetes", "hypertension", "sepsis", "heart failure", "fracture", "urosepsis", "headache", "fever", "congestive heart failure"]

for m in medications:
    matcher.add("MEDICATION", [nlp.make_doc(m)])
for d in diagnoses:
    matcher.add("DIAGNOSIS", [nlp.make_doc(d)])

print(f"Loading ALL datasets from directory: {DATASET_PATH} ...")
print("[WARNING] This might take several hours on a CPU!")
loader = DataLoader(DATASET_PATH)

training_texts = []
for idx, report in enumerate(loader.stream_reports(chunk_size=1000)):
    if report["text"] and len(report["text"]) > 10:
        training_texts.append(report["text"])
        
    if idx % 10000 == 0 and idx > 0:
        print(f"...Loaded {idx} records so far...")

print(f"Extracted {len(training_texts)} text snippets. Auto-labeling now...")
train_data = []

# Generate Weak Supervision Labels
for text in training_texts:
    doc = nlp.make_doc(text)
    matches = matcher(doc)
    
    # We must ensure no overlapping spans. The PhraseMatcher can sometimes match overlapping words.
    # Spacy's filter_spans resolves this.
    spans = [doc[start:end] for match_id, start, end in matches]
    filtered_spans = spacy.util.filter_spans(spans)
    
    entities = []
    for span in filtered_spans:
        label = nlp.vocab.strings[matcher(nlp.make_doc(span.text))[0][0]] # get back the rule ID (e.g. MEDICATION)
        entities.append((span.start_char, span.end_char, label))
        
    if entities:
        train_data.append((text, {"entities": entities}))

print(f"Generated {len(train_data)} labeled examples for training!")

# 2. Add the NER component to our blank model
if "ner" not in nlp.pipe_names:
    ner = nlp.add_pipe("ner")
else:
    ner = nlp.get_pipe("ner")

# Add the labels
ner.add_label("MEDICATION")
ner.add_label("DIAGNOSIS")

# 3. Train the Model!
print("Beginning Gradient Descent Training Loop...")
optimizer = nlp.initialize()

epochs = 5
for i in range(epochs):
    random.shuffle(train_data)
    losses = {}
    
    # Batch the examples
    batches = spacy.util.minibatch(train_data, size=spacy.util.compounding(4.0, 32.0, 1.001))
    
    for batch in batches:
        examples = []
        for text, annotations in batch:
            doc = nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            examples.append(example)
        
        # Update weights
        nlp.update(examples, sgd=optimizer, drop=0.35, losses=losses)
    
    print(f"Epoch {i+1}/{epochs} - Losses: {losses}")

# 4. Save to Disk
os.makedirs(os.path.dirname(MODEL_OUTPUT_DIR), exist_ok=True)
nlp.to_disk(MODEL_OUTPUT_DIR)
print(f"[SUCCESS] Training Complete! Model saved successfully to {MODEL_OUTPUT_DIR}")
