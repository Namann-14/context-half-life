"""Dataset access: LongMemEval (cleaned, MIT) and public-domain Gutenberg haystack text."""
import json
import random
import urllib.request
from pathlib import Path

from . import tokens

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
LME_REPO = "xiaowu0162/longmemeval-cleaned"
LME_FILES = {"s": "longmemeval_s_cleaned.json", "oracle": "longmemeval_oracle.json"}
GUTENBERG = {
    "pride_and_prejudice": "https://www.gutenberg.org/cache/epub/1342/pg1342.txt",
    "moby_dick": "https://www.gutenberg.org/cache/epub/2701/pg2701.txt",
    "frankenstein": "https://www.gutenberg.org/cache/epub/84/pg84.txt",
}
# Per-category question counts for the E4 subset (total 100).
E4_STRATA = {"knowledge-update": 25, "temporal-reasoning": 25, "multi-session": 20,
             "single-session-user": 10, "single-session-preference": 5, "abstention": 15}


def fetch_longmemeval():
    """Download the cleaned LongMemEval files; return the resolved dataset commit sha."""
    from huggingface_hub import HfApi, hf_hub_download
    sha = HfApi().dataset_info(LME_REPO).sha
    DATA.mkdir(exist_ok=True)
    for name in LME_FILES.values():
        hf_hub_download(LME_REPO, name, repo_type="dataset", revision=sha, local_dir=DATA)
    return sha


def fetch_gutenberg():
    d = DATA / "gutenberg"
    d.mkdir(parents=True, exist_ok=True)
    for name, url in GUTENBERG.items():
        dst = d / f"{name}.txt"
        if not dst.exists():
            req = urllib.request.Request(url, headers={"User-Agent": "context-half-life-research"})
            dst.write_bytes(urllib.request.urlopen(req, timeout=60).read())


def load_gutenberg_text():
    parts = []
    for p in sorted((DATA / "gutenberg").glob("*.txt")):
        t = p.read_text(encoding="utf8", errors="ignore")
        a, b = t.find("*** START"), t.rfind("*** END")
        parts.append(t[a:b] if a >= 0 and b > a else t)
    return "\n".join(" ".join(p.split()) for p in parts)


def load_longmemeval(variant="s"):
    return json.loads((DATA / LME_FILES[variant]).read_text(encoding="utf8"))


def category(q):
    return "abstention" if q["question_id"].endswith("_abs") else q["question_type"]


def session_tokens(session):
    return sum(tokens.count(t["content"]) + 4 for t in session)


def stratified_subset(questions, seed, strata=E4_STRATA, max_evidence_tokens=9000):
    """Pick questions per stratum at random among those whose evidence sessions fit the budget."""
    rng = random.Random(seed)
    chosen = []
    for cat, n in strata.items():
        pool = []
        for q in questions:
            if category(q) != cat:
                continue
            ev = [s for s, sid in zip(q["haystack_sessions"], q["haystack_session_ids"])
                  if sid in set(q["answer_session_ids"])]
            if sum(session_tokens(s) for s in ev) <= max_evidence_tokens:
                pool.append(q["question_id"])
        rng.shuffle(pool)
        chosen += pool[:n]
        if len(pool) < n:
            print(f"warning: stratum {cat} has only {len(pool)} eligible questions (wanted {n})")
    index = {q["question_id"]: q for q in questions}
    return [index[i] for i in chosen]


def build_haystack_segments(q, target_tokens, seed):
    """Evidence sessions plus randomly chosen distractor sessions of the same question, in date order.

    Each message becomes a segment. Returns list of segment dicts (see inject.py).
    """
    rng = random.Random(seed)
    ev_ids = set(q["answer_session_ids"])
    sessions = list(zip(q["haystack_session_ids"], q["haystack_dates"], q["haystack_sessions"]))
    chosen = [x for x in sessions if x[0] in ev_ids]
    used = sum(session_tokens(x[2]) for x in chosen)
    others = [x for x in sessions if x[0] not in ev_ids]
    rng.shuffle(others)
    for x in others:
        t = session_tokens(x[2])
        if used + t > target_tokens:
            continue
        chosen.append(x)
        used += t
    chosen.sort(key=lambda x: x[1])
    segs = []
    for si, (sid, date, sess) in enumerate(chosen):
        for mi, m in enumerate(sess):
            text = f"[{date}] {m['content']}" if mi == 0 else m["content"]
            segs.append(dict(id=f"{sid}:{mi}", birth=si, role=m["role"], text=text,
                             tokens=tokens.count(text) + 4, type="chat", eav=None, label=None,
                             protected=False, session=sid, date=date))
    return segs


def chat_pairs(questions, seed, n=400, max_words=120):
    """(user, assistant) turn pairs from LongMemEval haystack sessions, each message cut to max_words.

    Messages from the *evidence* sessions are skipped so filler never contains task-relevant facts.
    """
    rng = random.Random(seed)
    pairs = []
    for q in questions:
        ev = set(q["answer_session_ids"])
        for sid, sess in zip(q["haystack_session_ids"], q["haystack_sessions"]):
            if sid in ev:
                continue
            for a, b in zip(sess[::2], sess[1::2]):
                if a["role"] == "user" and b["role"] == "assistant":
                    pairs.append((" ".join(a["content"].split()[:max_words]),
                                  " ".join(b["content"].split()[:max_words])))
    rng.shuffle(pairs)
    return pairs[:n]
