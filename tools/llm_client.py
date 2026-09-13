"""Ultra-lightweight Gemini LLM client for clinical entity & relation extraction.
Uses standard library urllib to avoid extra dependencies and zero SSD model storage.
"""
from __future__ import annotations

import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

def get_api_key() -> Optional[str]:
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key.strip()
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        return val
    return None

def call_gemini_json(prompt: str, model: str = "gemini-3.1-flash-lite", timeout: int = 15) -> Optional[Dict[str, Any]]:
    """Calls Gemini API with structured JSON output enforced."""
    key = get_api_key()
    if not key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
    except Exception as exc:
        # Fallback to local deterministic agent if any network/API issue occurs
        return None


def transcribe_clinical_image(image_bytes: bytes, mime_type: str = "image/jpeg", model: str = "gemini-3.1-flash-lite", timeout: int = 25) -> Optional[str]:
    """Uses Gemini Multimodal Vision to accurately transcribe printed and handwritten prescriptions."""
    key = get_api_key()
    if not key:
        return None
    try:
        import base64
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        prompt = (
            "You are an expert clinical document transcriber and medical OCR specialist.\n"
            "Accurately read and transcribe all printed and handwritten text from this medical prescription / clinical record.\n"
            "Format the output clearly as structured plain clinical text:\n"
            "Header / Clinic Name:\n"
            "Date:\n"
            "Patient: [Name] (Age, Gender, ID/UHID)\n"
            "Chief Complaints / Symptoms:\n"
            "Clinical Examination / Vitals / Labs (e.g. BP, Pulse, RBS blood glucose):\n"
            "Diagnosis / Impression:\n"
            "Prescription Orders:\n"
            "(List each drug with dosage, route, frequency, and instructions)\n"
            "Advice / Warnings:\n\n"
            "Transcribe all handwritten medications and clinical notes with the utmost medical accuracy. "
            "Output pure clinical text without conversational disclaimers."
        )
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": mime_type, "data": img_b64}}
                ]
            }],
            "generationConfig": {
                "temperature": 0.1
            }
        }
        data = json.dumps(payload).encode("utf-8")
        candidate_models = [model, "gemini-2.5-flash", "gemini-2.0-flash"]
        for m in candidate_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if text:
                        return text
            except Exception:
                continue
        return None
    except Exception as exc:
        return None

