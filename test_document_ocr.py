import sys
from pathlib import Path

from agents.document import DocumentAgent
from agents.ocr import OCRAgent


def main():
    if len(sys.argv) != 2:
        print('Usage: python test_document_ocr.py "path\\to\\file"')
        return

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return

    print("=" * 70)
    print("DOCUMENT + OCR INTEGRATION TEST")
    print("=" * 70)

    data = file_path.read_bytes()

    print(f"File: {file_path}")
    print(f"Size: {len(data):,} bytes")

    # ---------------------------------------------------------
    # STEP 1: Document analysis
    # ---------------------------------------------------------
    document_agent = DocumentAgent()

    print("\n" + "=" * 70)
    print("STEP 1 - DOCUMENT ANALYSIS")
    print("=" * 70)

    document_analysis, native_text = document_agent.analyze_file(
        data=data,
        filename=file_path.name,
    )

    print(f"Document type:    {document_analysis.document_type}")
    print(f"Format:           {document_analysis.format}")
    print(f"Pages:            {document_analysis.pages}")
    print(f"Requires OCR:     {document_analysis.requires_ocr}")
    print(f"Scanned pages:    {document_analysis.scanned_pages}")
    print(f"Machine readable: {document_analysis.machine_readable_pages}")
    print(f"Source text kind:  {document_analysis.source_text_kind}")

    # ---------------------------------------------------------
    # STEP 2: OCR only if document agent says it is required
    # ---------------------------------------------------------
    if document_analysis.requires_ocr:
        print("\n" + "=" * 70)
        print("STEP 2 - OCR")
        print("=" * 70)

        ocr_agent = OCRAgent()

        ocr_result = ocr_agent.process(
            data=data,
            filename=file_path.name,
        )

        print(f"Success:             {ocr_result.success}")
        print(f"Source type:         {ocr_result.source_type}")
        print(f"Pages processed:     {ocr_result.pages_processed}")
        print(f"Pages failed:        {ocr_result.pages_failed}")
        print(f"Overall confidence:  {ocr_result.overall_confidence}")

        if ocr_result.warnings:
            print("\nWarnings:")
            for warning in ocr_result.warnings:
                print(f"  - {warning}")

        if ocr_result.errors:
            print("\nErrors:")
            for error in ocr_result.errors:
                print(f"  - {error}")

        # -----------------------------------------------------
        # STEP 3: Classify document using OCR text
        # -----------------------------------------------------
        print("\n" + "=" * 70)
        print("STEP 3 - DOCUMENT CLASSIFICATION FROM OCR TEXT")
        print("=" * 70)

        if ocr_result.success and ocr_result.text:
            classified = document_agent.analyze_text(ocr_result.text)

            print(f"Document type: {classified.document_type}")
            print(f"Format:        {classified.format}")
            print(f"Pages:         {classified.pages}")
            print(f"Requires OCR:  {classified.requires_ocr}")

            print("\n" + "=" * 70)
            print("OCR EXTRACTED TEXT")
            print("=" * 70)

            print(ocr_result.text)

        else:
            print("OCR failed. Document classification cannot continue.")

    else:
        print("\n" + "=" * 70)
        print("STEP 2 - OCR")
        print("=" * 70)
        print("OCR was not required.")

        print("\nNative document text:")
        print(native_text)


if __name__ == "__main__":
    main()