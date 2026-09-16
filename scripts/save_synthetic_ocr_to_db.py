import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure DATABASE_URL points to Postgres (set to your Neon URL)
DATABASE_URL = "postgresql://neondb_owner:npg_hCpk8bBxJV3l@ep-dawn-recipe-b5a6gotn-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
os.environ['DATABASE_URL'] = DATABASE_URL

from agents.ocr import OCRAgent
from schemas.core import ReportState, OCRResult
from data import db as data_db

# Run OCR on the synthetic image created earlier (or generate new)
script_img = os.path.join(PROJECT_ROOT, 'scripts', 'synthetic_prescription.png')
if not os.path.exists(script_img):
    # regenerate using previous script
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (800, 300), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    text = "Patient: John Doe\nAge: 58\nRx: Metformin 500 mg twice daily\nTake with food."
    d.text((20, 20), text, fill=(0, 0, 0))
    img.save(script_img)

with open(script_img, 'rb') as f:
    image_bytes = f.read()

agent = OCRAgent()
ocr_result = agent.process(image_bytes, filename=os.path.basename(script_img))

# Build a minimal ReportState
rs = ReportState(
    document_id=f"synthetic_ocr_{int(datetime.utcnow().timestamp())}",
    original_text="",
    source_text=None,
    source_type=ocr_result.source_type,
    source_file=script_img,
    ocr_result=ocr_result,
    document_analysis=None,
    execution_plan=['ocr_agent'],
    extracted_entities=[],
    relations=[],
    timeline=[],
    verifier_flags=[],
    audit_trail=[{
        'id': 'audit-1', 'timestamp': datetime.utcnow().isoformat(), 'agent_name': 'ocr_test', 'action_type': 'ocr_run', 'details': {'image': script_img}
    }],
    summary=None,
    trained_model_used=False,
    replan_count=0,
    agent_outputs={'ocr': ocr_result.model_dump()},
)

# Save to DB (will use Postgres because DATABASE_URL is set)
data_db.save_report(rs)
print('Saved synthetic OCR ReportState to DB as', rs.document_id)
