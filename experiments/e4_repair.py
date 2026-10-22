"""E4 (repair comparison) and E5 (ablations) on a stratified LongMemEval subset.

Stage 1 (reader answers):  python experiments/e4_repair.py --stage answer
Stage 2 (LLM judge):       python experiments/e4_repair.py --stage judge

Conditions
  B0 full context | B1 sliding window | B2 rolling summary | RND random repair | OLD oldest-first
  HL half-life-guided repair | ORACLE evidence sessions only (upper bound)
  E5: HL_noupdate HL_nomerge HL_noremove HL_noprotect HL_noverify HL_tok (token-budget trigger)
B1/B2/RND/OLD are matched per question to the token count of the HL context.
Identical prompts are answered once (temperature 0), and the answer is reused with cached=1.
"""
import argparse
import hashlib
import json
import re
import time
import zlib

import numpy as np

from common import JsonlLog, SUMMARY, read_jsonl, capture_env
from context_half_life import SEED, data, detectors, llm, repair, scoring, tokens

TARGET_TOKENS = 8000
MAX_EVIDENCE = 4500
R_STAR = 0.10
STRATA = {"knowledge-update": 12, "temporal-reasoning": 12, "multi-session": 10,
          "single-session-user": 8, "abstention": 8}
CONDITIONS = ["B0", "B1", "B2", "RND", "OLD", "HL", "ORACLE",
              "HL_noupdate", "HL_nomerge", "HL_noremove", "HL_noprotect", "HL_noverify", "HL_tok"]
SYSTEM = ("You are a helpful assistant with access to the earlier chat history below. Answer the question "
          "using only that history. If the history does not contain the information, say that you do not "
          "know. Answer in one short sentence.")
EXTRACT = ("List personal facts the user states about themself in the message below, one per line as "
           "'attribute: value' with a short generic attribute name (for example 'city: Pune'). "
           "If there are none, reply NONE.\n\nMessage: {m}")
CUE = re.compile(r"\b(now|currently|moved|changed|switched|new|used to|no longer|started|since|latest|"
                 r"live in|work at|my \w+ is)\b|\d", re.I)


def render(segs, q):
    hist = "\n".join(f"{s['role']}: {s['text']}" for s in segs)
    return [{"role": "user", "content": f"{SYSTEM}\n\n### Chat history\n{hist}\n\n### Question\n"
                                        f"Today's date: {q['question_date']}\n{q['question']}"}]


def extract_eav(q_segs, aux, xlog, embed):
    """LLM extraction of (attribute, value) for cue-bearing user messages; attributes canonicalised."""
    canon, out = [], []
    for s in q_segs:
        eav = None
        if s["role"] == "user" and CUE.search(s["text"]):
            key = "x|" + hashlib.sha256(s["text"].encode()).hexdigest()[:16]
            if key in xlog.done:
                resp = xlog.cache[key]
            else:
                resp = aux.chat([{"role": "user", "content": EXTRACT.format(m=" ".join(s["text"].split()[:150]))}],
                                num_predict=48).text
                xlog.write(dict(key=key, response=resp))
                xlog.cache[key] = resp
            for line in resp.splitlines():
                if ":" in line and "none" not in line.lower():
                    attr, val = [x.strip().lower() for x in line.split(":", 1)]
                    if attr and val:
                        v = embed([attr])[0]
                        match = next((c for c, cv in canon if float(v @ cv) >= 0.85), None)
                        if match is None:
                            canon.append((attr, v))
                            match = attr
                        eav = ("user", match, val)
                        break
        out.append(dict(s, eav=eav, protected=bool(eav)))
    return out


def run_detectors(obs, embed, question, dup, rel):
    det = dict(stale=detectors.detect_stale(obs), redundant=detectors.detect_redundant(obs, embed, dup),
               irrelevant=detectors.detect_irrelevant(obs, embed, question, rel), contradictory=set())
    flagged = set().union(*det.values())
    tot = sum(s["tokens"] for s in obs)
    return det, sum(s["tokens"] for s in obs if s["id"] in flagged) / tot


def build_contexts(q, obs, embed, dup, rel, summarizer):
    """Return {condition: segments} and metadata for one question."""
    t0 = time.perf_counter()
    det, rhat = run_detectors(obs, embed, q["question"], dup, rel)
    vecs = np.asarray(embed([s["text"] for s in obs]))
    qvec = np.asarray(embed([q["question"]]))[0]

    def hl(**kw):
        new, archive, log = repair.halflife_repair(obs, vecs, qvec, det, **kw)
        return new

    full_tokens = repair.total_tokens(obs)
    ctx = {"B0": obs}
    triggered = rhat > R_STAR
    ctx["HL"] = hl() if triggered else obs
    ctx["HL_noupdate"] = hl(ops=("merge", "remove")) if triggered else obs
    ctx["HL_nomerge"] = hl(ops=("update", "remove")) if triggered else obs
    ctx["HL_noremove"] = hl(ops=("update", "merge")) if triggered else obs
    ctx["HL_noprotect"] = hl(protect=False) if triggered else obs
    ctx["HL_noverify"] = ctx["HL"]
    ctx["HL_tok"] = hl() if full_tokens > 0.9 * TARGET_TOKENS else obs
    budget = repair.total_tokens(ctx["HL"])
    if budget < full_tokens:
        ctx["B1"] = repair.sliding_window(obs, budget)
        ctx["B2"] = repair.rolling_summary(obs, budget, summarizer)
        ctx["RND"] = repair.random_repair(obs, budget, repair.make_rng(SEED + zlib.crc32(q["question_id"].encode())))
        ctx["OLD"] = repair.oldest_first(obs, budget)
    else:
        ctx.update({k: obs for k in ("B1", "B2", "RND", "OLD")})
    ev = set(q["answer_session_ids"])
    ctx["ORACLE"] = [s for s in obs if s["session"] in ev]
    meta = dict(full_tokens=full_tokens, r_hat=rhat, triggered=triggered, repair_s=time.perf_counter() - t0,
                n_stale=len(det["stale"]), n_redundant=len(det["redundant"]), n_irrelevant=len(det["irrelevant"]))
    return ctx, meta


