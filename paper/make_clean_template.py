"""Create paper/template/ieee_template.docx from the original IEEE template.

The original template (paper/originals/template.docx, not published) carries another team's paper.
This script keeps everything build_paper.py relies on (paragraph and section structure, styles,
numbering, page setup) and blanks all text, images, links, tables and identifying metadata.

Run from the repository root:  python paper/make_clean_template.py
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

HERE = Path(__file__).resolve().parent
SRC = HERE / "originals" / "template.docx"
DST = HERE / "template" / "ieee_template.docx"


def clean(src, dst):
    doc = Document(src)
    body = doc.element.body
    for tbl in body.findall(qn("w:tbl")):
        body.remove(tbl)
    for tag in ("w:hyperlink", "w:drawing", "w:pict", "w:object"):
        for el in list(body.iter(qn(tag))):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
    for t in body.iter(qn("w:t")):
        t.text = ""
    for t in body.iter(qn("w:instrText")):
        t.text = ""
    for rId, rel in list(doc.part.rels.items()):
        if rel.reltype.endswith(("/image", "/hyperlink")):
            doc.part.drop_rel(rId)
    cp = doc.core_properties
    for attr in ("title", "author", "last_modified_by", "subject", "keywords", "comments", "category"):
        setattr(cp, attr, "")
    dv = doc.settings.element.find(qn("w:docVars"))
    if dv is not None:
        doc.settings.element.remove(dv)
    for part in doc.part.package.iter_parts():
        name = str(part.partname)
        if name == "/docProps/custom.xml":
            part._blob = re.sub(rb"<property .*?</property>", b"", part.blob, flags=re.S)
    DST.parent.mkdir(exist_ok=True)
    doc.save(dst)
    return dst


if __name__ == "__main__":
    print("wrote", clean(Path(sys.argv[1]) if len(sys.argv) > 1 else SRC, DST))
