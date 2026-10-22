from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_listing_lines_fit_one_column():
    from paper_content import LISTINGS
    assert set(LISTINGS) >= {"probe", "fit", "repair"}
    for name, src in LISTINGS.items():
        for line in src.split("\n"):
            assert len(line) <= 49, (name, line)


def test_listings_come_from_real_source():
    from paper_content import LISTINGS
    code = "".join(p.read_text(encoding="utf8") for p in (ROOT / "src").rglob("*.py"))
    for name, src in LISTINGS.items():
        assert src.split("\n")[0] in code, name
