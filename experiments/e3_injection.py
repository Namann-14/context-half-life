"""E3: rot-injection suite (SYNTHETIC sessions with known ground truth).

Part A (CPU only): detector precision/recall per decay mode; thresholds tuned on the dev sessions only.
Part B (reader): accuracy on current-value probes at checkpoints every 4 turns (rot session), and at the
end for a paired *twin* with the same turn structure and no rot.

    python experiments/e3_injection.py --model llama3.2:3b --sessions 40
"""
import argparse
import itertools
import json

import numpy as np

from common import JsonlLog, RAW, SUMMARY, capture_env
from context_half_life import SEED, detectors, inject, llm, rot, scoring

DEV_FRACTION = 0.2
CHECKPOINTS = list(range(4, 41, 4))


def observe(session):
    """What a detector may see: text only. EAV is re-extracted by rules; labels and flags are hidden."""
    out = []
    for s in session["segments"]:
        eav = detectors.extract_eav(s["text"], session["entity"])
        out.append(dict(s, eav=eav, label=None, protected=bool(eav and s["role"] == "user")))
    return out


def truth_sets(session):
    sets = {m: set() for m in ("stale", "contradictory", "redundant", "irrelevant")}
    for s in session["segments"]:
        if s["label"]:
            sets[s["label"]].add(s["id"])
    return sets


def cached(embed):
    memo = {}

    def f(texts):
        miss = [t for t in dict.fromkeys(texts) if t not in memo]
        if miss:
            for t, v in zip(miss, embed(miss)):
                memo[t] = v
        return np.array([memo[t] for t in texts])

    return f


def detect(session, embed, nli, dup, rel, upto=None):
    obs = observe(session)
    if upto is not None:
        obs = [s for s in obs if s["birth"] <= upto]
    # "current task" = the last four user chat messages visible at this point
    recent = [x["text"] for x in obs if x["role"] == "user" and x["type"] == "chat"][-4:]
    query = " ".join(recent) if recent else session["probes"][0]["question"]
    return obs, detectors.detect_all(obs, embed, nli, query, dup, rel)


def f1(p, r):
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def gold_at(session, t):
    """Current value of each attribute at turn t (only attributes already stated)."""
    latest = {}
    for s in session["segments"]:
        if s["eav"] and s["role"] == "user" and s["birth"] <= t:
            latest[s["eav"][1]] = s["eav"][2]
    return latest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="llama3.2:3b")
    ap.add_argument("--sessions", type=int, default=40)
    ap.add_argument("--skip-reader", action="store_true")
    a = ap.parse_args()
    sessions = [inject.generate_session(SEED + i) for i in range(a.sessions)]
    n_dev = max(2, int(DEV_FRACTION * len(sessions)))
    dev, test = sessions[:n_dev], sessions[n_dev:]
    embed, nli = cached(detectors.load_embedder()), detectors.load_nli()

    # ---- thresholds on dev only
    best = None
    for dup, rel in itertools.product([0.85, 0.90, 0.95], [0.05, 0.10, 0.15, 0.20, 0.25]):
        score = []
        for s in dev:
            _, det = detect(s, embed, nli, dup, rel)
            t = truth_sets(s)
            score += [f1(*detectors.precision_recall(det["redundant"], t["redundant"])),
                      f1(*detectors.precision_recall(det["irrelevant"], t["irrelevant"]))]
        m = float(np.mean(score))
        if best is None or m > best[0]:
            best = (m, dup, rel)
    _, dup, rel = best
    SUMMARY.mkdir(parents=True, exist_ok=True)
    (SUMMARY / "e3_thresholds.json").write_text(json.dumps(dict(dup=dup, rel=rel, tuned_on="dev", n_dev=n_dev,
                                                                 dev_mean_f1=best[0]), indent=2))

    # ---- part A: detectors on the test sessions + Rot Index series
    log = JsonlLog("e3_detect")
    for s in test:
        key = f"detect|{s['seed']}"
        if key in log:
            continue
        obs, det = detect(s, embed, nli, dup, rel)
        t = truth_sets(s)
        rec = dict(key=key, exp="e3", part="detect", seed=s["seed"], change_point=s["change_point"],
                   n_segments=len(obs))
        for mode in t:
            p, r = detectors.precision_recall(det[mode], t[mode])
            rec[mode] = dict(precision=p, recall=r, n_true=len(t[mode]), n_pred=len(det[mode]))
        # Rot Index series: share of tokens in segments flagged (any mode) on the prefix context C(t)
        series = []
        for turn in range(1, s["n_turns"] + 1):
            o, d = detect(s, embed, nli, dup, rel, upto=turn)
            flagged = set().union(*d.values())
            tot = sum(x["tokens"] for x in o)
            series.append(sum(x["tokens"] for x in o if x["id"] in flagged) / tot)
        rec["rot_series"] = series
        rec["onset_rot"] = rot.onset_from_series(list(range(1, s["n_turns"] + 1)), series)
        log.write(rec)

    if a.skip_reader:
        return
    # ---- part B: reader accuracy
    chat = llm.OllamaChat(a.model, num_ctx=8192, num_predict=16)
    digest = chat.digest()
    rlog = JsonlLog(f"e3_reader_{a.model.replace(':', '_')}")
    for s in test:
        variants = [("rot", s, CHECKPOINTS), ("twin", inject.twin(s), [s["n_turns"]])]
        for variant, sess, cps in variants:
            for t in cps:
                gold = gold_at(s, t)
                ctx = [x for x in sess["segments"] if x["birth"] <= t]
                for probe in s["probes"]:
                    attr = probe["attr"]
                    if attr not in gold:
                        continue
                    key = f"{a.model}|{variant}|{s['seed']}|{t}|{attr}"
                    if key in rlog:
                        continue
                    msgs = inject.to_messages(ctx) + [dict(role="user", content=probe["question"])]
                    r = chat.chat(msgs)
                    rlog.write(dict(key=key, exp="e3", part="reader", model=a.model, digest=digest,
                                    variant=variant, seed=s["seed"], turn=t, attr=attr,
                                    change_point=s["change_point"], gold=gold[attr],
                                    correct=int(scoring.contains_answer(r.text, gold[attr])),
                                    prompt_tokens=r.prompt_tokens, response=r.text, wall_s=r.wall_s))
    capture_env({a.model: digest})


if __name__ == "__main__":
    main()
