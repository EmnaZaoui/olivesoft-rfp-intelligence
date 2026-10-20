import subprocess
from pathlib import Path

LIBREOFFICE_BIN = r"C:\Program Files\LibreOffice\program\soffice.exe"


def convert_pptx_to_pdf(pptx_path: Path) -> Path:
    output_dir = pptx_path.parent
    try:
        subprocess.run(
            [LIBREOFFICE_BIN, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(pptx_path)],
            check=True, timeout=60, capture_output=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "LibreOffice (soffice) introuvable. Installez LibreOffice et vérifiez que 'soffice' "
            "est accessible, ou modifiez LIBREOFFICE_BIN dans ce fichier avec le chemin complet."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Échec de la conversion PDF: {e.stderr.decode(errors='ignore')}")

    pdf_path = output_dir / f"{pptx_path.stem}.pdf"
    if not pdf_path.exists():
        raise RuntimeError("La conversion PDF n'a produit aucun fichier de sortie.")
    return pdf_path