"""Repair operations and baselines. All functions map a segment list to a new segment list.

Segments are dicts (see inject.py). ``archive`` holds removed segments so removal is reversible.
"""
import random

import numpy as np

from . import tokens


def total_tokens(segs):
    return sum(s["tokens"] for s in segs)


# ---------------------------------------------------------------- baselines
def sliding_window(segs, budget):
    """B1: keep the newest segments that fit in `budget` tokens."""
    kept, used = [], 0
    for s in reversed(segs):
        if used + s["tokens"] > budget:
            break
        kept.append(s)
        used += s["tokens"]
    return kept[::-1]


def rolling_summary(segs, budget, summarize, keep_last=6):
    """B2: while over budget, condense the oldest half of the unprotected-by-recency segments into one."""
    segs = list(segs)
    guard = 0
    while total_tokens(segs) > budget and len(segs) > keep_last + 1 and guard < 8:
        guard += 1
        old, recent = segs[:-keep_last], segs[-keep_last:]
        half = max(2, len(old) // 2)
        head, tail = old[:half], old[half:]
        text = summarize("\n".join(f"{s['role']}: {s['text']}" for s in head))
        merged = dict(id="sum" + head[0]["id"], birth=head[-1]["birth"], role="user", text="Summary of earlier "
                      "conversation: " + text, tokens=tokens.count(text) + 8, type="summary", eav=None,
                      label=None, protected=False)
        segs = [merged] + tail + recent
    return segs


def random_repair(segs, budget, rng, protected_ids=(), keep_last=6):
    """Control: drop random unprotected, non-recent segments until under budget."""
    segs = list(segs)
    recent = {s["id"] for s in segs[-keep_last:]}
    order = [s["id"] for s in segs if s["id"] not in recent and s["id"] not in protected_ids]
    rng.shuffle(order)
    drop = set()
    used = total_tokens(segs)
    for sid in order:
        if used <= budget:
            break
        drop.add(sid)
        used -= next(s["tokens"] for s in segs if s["id"] == sid)
    return [s for s in segs if s["id"] not in drop]


def oldest_first(segs, budget, protected_ids=(), keep_last=6):
    """Control: drop the oldest unprotected, non-recent segments until under budget."""
    segs = list(segs)
    recent = {s["id"] for s in segs[-keep_last:]}
    drop, used = set(), total_tokens(segs)
    for s in segs:
        if used <= budget:
            break
        if s["id"] in recent or s["id"] in protected_ids:
            continue
        drop.add(s["id"])
        used -= s["tokens"]
    return [s for s in segs if s["id"] not in drop]


# ---------------------------------------------------------------- half-life-guided repair
def protection_set(segs, keep_last=6):
    """Segments never edited without verification: user constraints/preferences, current goal, last k turns."""
    prot = {s["id"] for s in segs if s.get("protected")}
    prot |= {s["id"] for s in segs[-keep_last:]}
    return prot


def update_change_record(old, new):
    return dict(new, text=f"{new['text']} (previously: {old['eav'][2]})", tokens=new["tokens"] + 8)


# [listing:repair]
def prune(segs, vecs, qvec, protected,
          keep_last=6, dup=0.92, rel=0.20):
    """MERGE duplicates, REMOVE off-topic."""
    cut = max(0, len(segs) - keep_last)
    old, recent = segs[:cut], segs[cut:]
    sim = vecs[:cut] @ vecs[:cut].T
    kept, archive = [], []
    for i, seg in enumerate(old):
        newer = (sim[i][i + 1:] > dup).any()
        offtopic = float(vecs[i] @ qvec) < rel
        if seg["id"] in protected:
            kept.append(seg)          # KEEP
        elif newer or offtopic:
            archive.append(seg)   # MERGE/REMOVE
        else:
            kept.append(seg)
    return kept + recent, archive
# [/listing]


def halflife_repair(segs, vecs, qvec, detections, ops=("update", "merge", "remove"), protect=True,
                    keep_last=6, dup=0.92, rel=0.20):
    """One repair pass. ``detections``: dict of id-sets from detectors.detect_all (stale, redundant, ...).

    Returns (new_segments, archive, log). Disabled ops/protection model the E5 ablations.
    """
    prot = protection_set(segs, keep_last) if protect else set()
    recent_ids = {s["id"] for s in segs[-keep_last:]}
    by_id = {s["id"]: s for s in segs}
    archive, log, drop, replace = [], [], set(), {}
    stale, red = detections.get("stale", set()), detections.get("redundant", set())
    irr, con = detections.get("irrelevant", set()), detections.get("contradictory", set())
    newest_by_key = {}
    for s in segs:
        if s["eav"] and s["role"] == "user":
            newest_by_key[(s["eav"][0], s["eav"][1])] = s
    for sid in stale:
        if "update" not in ops:
            continue
        s = by_id[sid]
        new = newest_by_key.get((s["eav"][0], s["eav"][1]))
        if new and new["id"] != sid:
            drop.add(sid)
            replace[new["id"]] = update_change_record(s, new)
            log.append(("UPDATE", sid, new["id"]))
    for sid in red:
        if "merge" in ops and sid not in recent_ids and (sid not in prot or not protect):
            drop.add(sid)
            log.append(("MERGE", sid, None))
    for sid in irr:
        if "remove" in ops and sid not in recent_ids and sid not in prot:
            drop.add(sid)
            log.append(("REMOVE", sid, None))
    for sid in con:
        if "update" in ops and sid not in recent_ids:
            drop.add(sid)
            log.append(("RESOLVE", sid, None))
    out = []
    for s in segs:
        if s["id"] in drop:
            archive.append(s)
            continue
        out.append(replace.get(s["id"], s))
    return out, archive, log


def verify_and_rollback(original, repaired, log, chat, probes, to_messages, max_probes=5):
    """Ask probe questions on both contexts; if the repaired context loses a probe the original passed, roll back.

    Returns (final_segments, rolled_back: bool, n_calls).
    """
    calls, lost = 0, False
    for p in probes[:max_probes]:
        ok_o = p["answer"].lower() in chat.chat(to_messages(original) + [dict(role="user", content=p["question"])]).text.lower()
        ok_r = p["answer"].lower() in chat.chat(to_messages(repaired) + [dict(role="user", content=p["question"])]).text.lower()
        calls += 2
        if ok_o and not ok_r:
            lost = True
            break
    return (original if lost else repaired), lost, calls


# ---------------------------------------------------------------- triggers
def half_life_trigger(rot_value, r_star=0.4):
    return rot_value > r_star


def token_budget_trigger(segs, budget):
    return total_tokens(segs) > budget


def make_rng(seed):
    return random.Random(seed)


def as_text(segs):
    return "\n".join(f"{s['role']}: {s['text']}" for s in segs)
