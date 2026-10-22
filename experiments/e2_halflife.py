"""E2: fact-ageing half-life. Mode 'ageing' (age = turns after the fact) or 'matched' (total length fixed).

    python experiments/e2_halflife.py --model llama3.2:3b --mode ageing
"""
import argparse
import random

from common import JsonlLog, capture_env
from context_half_life import SEED, data, llm, probe, scoring, tokens

AGES = [0, 5, 10, 20, 40, 80]
KINDS = ["preference", "changing", "tool"]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="llama3.2:3b")
    ap.add_argument("--mode", choices=["ageing", "matched"], default="ageing")
    ap.add_argument("--facts", type=int, default=20)
    ap.add_argument("--ages", type=int, nargs="+", default=AGES)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    questions = data.load_longmemeval("s")
    pool = data.chat_pairs(questions, SEED, n=400)
    chat = llm.OllamaChat(a.model, num_ctx=24576, num_predict=24)
    digest = chat.digest()
    log = JsonlLog(f"e2_{a.mode}_{a.model.replace(':', '_')}")
    total = max(AGES)
    jobs = []
    for kind in KINDS:
        for i in range(a.facts):
            fact = probe.make_fact(kind, i, random.Random(f"{SEED}|{kind}|{i}"))
            for age in a.ages:
                jobs.append((kind, i, fact, age))
    random.Random(SEED).shuffle(jobs)
    new = 0
    for kind, i, fact, age in jobs:
        key = f"{a.model}|{a.mode}|{kind}|{i}|{age}"
        if key in log:
            continue
        seed = SEED + 1000 * KINDS.index(kind) + i
        after = probe.nested_filler(pool, age, seed)
        before = probe.nested_filler(pool[::-1], total - age, seed + 7) if a.mode == "matched" else []
        msgs = []
        for u, b in before:
            msgs += [{"role": "user", "content": u}, {"role": "assistant", "content": b}]
        msgs += [{"role": "user", "content": fact["statement"]}, {"role": "assistant", "content": "Noted!"}]
        if kind == "changing":
            msgs += [{"role": "user", "content": fact["update"]}, {"role": "assistant", "content": "Got it, updated."}]
        for u, b in after:
            msgs += [{"role": "user", "content": u}, {"role": "assistant", "content": b}]
        msgs.append({"role": "user", "content": fact["question"]})
        r = chat.chat(msgs)
        rec = dict(key=key, exp="e2", mode=a.mode, model=a.model, digest=digest, kind=kind, fact=i, age=age,
                   seed=seed, prompt_hash=llm.prompt_hash(msgs), ref_tokens=tokens.count_messages(msgs),
                   prompt_tokens=r.prompt_tokens, response=r.text, correct=int(scoring.contains_answer(r.text, fact["answer"])),
                   wall_s=r.wall_s)
        if "stale" in fact:
            rec["stale_hit"] = int(scoring.contains_answer(r.text, fact["stale"]))
        log.write(rec)
        new += 1
        if a.limit and new >= a.limit:
            break
    capture_env({a.model: digest})
    print("calls written:", new)
