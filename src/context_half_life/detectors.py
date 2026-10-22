"""Tier-1 detectors for the four decay modes.

``embed`` is any callable list[str] -> array [n, d] of L2-normalised vectors, so the detectors can be
tested without a model. ``nli`` is a callable (premise, hypothesis) -> probability of contradiction.
"""
import re

import numpy as np

_EAV_PATTERNS = [
    re.compile(r"my (?P<attr>[a-z ]+?) is (?:now )?(?P<val>[^,.]+)", re.I),
    re.compile(r"your (?P<attr>[a-z ]+?) is (?P<val>[^,.]+)", re.I),
    re.compile(r"I (?:currently )?live in (?P<val>[^,.]+)", re.I),
]


def extract_eav(text, entity):
    """Rule-based entity-attribute-value extraction for templated statements; None if no match."""
    for p in _EAV_PATTERNS:
        m = p.search(text)
        if m:
            attr = m.groupdict().get("attr") or "city"
            return (entity, attr.strip().lower(), m.group("val").strip())
    return None


def detect_stale(segments):
    """Ids of segments whose (entity, attribute) value is superseded by a later *user* statement."""
    latest = {}
    for s in segments:
        if s["eav"] and s["role"] == "user":
            latest[(s["eav"][0], s["eav"][1])] = (s["birth"], s["eav"][2], s["id"])
    out = set()
    for s in segments:
        if s["eav"] and s["role"] == "user":
            key = (s["eav"][0], s["eav"][1])
            if latest[key][2] != s["id"] and latest[key][1] != s["eav"][2]:
                out.add(s["id"])
    return out


def detect_redundant(segments, embed, dup=0.92):
    """Ids of segments having a *later* near-duplicate; the newest copy is kept."""
    vecs = np.asarray(embed([s["text"] for s in segments]))
    sim = vecs @ vecs.T
    out = set()
    for i, s in enumerate(segments):
        later = sim[i, i + 1:]
        if len(later) and (later > dup).any():
            out.add(s["id"])
    return out


def detect_irrelevant(segments, embed, query, rel=0.20):
    """Ids of unprotected segments with low similarity to the current query."""
    vecs = np.asarray(embed([s["text"] for s in segments] + [query]))
    sims = vecs[:-1] @ vecs[-1]
    return {s["id"] for s, v in zip(segments, sims) if v < rel and not s["protected"]}


def detect_contradictory(segments, nli, threshold=0.5):
    """Ids of earlier segments of a pair on the same entity+attribute that NLI judges contradictory.

    Only pairs with differing extracted values are scored. The *older* statement is flagged unless
    it is a user statement (users outrank assistants), in which case the assistant's one is flagged.
    """
    out = set()
    by_key = {}
    for s in segments:
        if s["eav"]:
            by_key.setdefault((s["eav"][0], s["eav"][1]), []).append(s)
    for group in by_key.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a["eav"][2] == b["eav"][2]:
                    continue
                if nli(a["text"], b["text"]) < threshold:
                    continue
                if a["role"] == "assistant" and b["role"] == "assistant":
                    out.add(a["id"])
                elif a["role"] == "assistant":
                    out.add(a["id"])
                elif b["role"] == "assistant":
                    out.add(b["id"])
    return out


def detect_all(segments, embed, nli, query, dup=0.92, rel=0.20):
    return dict(stale=detect_stale(segments), redundant=detect_redundant(segments, embed, dup),
                irrelevant=detect_irrelevant(segments, embed, query, rel),
                contradictory=detect_contradictory(segments, nli))


def precision_recall(predicted, truth):
    """Sets of ids. Precision is 1.0 when nothing is predicted; recall is 1.0 when nothing is true."""
    tp = len(predicted & truth)
    p = tp / len(predicted) if predicted else 1.0
    r = tp / len(truth) if truth else 1.0
    return p, r


def load_embedder(name="sentence-transformers/all-MiniLM-L6-v2"):
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(name, device="cpu")
    return lambda texts: m.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)


def load_nli(name="cross-encoder/nli-deberta-v3-xsmall"):
    """Returns f(premise, hypothesis) -> P(contradiction). Label order: contradiction, entailment, neutral."""
    from sentence_transformers import CrossEncoder
    m = CrossEncoder(name, device="cpu")

    def f(premise, hypothesis):
        logits = np.asarray(m.predict([(premise, hypothesis)])[0], float)
        e = np.exp(logits - logits.max())
        return float((e / e.sum())[0])

    return f
