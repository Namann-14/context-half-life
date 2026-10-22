"""E1: needle-in-a-haystack grid, literal vs paraphrased question wording.

    python experiments/e1_niah.py --model llama3.2:3b --lengths 1024 2048 4096 8192 16384 32768
"""
import argparse
import random

from common import JsonlLog, capture_env
from context_half_life import SEED, data, llm, niah, scoring, tokens

DEPTHS = [i / 10 for i in range(11)]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="llama3.2:3b")
    ap.add_argument("--lengths", type=int, nargs="+", default=[1024, 2048, 4096, 8192, 16384])
    ap.add_argument("--needles", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="stop after N new calls (smoke test)")
    a = ap.parse_args()
    niah.check_needles()
    text = data.load_gutenberg_text()
    chat = llm.OllamaChat(a.model, num_ctx=max(a.lengths) + 1024, num_predict=24)
    log = JsonlLog(f"e1_niah_{a.model.replace(':', '_')}")
    digest = chat.digest()
    cells = [(L, d, ni, wording) for L in a.lengths for d in DEPTHS for ni in range(a.needles)
             for wording in ("literal", "paraphrase")]
    random.Random(SEED).shuffle(cells)  # avoid consecutive prompts sharing long prefixes
    new = 0
    for L, d, ni, wording in cells:
        key = f"{a.model}|{L}|{d}|{ni}|{wording}"
        if key in log:
            continue
        n = niah.NEEDLES[ni]
        hay = niah.build_haystack(text, n, L, d, tokens.count)
        msgs = [{"role": "user", "content": f"{hay}\n\nUsing only the text above, answer briefly: {n[wording]}"}]
        r = chat.chat(msgs)
        log.write(dict(key=key, exp="e1", model=a.model, digest=digest, length=L, depth=d, needle=ni,
                       wording=wording, seed=SEED, prompt_hash=llm.prompt_hash(msgs),
                       ref_tokens=tokens.count(msgs[0]["content"]), prompt_tokens=r.prompt_tokens,
                       response=r.text, correct=int(scoring.contains_answer(r.text, n["answer"])),
                       wall_s=r.wall_s, prefill_s=r.prefill_s, decode_s=r.decode_s))
        new += 1
        if a.limit and new >= a.limit:
            break
    capture_env({a.model: digest})
    print("calls written:", new)
