"""Download datasets into data/ (LongMemEval cleaned, Gutenberg texts) and record the dataset commit."""
import json

from common import ENV, ROOT  # noqa: F401
from context_half_life import data

if __name__ == "__main__":
    sha = data.fetch_longmemeval()
    data.fetch_gutenberg()
    ENV.mkdir(parents=True, exist_ok=True)
    (ENV / "datasets.json").write_text(json.dumps({"longmemeval-cleaned": sha}, indent=2))
    print("LongMemEval commit", sha)
