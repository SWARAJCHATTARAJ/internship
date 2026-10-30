import os
import sys
from io import BytesIO

# Ensure project root is on sys.path for local imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.ocr import OCRAgent
from PIL import Image, ImageDraw, ImageFont

# Generate a synthetic prescription-like image
img = Image.new('RGB', (800, 300), color=(255, 255, 255))
d = ImageDraw.Draw(img)
text = "Patient: John Doe\nAge: 58\nRx: Metformin 500 mg twice daily\nTake with food."
# Use default font
d.text((20, 20), text, fill=(0, 0, 0))

buf = BytesIO()
img.save(buf, format='PNG')
image_bytes = buf.getvalue()

agent = OCRAgent()
result = agent.process(image_bytes, filename="synthetic_prescription.png")

# Print JSON result (Pydantic v2 -> use model_dump())
import json
print(json.dumps(result.model_dump(), indent=2))

# Optionally write image to disk for inspection
out_path = os.path.join(os.path.dirname(__file__), 'synthetic_prescription.png')
with open(out_path, 'wb') as f:
    f.write(image_bytes)
print(f"Wrote test image to: {out_path}")
