import requests
import json
import sys

BASE_URL = "http://localhost:8000"
UPLOAD_PATH = "scripts/synthetic_prescription.png"


def main():
    print('Uploading', UPLOAD_PATH, 'to', BASE_URL + '/process/upload')
    # include a document_id form field required by the API
    import time
    doc_id = f"synthetic_upload_{int(time.time())}"
    try:
        with open(UPLOAD_PATH, 'rb') as f:
            files = {'file': ('synthetic_prescription.png', f, 'image/png')}
            data = {'document_id': doc_id}
            r = requests.post(BASE_URL + '/process/upload', files=files, data=data, timeout=120)
    except Exception as e:
        print('Upload failed:', e)
        sys.exit(2)

    print('Upload status:', r.status_code)
    try:
        resp = r.json()
    except Exception:
        print('Upload response text:', r.text)
        sys.exit(2)

    print('Upload response:', json.dumps(resp, indent=2)[:2000])

    # prefer the generated doc_id if API doesn't echo it
    doc_id = resp.get('document_id') or resp.get('id') or resp.get('documentId') or doc_id
    if not doc_id:
        print('No document_id in upload response; cannot check persistence.')
        sys.exit(0)

    print('\nFetching saved report for', doc_id)
    try:
        r2 = requests.get(BASE_URL + f'/reports/{doc_id}', timeout=30)
        print('GET /reports/{id} status:', r2.status_code)
        print(r2.text[:4000])
    except Exception as e:
        print('Error fetching report:', e)

    print('\nListing recent reports (limit=10)')
    try:
        r3 = requests.get(BASE_URL + '/reports?limit=10', timeout=30)
        print('GET /reports status:', r3.status_code)
        print(json.dumps(r3.json(), indent=2)[:4000])
    except Exception as e:
        print('Error listing reports:', e)


if __name__ == '__main__':
    main()
