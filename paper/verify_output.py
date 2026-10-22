"""Sanity checks for Context_Rot_Research_Final.docx.

Checks that the file opens, that nothing from the template's original paper survives, that every
section heading and reference is present, that citations and captions are consistent, and that no
build markup leaked into the text. Run from the repository root:  python paper/verify_output.py
"""
import json
import re
import sys
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paper_content import BODY, REFERENCES  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Context_Rot_Research_Final.docx"
TEMPLATE_LEFTOVERS = ["breast", "cancer", "CNN", "Deepak", "Abhiraj", "Malhotra", "mammogra", "infrared",
                      "Kaggle", "kaggle", "Rajpura", "Himachal", "thermal", "RFID", "Grammarly"]

failures = []


def check(cond, msg):
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        failures.append(msg)


doc = Document(OUT)
paras = doc.paragraphs
text_all = "\n".join(p.text for p in paras)
for t in doc.tables:
    for row in t.rows:
        text_all += "\n" + " | ".join(c.text for c in row.cells)

with zipfile.ZipFile(OUT) as z:
    names = z.namelist()
    xml_all = "".join(z.read(n).decode("utf-8", "ignore") for n in names if n.endswith((".xml", ".rels")))
    check(z.testzip() is None, "zip container is intact")
    media = [n for n in names if n.startswith("word/media/")]

leftovers = [w for w in TEMPLATE_LEFTOVERS if w in xml_all]
check(not leftovers, f"no template leftovers in any XML part {leftovers or ''}")
check(not re.search(r"\[@|\[#|</?(b|i|code|super|sub)>", text_all), "no build markup leaked into text")
n_figures = sum(1 for b in BODY if b[0] == "figure")
check(len(media) == n_figures, f"exactly the {n_figures} new figures are embedded ({len(media)} media files)")

headings = [(int(b[0][1]), b[1]) for b in BODY if b[0] in ("h1", "h2", "h3")]
doc_headings = [(int(p.style.name[-1]), p.text) for p in paras if p.style.name.startswith("Heading")]
check(doc_headings == headings, f"all {len(headings)} headings present in order")

ref_paras = [p for p in paras if p._p.pPr is not None and p._p.pPr.numPr is not None
             and p._p.pPr.numPr.numId.val == 12]
check(len(ref_paras) == len(REFERENCES), f"{len(ref_paras)} of {len(REFERENCES)} references listed")


def is_code(p):
    """A listing line: every non-empty run is monospace (inline <code> in prose does not count)."""
    runs = [r for r in p.runs if r.text]
    return bool(runs) and all(r.font.name == "Courier New" for r in runs)


body_text = "\n".join(p.text for p in paras if p not in ref_paras and not is_code(p))
for t in doc.tables:
    for row in t.rows:
        body_text += "\n" + " ".join(c.text for c in row.cells)
cited = {int(n) for n in re.findall(r"\[(\d+)\]", body_text)}
for a, b in re.findall(r"\[(\d+)\]–\[(\d+)\]", body_text):
    cited |= set(range(int(a), int(b) + 1))
check(cited == set(range(1, len(REFERENCES) + 1)), f"every reference 1..{len(REFERENCES)} is cited in the text")

first_seen = []
for n in re.findall(r"\[(\d+)\]", body_text):
    if int(n) not in first_seen:
        first_seen.append(int(n))
check(first_seen == sorted(first_seen), "references are numbered in order of first citation (IEEE)")

for kind in ("Figure", "Table", "Listing"):
    nums = [int(m) for m in re.findall(rf"^{kind} (\d+):", text_all, re.M)]
    check(nums == list(range(1, len(nums) + 1)), f"{kind} captions numbered 1..{len(nums)}")

# ---- cross-references: every "Fig. N", "Table N", "Listing N", "Eq. (N)" in the text resolves, and every
# caption and equation is referenced at least once.
caption_re = {"Figure": r"^Figure (\d+):", "Table": r"^Table (\d+):", "Listing": r"^Listing (\d+):"}
n_eq = sum(1 for b in BODY if b[0] == "eq")
is_caption = lambda p: any(re.match(rx, p.text) for rx in caption_re.values())  # noqa: E731
prose = "\n".join(p.text for p in paras if p not in ref_paras and not is_code(p) and not is_caption(p))
for t in doc.tables:
    for row in t.rows:
        prose += "\n" + " ".join(c.text for c in row.cells)
captions = {k: [int(m) for m in re.findall(rx, text_all, re.M)] for k, rx in caption_re.items()}
refs_in_text = {
    "Figure": {int(n) for n in re.findall(r"Figs?\. (\d+)", prose)},
    "Table": {int(n) for n in re.findall(r"Tables? (\d+)", prose)},
    "Listing": {int(n) for n in re.findall(r"Listings? (\d+)", prose)},
}
for kind, nums in refs_in_text.items():
    dangling = sorted(n for n in nums if n not in captions[kind])
    unref = sorted(n for n in captions[kind] if n not in nums)
    check(not dangling, f"every {kind} reference in the text resolves to a caption {dangling or ''}")
    check(not unref, f"every {kind} caption is referenced in the text {unref or ''}")
eq_refs = {int(n) for n in re.findall(r"Eqs?\. \((\d+)\)", prose)}
check(all(1 <= n <= n_eq for n in eq_refs), f"every equation reference resolves (1..{n_eq})")

# ---- measured numbers: nothing unresolved, and every quoted number matches results/paper_numbers.json
check("[$" not in text_all, "no unresolved [$key|fmt] number placeholders")
used_path = HERE / "numbers_used.json"
nums_path = ROOT / "results" / "paper_numbers.json"
if used_path.exists() and nums_path.exists():
    used, numbers = json.loads(used_path.read_text(encoding="utf8")), json.loads(nums_path.read_text(encoding="utf8"))
    check(len(used) > 50, f"paper quotes {len(used)} measured numbers")
    check(all(k in numbers and numbers[k] == v for k, v in used.items()),
          "every quoted number equals its value in results/paper_numbers.json")
else:
    check(False, "paper/numbers_used.json and results/paper_numbers.json exist")

# ---- wording rules and honest labelling
for phrase in ("first-year", "student can build it", "reports no empirical", "report no empirical",
               "Anticipated Results", "pre-register", "Expected results"):
    check(phrase.lower() not in text_all.lower(), f"banned phrase absent: {phrase!r}")
fig_caps = [p.text for p in paras if re.match(r"^Figure \d+:", p.text)]
markers = ("measured", "schematic", "illustrative", "calculation", "reported", "simulated", "loop")
check(all(any(m in c.lower() for m in markers) for c in fig_caps),
      "every figure caption says whether it is measured, reported, schematic, or simulated")
check(sum("(measured" in c.lower() for c in fig_caps) == 4, "four figures are labelled as measured results")

sections = doc.sections
layouts = []
for s in sections:
    cols = s._sectPr.find(qn("w:cols"))
    layouts.append(int(cols.get(qn("w:num"), "1")))
check(all(abs(s.page_width.inches - 8.5) < 0.01 and abs(s.page_height.inches - 11) < 0.01 for s in sections),
      "every section is US Letter, as in the template")
check(all(abs(m - 1.0) < 0.01 for s in sections
          for m in (s.top_margin.inches, s.bottom_margin.inches, s.left_margin.inches, s.right_margin.inches)),
      "1-inch margins everywhere, as in the template")
print(f"INFO  {len(sections)} sections, column layout {layouts}")
print(f"INFO  {len(paras)} paragraphs, {len(doc.tables)} tables, ~{len(text_all.split())} words")

sys.exit(1 if failures else 0)
