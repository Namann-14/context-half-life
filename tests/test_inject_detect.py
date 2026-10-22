import zlib

import numpy as np

from context_half_life import detectors, inject, niah, repair


def fake_embed(texts):
    """Bag-of-words hashing embedding, deterministic and model-free."""
    out = np.zeros((len(texts), 64))
    for i, t in enumerate(texts):
        for w in t.lower().split():
            out[i, zlib.crc32(w.encode()) % 64] += 1
    n = np.linalg.norm(out, axis=1, keepdims=True)
    return out / np.maximum(n, 1e-9)


def test_generator_is_deterministic_and_labelled():
    a, b = inject.generate_session(5), inject.generate_session(5)
    assert [s["text"] for s in a["segments"]] == [s["text"] for s in b["segments"]]
    labels = {s["label"] for s in a["segments"]}
    assert {"stale", "irrelevant", "redundant", "contradictory"} <= labels
    assert len(a["probes"]) == 3 and 1 <= a["change_point"] <= a["n_turns"]


def test_twin_has_no_labels():
    t = inject.twin(inject.generate_session(5))
    assert all(s["label"] is None for s in t["segments"])
    cur = [s for s in t["segments"] if s["eav"]]
    assert len(cur) == 3 and all(s["role"] == "user" for s in cur)  # only current values remain


def test_stale_detector_finds_all_stale():
    sess = inject.generate_session(11)
    truth = {s["id"] for s in sess["segments"] if s["label"] == "stale"}
    assert detectors.detect_stale(sess["segments"]) == truth


def test_redundancy_detector_recall():
    sess = inject.generate_session(11)
    truth = {s["id"] for s in sess["segments"] if s["label"] == "redundant"}
    pred = detectors.detect_redundant(sess["segments"], fake_embed)
    assert truth <= pred


def test_precision_recall_edges():
    assert detectors.precision_recall(set(), set()) == (1.0, 1.0)
    assert detectors.precision_recall({"a", "b"}, {"a"}) == (0.5, 1.0)


def test_repair_keeps_current_values_and_recent_and_saves_tokens():
    segs = inject.generate_session(3)["segments"]
    det = dict(stale=detectors.detect_stale(segs),
               redundant=detectors.detect_redundant(segs, fake_embed),
               irrelevant={s["id"] for s in segs if s["label"] == "irrelevant"}, contradictory=set())
    new, archive, log = repair.halflife_repair(segs, None, None, det)
    ids = {s["id"] for s in new}
    current = {s["id"] for s in segs if s["eav"] and s["role"] == "user" and s["label"] is None}
    assert current <= ids
    assert {s["id"] for s in segs[-6:]} <= ids
    assert repair.total_tokens(new) < repair.total_tokens(segs)
    assert len(archive) + len(new) == len(segs)


def test_update_leaves_change_record():
    segs = inject.generate_session(3)["segments"]
    new, _, _ = repair.halflife_repair(segs, None, None, dict(stale=detectors.detect_stale(segs)))
    assert any("previously:" in s["text"] for s in new)


def test_ablation_disabling_update_keeps_stale():
    segs = inject.generate_session(3)["segments"]
    stale = detectors.detect_stale(segs)
    new, _, _ = repair.halflife_repair(segs, None, None, dict(stale=stale), ops=("merge", "remove"))
    assert stale <= {s["id"] for s in new}


def test_baselines_respect_budget():
    segs = inject.generate_session(3)["segments"]
    budget = repair.total_tokens(segs) // 2
    assert repair.total_tokens(repair.sliding_window(segs, budget)) <= budget
    r = repair.random_repair(segs, budget, repair.make_rng(1))
    assert len(r) < len(segs)


def test_niah_paraphrases_share_no_content_word():
    niah.check_needles()


def test_haystack_insertion_depth():
    needle = niah.NEEDLES[0]
    text = " ".join(f"w{i}" for i in range(1000))
    hay = niah.build_haystack(text, needle, 400, 0.5, lambda s: len(s.split()))
    assert needle["statement"] in hay
    before = hay[:hay.index(needle["statement"])].split()
    assert 0.4 < len(before) / len(hay.split()) < 0.6
