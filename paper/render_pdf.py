"""Render the built .docx to PDF through Microsoft Word (COM automation, Windows) and to page images.

    python paper/render_pdf.py            -> paper/Context_Rot_Research_Final.pdf, paper/_render/page-N.png
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCX = HERE / "Context_Rot_Research_Final.docx"
PDF = HERE / "Context_Rot_Research_Final.pdf"
IMG = HERE / "_render"


def to_pdf():
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(DOCX), ReadOnly=True, AddToRecentFiles=False)
        doc.Fields.Update()
        doc.Repaginate()
        pages = doc.ComputeStatistics(2)  # wdStatisticPages
        doc.ExportAsFixedFormat(str(PDF), 17)  # wdExportFormatPDF
        doc.Close(False)
    finally:
        word.Quit()
    return pages


def to_images(dpi=110):
    import fitz

    IMG.mkdir(exist_ok=True)
    for old in IMG.glob("page-*.png"):
        old.unlink()
    with fitz.open(PDF) as d:
        for i, page in enumerate(d, 1):
            page.get_pixmap(dpi=dpi).save(IMG / f"page-{i:02d}.png")
        return len(d)


if __name__ == "__main__":
    words_pages = to_pdf()
    n = to_images()
    print(f"Word reports {words_pages} pages; PDF has {n} pages -> {PDF}")
    sys.exit(0)
