import requests, time, sys

BASE = 'http://127.0.0.1:8000'
PATH = 'scripts/synthetic_prescription.png'
if len(sys.argv) > 1:
    PATH = sys.argv[1]

with open(PATH, 'rb') as f:
    files = {'file': ('synthetic_prescription.png', f, 'image/png')}
    doc_id = f'upload_poll_{int(time.time())}'
    data = {'document_id': doc_id}
    print('Uploading', PATH, 'as', doc_id)
    r = requests.post(BASE + '/process/upload', files=files, data=data, timeout=600)
    print('POST status', r.status_code)
    try:
        print('response:', r.json())
    except Exception:
        print('response text:', r.text[:1000])

print('Polling for report...')
start = time.time()
while time.time() - start < 600:
    try:
        rr = requests.get(BASE + f'/reports/{doc_id}', timeout=10)
        if rr.status_code == 200:
            print('Report found')
            rep = rr.json()
            print('Execution trace:', rep.get('execution_trace'))
            # check orchestrator
            found = any((t.get('agent') == 'orchestrator' and (t.get('status') in ('completed','done'))) for t in (rep.get('execution_trace') or []))
            print('Orchestrator completed?', found)
            print('Saved report id:', rep.get('document_id'))
            sys.exit(0)
    except Exception as e:
        print('poll error', e)
    time.sleep(3)

print('Timed out waiting for report')
sys.exit(2)
