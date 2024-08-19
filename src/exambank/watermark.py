from io import BytesIO
from pathlib import Path
from datetime import datetime

import pymupdf
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# param to describe margin for exam generation text
BORDER = 20

def create_watermark(
    computing_id: str,
    density: int = 5
) -> BytesIO:
    """
        Returns a PDF with one page containing the watermark as text.
    """
    # Generate the tiling watermark
    stamp_buffer = BytesIO()
    stamp_pdf = canvas.Canvas(stamp_buffer, pagesize=A4)
    stamp_pdf.translate(density / 3 * inch, -density / 3 * inch)
    stamp_pdf.setFillColor(colors.grey, alpha=0.5)
    stamp_pdf.setFont("Helvetica", 100 / density)
    stamp_pdf.rotate(45)

    width, height = A4

    for i in range(1, 4  * int(width), int(width/density)):
        for j in range(1, 4 * int(height), int(height/density)):
            stamp_pdf.drawCentredString(i, j, computing_id)
    stamp_pdf.save()
    stamp_buffer.seek(0)

    # Generate the warning text in corner
    warning_buffer = BytesIO()
    warning_pdf = canvas.Canvas(warning_buffer, pagesize=A4)
    warning_pdf.setFillColor(colors.grey, alpha=0.75)
    warning_pdf.setFont("Helvetica", 14)

    warning_pdf.drawString(BORDER, BORDER, f"This exam was generated by {computing_id} at {datetime.now()}")

    warning_pdf.save()
    warning_buffer.seek(0)

    # Merge into watermark
    watermark_pdf = PdfWriter()
    stamp_pdf = PdfReader(stamp_buffer)
    warning_pdf = PdfReader(warning_buffer)

    # Destructively merges in place
    stamp_pdf.pages[0].merge_page(warning_pdf.pages[0])
    watermark_pdf.add_page(stamp_pdf.pages[0])

    watermark_buffer = BytesIO()
    watermark_pdf.write(watermark_buffer)
    watermark_buffer.seek(0)
    return watermark_buffer

def apply_watermark(
    pdf_path: Path | str,
    # expect a BytesIO instance (at position 0), accept a file/path
    stamp: BytesIO | Path | str,
) -> BytesIO:
    # process file
    stamp_page = PdfReader(stamp).pages[0]

    writer = PdfWriter()
    reader = PdfReader(pdf_path)
    writer.append(reader)
    for pdf_page in writer.pages:
        pdf_page.transfer_rotation_to_content()
        pdf_page.merge_page(stamp_page)

    watermarked_pdf = BytesIO()
    writer.write(watermarked_pdf)
    watermarked_pdf.seek(0)
    return watermarked_pdf

def raster_pdf(
    pdf_path: BytesIO,
    dpi: int = 300
) -> BytesIO:
    raster_buffer = BytesIO()
    # adapted from https://github.com/pymupdf/PyMuPDF/discussions/1183
    with pymupdf.open(stream=pdf_path) as doc:
        page_count = doc.page_count
        with pymupdf.open() as target:
            for page, _dpi in zip(doc, [dpi] * page_count, strict=False):
                zoom = _dpi / 72
                mat = pymupdf.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                tarpage = target.new_page(width=page.rect.width, height=page.rect.height)
                tarpage.insert_image(tarpage.rect, stream=pix.pil_tobytes("PNG"))

            target.save(raster_buffer)

    raster_buffer.seek(0)
    return raster_buffer

# TODO: not sure what this function does, but let's remove it?
def raster_pdf_from_path(
    pdf_path: Path | str,
    dpi: int = 300
) -> BytesIO:
    raster_buffer = BytesIO()
    
    # adapted from https://github.com/pymupdf/PyMuPDF/discussions/1183
    with pymupdf.open(filename=pdf_path) as doc:
        page_count = doc.page_count
        with pymupdf.open() as target:
            for page, _dpi in zip(doc, [dpi] * page_count, strict=False):
                zoom = _dpi / 72
                mat = pymupdf.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                tarpage = target.new_page(width=page.rect.width, height=page.rect.height)
                tarpage.insert_image(tarpage.rect, stream=pix.pil_tobytes("PNG"))

            target.save(raster_buffer)

    raster_buffer.seek(0)
    return raster_buffer
