from pathlib import Path
import pdfplumber


def extract_text_from_pdf(pdf_path: Path) -> str:
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        return f"PDF_EXTRACTION_ERROR: {pdf_path.name} ({e})"

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        return f"PDF_EXTRACTION_ERROR: aucun texte extrait de {pdf_path.name} (PDF probablement scanné/image)"
    return full_text


def guess_doc_type(filename: str) -> str:
    lower = filename.lower()
    if "cv" in lower:
        return "cv"
    if "projet" in lower or "project" in lower or "pfe" in lower:
        return "project"
    return "reference"