def stage_answer(a):
    questions = data.load_longmemeval("s")
    subset = data.stratified_subset(questions, SEED, STRATA, MAX_EVIDENCE)
    th = json.loads((SUMMARY / "e3_thresholds.json").read_text())
    dup, rel = th["dup"], th["rel"]
    embed = detectors.load_embedder()
    chat = llm.OllamaChat(a.model, num_ctx=TARGET_TOKENS + 2048, num_predict=64)
    summarizer_chat = llm.OllamaChat(a.model, num_ctx=TARGET_TOKENS + 2048, num_predict=220)
    digest = chat.digest()

    def summarize(text):
        return summarizer_chat.chat([{"role": "user", "content": "Summarize the conversation below in under 150 "
                                      "words. Keep every concrete fact (names, dates, numbers, preferences, "
                                      "changes).\n\n" + text}]).text.strip()

    xlog = JsonlLog("e4_extract")
    xlog.cache = {r["key"]: r["response"] for r in read_jsonl("e4_extract")}
    mlog = JsonlLog("e4_meta")
    alog = JsonlLog(f"e4_answers_{a.model.replace(':', '_')}")
    existing = read_jsonl(f"e4_answers_{a.model.replace(':', '_')}")
    done_recs = {r["key"]: r for r in existing}
    by_hash = {r["prompt_hash"]: dict(r, response=r.get("raw_response", r["response"])) for r in existing}
    for qi, q in enumerate(subset):
        if a.limit and qi >= a.limit:
            break
        if all(f"{a.model}|{q['question_id']}|{c}" in alog for c in CONDITIONS):
            continue
        segs = data.build_haystack_segments(q, TARGET_TOKENS, SEED + qi)
        obs = extract_eav(segs, chat, xlog, embed)
        ctx, meta = build_contexts(q, obs, embed, dup, rel, summarize)
        mlog.write(dict(key=f"{q['question_id']}", qid=q["question_id"], category=data.category(q), **meta))
        base = {}
        for cond in CONDITIONS:
            key = f"{a.model}|{q['question_id']}|{cond}"
            if key in alog:
                base[cond] = done_recs[key]
                continue
            msgs = render(ctx[cond], q)
            h = llm.prompt_hash(msgs)
            cached = h in by_hash
            if cached:
                src = by_hash[h]
                resp, ptoks, wall = src["response"], src["prompt_tokens"], src["wall_s"]
            else:
                r = chat.chat(msgs)
                resp, ptoks, wall = r.text, r.prompt_tokens, r.wall_s
            raw = resp
            rolled = 0
            # Verification with rollback: a repaired context that turns an answer into an abstention
            # (while the original context answered) is rolled back. No gold label is used.
            if cond.startswith("HL") and cond != "HL_noverify":
                b0 = base["B0"]
                if scoring.is_abstention(resp) and not b0["abstained"]:
                    resp, rolled, wall = b0["response"], 1, wall + b0["wall_s"]
            rec = dict(key=key, exp="e4", model=a.model, digest=digest, qid=q["question_id"],
                       category=data.category(q), condition=cond, prompt_hash=h, cached=int(cached),
                       prompt_tokens=ptoks, ref_tokens=repair.total_tokens(ctx[cond]), response=resp,
                       raw_response=raw, rolled_back=rolled, wall_s=wall,
                       abstained=int(scoring.is_abstention(resp)), n_segments=len(ctx[cond]))
            alog.write(rec)
            base[cond] = rec
            by_hash.setdefault(h, dict(rec, response=raw, wall_s=wall if not rolled else rec["wall_s"]))
    capture_env({a.model: digest})


def stage_judge(a):
    questions = {q["question_id"]: q for q in data.load_longmemeval("s")}
    judge = llm.OllamaChat(a.judge, num_ctx=2048, num_predict=4)
    digest = judge.digest()
    jlog = JsonlLog(f"e4_judge_{a.judge.replace(':', '_')}")
    done_resp = {}
    for rec in read_jsonl(f"e4_answers_{a.model.replace(':', '_')}"):
        q = questions[rec["qid"]]
        abstention = rec["category"] == "abstention"
        hkey = hashlib.sha256((rec["qid"] + "|" + rec["response"]).encode()).hexdigest()[:16]
        key = f"{a.judge}|{rec['key']}"
        if key in jlog:
            continue
        if hkey in done_resp:
            verdict, jresp = done_resp[hkey]
        else:
            prompt = scoring.judge_prompt(q["question"], q["answer"], rec["response"], q["question_type"], abstention)
            jresp = judge.chat([{"role": "user", "content": prompt}]).text
            verdict = int(scoring.parse_yes(jresp))
            done_resp[hkey] = (verdict, jresp)
        jlog.write(dict(key=key, judge=a.judge, judge_digest=digest, answer_key=rec["key"], qid=rec["qid"],
                        condition=rec["condition"], correct=verdict, judge_response=jresp))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["answer", "judge"], required=True)
    ap.add_argument("--model", default="llama3.2:3b")
    ap.add_argument("--judge", default="qwen2.5:3b")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    (stage_answer if args.stage == "answer" else stage_judge)(args)
