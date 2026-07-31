import os
import sys
import time
import random
import json
import pandas as pd
from typing import List, Dict, Any, Tuple
import spacy
# Enable GPU training for RTX 3050 if available, otherwise fallback to CPU
spacy.prefer_gpu()
from spacy.training.example import Example
from spacy.matcher import PhraseMatcher

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.data_loader import DataLoader
from schemas.core import ReportState
from agents.orchestrator import graph
from data.db import save_report

DATASET_PATH = os.path.join(PROJECT_ROOT, "dataset")
MODEL_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "models", "custom_medical_ner")

def run_training_and_evaluation(max_train_samples: int = 5000, eval_split: float = 0.2, epochs: int = 5):
    print("==================================================", flush=True)
    print(" CLINICAL REPORT SYSTEM: DATASET EVAL & MODEL TRAIN", flush=True)
    print("==================================================", flush=True)
    
    # 1. Load Data
    print(f"\n[STEP 1] Scanning and Streaming Datasets from '{DATASET_PATH}'...", flush=True)
    loader = DataLoader(DATASET_PATH)
    
    reports = []
    dataset_sources = {}
    
    for report in loader.stream_reports(chunk_size=1000):
        text = report.get("text", "")
        if text and isinstance(text, str) and len(text.strip()) > 15:
            reports.append(report)
            if max_train_samples is not None and len(reports) >= max_train_samples:
                break
                
    print(f"[DATASET SUMMARY] Loaded {len(reports)} valid clinical text records for training & evaluation.", flush=True)
    
    if not reports:
        print("[ERROR] No valid text reports found in dataset!")
        return
        
    # Split into Train and Evaluation sets
    random.seed(42)
    random.shuffle(reports)
    eval_count = int(len(reports) * eval_split)
    eval_reports = reports[:eval_count]
    train_reports = reports[eval_count:]
    
    print(f"[DATASET SPLIT] Train Set: {len(train_reports)} samples | Eval Set: {len(eval_reports)} samples", flush=True)
    
    # 2. Setup Weak Supervision Entity Dictionaries
    print("\n[STEP 2] Initializing SpaCy Weak-Supervision Dictionaries...", flush=True)
    if os.path.exists(MODEL_OUTPUT_DIR):
        print(f"[LOAD] Resuming from existing model at '{MODEL_OUTPUT_DIR}'...", flush=True)
        nlp = spacy.load(MODEL_OUTPUT_DIR)
    else:
        nlp = spacy.blank("en")
    
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    
    medications = [
        "metformin", "aspirin", "ibuprofen", "lisinopril", "amoxicillin", "atorvastatin",
        "amlodipine", "azithromycin", "clopidogrel", "acetaminophen", "heparin", "warfarin",
        "vancomycin", "furosemide", "omeprazole", "levothyroxine", "losartan", "simvastatin"
    ]
    
    diagnoses = [
        "diabetes", "diabetes mellitus", "hypertension", "sepsis", "heart failure", 
        "fracture", "urosepsis", "headache", "fever", "congestive heart failure",
        "pneumonia", "coronary artery disease", "stroke", "kidney injury", "asthma",
        "copd", "arrhythmia", "hypokalemia", "anemia"
    ]
    
    symptoms = [
        "chest pain", "shortness of breath", "cough", "abdominal pain", "nausea",
        "fatigue", "dizziness", "edema", "dyspnea", "fever", "chills"
    ]

    for m in medications:
        matcher.add("MEDICATION", [nlp.make_doc(m)])
    for d in diagnoses:
        matcher.add("DIAGNOSIS", [nlp.make_doc(d)])
    for s in symptoms:
        matcher.add("SYMPTOM", [nlp.make_doc(s)])
        
    print(f"[DICTIONARIES] Added {len(medications)} Medications, {len(diagnoses)} Diagnoses, {len(symptoms)} Symptoms.", flush=True)

    # Helper function to generate annotations
    def generate_examples(report_list):
        data = []
        for r in report_list:
            text = r["text"]
            doc = nlp.make_doc(text)
            matches = matcher(doc)
            spans = [doc[start:end] for match_id, start, end in matches]
            filtered_spans = spacy.util.filter_spans(spans)
            
            entities = []
            for span in filtered_spans:
                match_id = matcher(nlp.make_doc(span.text))[0][0]
                label = nlp.vocab.strings[match_id]
                entities.append((span.start_char, span.end_char, label))
                
            if entities:
                data.append((text, {"entities": entities}))
        return data

    print("\n[STEP 3] Auto-Labeling Training and Evaluation Sets...", flush=True)
    train_data = generate_examples(train_reports)
    eval_data = generate_examples(eval_reports)
    print(f"[AUTO-LABEL] Labeled Examples -> Train: {len(train_data)} | Eval: {len(eval_data)}", flush=True)

    # 3. Model Architecture Setup
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner")
    else:
        ner = nlp.get_pipe("ner")
        
    ner.add_label("MEDICATION")
    ner.add_label("DIAGNOSIS")
    ner.add_label("SYMPTOM")

    # 4. Training Loop
    if os.path.exists(MODEL_OUTPUT_DIR):
        print("\n[STEP 4] Resuming SpaCy Neural Network Training Loop...", flush=True)
        optimizer = nlp.resume_training()
    else:
        print("\n[STEP 4] Beginning SpaCy Neural Network Training Loop...", flush=True)
        optimizer = nlp.initialize()
    
    epoch_losses = []
    start_train_time = time.time()
    
    for i in range(epochs):
        random.shuffle(train_data)
        losses = {}
        batches = spacy.util.minibatch(train_data, size=spacy.util.compounding(4.0, 32.0, 1.001))
        
        for batch in batches:
            examples = []
            for text, annotations in batch:
                doc = nlp.make_doc(text)
                example = Example.from_dict(doc, annotations)
                examples.append(example)
            nlp.update(examples, sgd=optimizer, drop=0.35, losses=losses)
            
        ner_loss = losses.get("ner", 0.0)
        epoch_losses.append(ner_loss)
        print(f" -> Epoch {i+1}/{epochs} - NER Loss: {ner_loss:.4f}", flush=True)

    train_duration = time.time() - start_train_time
    print(f"[TRAINING COMPLETE] Finished in {train_duration:.2f} seconds.", flush=True)

    # 5. Model Evaluation on Held-Out Set
    print("\n[STEP 5] Evaluating Model Metrics on Held-Out Evaluation Dataset...", flush=True)
    eval_examples = []
    for text, annotations in eval_data:
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, annotations)
        pred_doc = nlp(text)
        example.predicted = pred_doc
        eval_examples.append(example)

    scores = nlp.evaluate(eval_examples)
    
    prec = scores.get("ents_p", 0.0)
    rec = scores.get("ents_r", 0.0)
    f1 = scores.get("ents_f", 0.0)
    per_type = scores.get("ents_per_type", {})
    
    print("\n--- MODEL PERFORMANCE METRICS ---", flush=True)
    print(f"Overall Precision : {prec * 100:.2f}%", flush=True)
    print(f"Overall Recall    : {rec * 100:.2f}%", flush=True)
    print(f"Overall F1 Score  : {f1 * 100:.2f}%", flush=True)
    print("\nPer-Entity Performance:", flush=True)
    for ent_type, metrics in per_type.items():
        print(f" - {ent_type:12s} | P: {metrics.get('p', 0)*100:6.2f}% | R: {metrics.get('r', 0)*100:6.2f}% | F1: {metrics.get('f', 0)*100:6.2f}%", flush=True)

    # Save Trained Model
    print(f"\n[STEP 6] Saving Trained Model to disk at '{MODEL_OUTPUT_DIR}'...", flush=True)
    os.makedirs(os.path.dirname(MODEL_OUTPUT_DIR), exist_ok=True)
    nlp.to_disk(MODEL_OUTPUT_DIR)
    print("[SUCCESS] Model successfully saved to disk!", flush=True)

    # 6. Evaluate Multi-Agent Graph Orchestrator with the Trained Model
    print("\n[STEP 7] Evaluating Multi-Agent Orchestrator Pipeline with Trained Model...", flush=True)
    pipeline_results = []
    
    sample_eval_subset = eval_reports[:20] if len(eval_reports) >= 20 else eval_reports
    
    for idx, report in enumerate(sample_eval_subset):
        initial_state = ReportState(
            document_id=report["document_id"],
            original_text=report["text"]
        )
        try:
            res = graph.invoke(initial_state)
            state_obj = ReportState(**res)
            save_report(state_obj)
            
            pipeline_results.append({
                "document_id": report["document_id"],
                "status": "success",
                "extracted_entities": len(res.get("extracted_entities", [])),
                "execution_plan": res.get("execution_plan", []),
                "replan_count": res.get("replan_count", 0),
                "verifier_flags": len(res.get("verifier_flags", []))
            })
        except Exception as e:
            pipeline_results.append({
                "document_id": report["document_id"],
                "status": "error",
                "error": str(e)
            })

    successful_runs = [r for r in pipeline_results if r["status"] == "success"]
    avg_entities = sum(r["extracted_entities"] for r in successful_runs) / max(len(successful_runs), 1)
    
    print("\n--- MULTI-AGENT PIPELINE EVALUATION ---", flush=True)
    print(f"Processed Reports   : {len(pipeline_results)}", flush=True)
    print(f"Success Rate        : {len(successful_runs)}/{len(pipeline_results)} ({len(successful_runs)/len(pipeline_results)*100:.1f}%)", flush=True)
    print(f"Avg Entities Extracted per Report: {avg_entities:.2f}", flush=True)

    # Export Evaluation Results Summary JSON
    eval_summary = {
        "dataset_samples_loaded": len(reports),
        "train_samples": len(train_reports),
        "eval_samples": len(eval_reports),
        "epochs": epochs,
        "train_duration_seconds": round(train_duration, 2),
        "epoch_losses": [round(float(l), 4) for l in epoch_losses],
        "metrics": {
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "per_entity": {k: {mk: float(mv) for mk, mv in v.items()} for k, v in per_type.items()}
        },
        "pipeline_eval": {
            "processed": len(pipeline_results),
            "success_rate": round(len(successful_runs)/max(len(pipeline_results), 1), 4),
            "avg_entities_extracted": round(float(avg_entities), 2)
        }
    }
    
    metrics_path = os.path.join(PROJECT_ROOT, "model_evaluation_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(eval_summary, f, indent=2)
        
    print(f"\n[EXPORT] Evaluation summary exported to '{metrics_path}'", flush=True)
    print("==================================================", flush=True)
    print(" ALL TASKS COMPLETED SUCCESSFULLY!", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    run_training_and_evaluation(max_train_samples=5000, eval_split=0.2, epochs=5)
