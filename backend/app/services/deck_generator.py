from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

# Palette "vert olive" par défaut — à ajuster avec les vraies couleurs de charte OliveSoft
OLIVE_PRIMARY = RGBColor(0x4B, 0x5D, 0x2E)
OLIVE_SECONDARY = RGBColor(0x8A, 0x9A, 0x5B)
OLIVE_ACCENT = RGBColor(0xD4, 0xC5, 0x8E)
TEXT_DARK = RGBColor(0x2B, 0x2B, 0x2B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "generated_decks"
OUTPUT_DIR.mkdir(exist_ok=True)

SLIDE_WIDTH = Inches(13.33)
SLIDE_HEIGHT = Inches(7.5)


def _add_background(slide, color: RGBColor):
    shape = slide.shapes.add_shape(1, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False
    slide.shapes._spTree.remove(shape._element)
    slide.shapes._spTree.insert(2, shape._element)


def _add_title(slide, text: str, color: RGBColor = WHITE, top=Inches(0.5), size=32):
    box = slide.shapes.add_textbox(Inches(0.7), top, Inches(12), Inches(1.2))
    tf = box.text_frame
    tf.word_wrap = True
    run = tf.paragraphs[0].add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = color


def _add_body_text(slide, text: str, top, height=Inches(5), color: RGBColor = TEXT_DARK, size=16):
    box = slide.shapes.add_textbox(Inches(0.7), top, Inches(12), height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.color.rgb = color


def _add_section_header_slide(prs: Presentation, title: str):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_background(slide, OLIVE_PRIMARY)
    _add_title(slide, title, color=WHITE, top=Inches(3.0), size=40)
    return slide


def _add_content_slide(prs: Presentation, title: str, body_text: str):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_background(slide, WHITE)
    accent = slide.shapes.add_shape(1, 0, 0, SLIDE_WIDTH, Inches(0.15))
    accent.fill.solid()
    accent.fill.fore_color.rgb = OLIVE_SECONDARY
    accent.line.fill.background()
    _add_title(slide, title, color=OLIVE_PRIMARY, top=Inches(0.4), size=26)
    _add_body_text(slide, body_text, top=Inches(1.5))
    return slide


def _add_matrix_slide(prs: Presentation, matrix: list[dict]):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_background(slide, WHITE)
    _add_title(slide, "Matrice de couverture des exigences", color=OLIVE_PRIMARY, top=Inches(0.4), size=26)

    display_rows = matrix[:8]
    table_shape = slide.shapes.add_table(
        len(display_rows) + 1, 3, Inches(0.7), Inches(1.4), Inches(12), Inches(5.4)
    )
    table = table_shape.table

    for c, header in enumerate(["Exigence", "Couverte", "Score"]):
        cell = table.cell(0, c)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = OLIVE_PRIMARY
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.color.rgb = WHITE
                r.font.bold = True

    for i, item in enumerate(display_rows, start=1):
        table.cell(i, 0).text = item["requirement_text"][:80]
        table.cell(i, 1).text = "Oui" if item["covered"] else "Non"
        table.cell(i, 2).text = f"{item['score']}/100"

    return slide


def generate_pptx(tender: dict, proposal_sections: dict, matrix: list[dict], filename: str) -> Path:
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    title_slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_background(title_slide, OLIVE_PRIMARY)
    _add_title(title_slide, "Proposition Commerciale", color=WHITE, top=Inches(2.6), size=44)

    tender_title = tender.get("title", "Appel d'offres")
    _add_body_text(
        title_slide,
        f"{tender_title}\nPréparé par OliveSoft",
        top=Inches(4.0), color=OLIVE_ACCENT, size=20,
    )

    for content in proposal_sections.values():
        lines = content.splitlines()
        heading = lines[0].lstrip("#").strip() if lines else "Section"
        body = "\n".join(l for l in lines if not l.strip().startswith("#")).strip()
        _add_content_slide(prs, heading, body[:900])

    if matrix:
        _add_matrix_slide(prs, matrix)

    _add_section_header_slide(prs, "Merci pour votre confiance")

    output_path = OUTPUT_DIR / f"{filename}.pptx"
    prs.save(output_path)
    return output_path