from pathlib import Path
from agents.document import DocumentAgent


def main():
    if len(__import__("sys").argv) != 2:
        print('Usage: python test_document.py "path\\to\\file"')
        return

    file_path = Path(__import__("sys").argv[1])

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return

    print("=" * 70)
    print("DOCUMENT AGENT TEST")
    print("=" * 70)

    data = file_path.read_bytes()

    print(f"File: {file_path}")
    print(f"Size: {len(data):,} bytes")

    agent = DocumentAgent()

    print("\nRunning Document Agent...\n")

    analysis, text = agent.analyze_file(
        data=data,
        filename=file_path.name
    )

    print("=" * 70)
    print("DOCUMENT ANALYSIS")
    print("=" * 70)

    print(f"Document type:       {analysis.document_type}")
    print(f"Format:              {analysis.format}")
    print(f"Pages:               {analysis.pages}")
    print(f"Requires OCR:        {analysis.requires_ocr}")
    print(f"Scanned pages:       {analysis.scanned_pages}")
    print(f"Machine-readable:    {analysis.machine_readable_pages}")
    print(f"Has tables:          {analysis.has_tables}")
    print(f"Source text kind:    {analysis.source_text_kind}")

    print("\n" + "=" * 70)
    print("NATIVE TEXT RETURNED BY DOCUMENT AGENT")
    print("=" * 70)

    if text:
        print(text)
    else:
        print("(No native text returned)")


if __name__ == "__main__":
    main()