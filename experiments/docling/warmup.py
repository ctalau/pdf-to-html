"""
warmup.py — Pre-download docling ML models into the Docker image.
Run once during docker build to avoid model downloads at container start.
"""
import tempfile
import os

# Minimal valid 1-page PDF with the text "Hello"
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>>>endobj\n"
    b"4 0 obj<</Length 44>>\nstream\nBT /F1 12 Tf 100 700 Td (Hello world) Tj ET\nendstream\nendobj\n"
    b"xref\n0 5\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000274 00000 n \n"
    b"trailer<</Size 5/Root 1 0 R>>\n"
    b"startxref\n370\n%%EOF\n"
)

with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
    f.write(MINIMAL_PDF)
    pdf_path = f.name

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True   # trigger OCR model download too
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    result = converter.convert(pdf_path)
    md = result.document.export_to_markdown()
    print(f"Warm-up OK — extracted: {md[:80]!r}")
except Exception as e:
    print(f"Warm-up error (non-fatal): {e}")
finally:
    os.unlink(pdf_path)

print("Model warm-up complete.")
