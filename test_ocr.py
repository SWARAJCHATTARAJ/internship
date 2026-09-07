import sys
from pathlib import Path

from agents.ocr import OCRAgent


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print('python test_ocr.py "path\\to\\file.png"')
        return

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return

    print("=" * 70)
    print("OCR TEST")
    print("=" * 70)

    data = file_path.read_bytes()

    print(f"File: {file_path}")
    print(f"Size: {len(data):,} bytes")

    agent = OCRAgent()

    print("\nRunning OCR...\n")

    result = agent.process(
        data=data,
        filename=file_path.name
    )

    print("=" * 70)
    print("OCR RESULT")
    print("=" * 70)

    print(f"Success: {result.success}")
    print(f"Source type: {result.source_type}")
    print(f"Pages processed: {result.pages_processed}")
    print(f"Pages failed: {result.pages_failed}")
    print(f"Overall confidence: {result.overall_confidence}")

    print("\nWarnings:")
    for warning in result.warnings:
        print(f"  - {warning}")

    print("\nErrors:")
    for error in result.errors:
        print(f"  - {error}")

    print("\n" + "=" * 70)
    print("EXTRACTED TEXT")
    print("=" * 70)

    print(result.text)

    print("\n" + "=" * 70)
    print("PAGE DETAILS")
    print("=" * 70)

    for page in result.pages:
        print(f"\nPage {page.page_number}")
        print(f"Confidence: {page.confidence}")
        print(f"Error: {page.error}")
        print(f"Regions: {len(page.regions)}")

        print("\nFirst 20 OCR regions:")

        for region in page.regions[:20]:
            print(
                f"  {region.text!r} "
                f"confidence={region.confidence:.2f} "
                f"bbox={region.bbox}"
            )


if __name__ == "__main__":
    main()
