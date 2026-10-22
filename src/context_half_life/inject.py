"""Synthetic rot-injection generator (SYNTHETIC data with known ground truth).

A session is a list of segments. Each segment is a dict with
  id, birth (turn), role, text, tokens, type, eav (entity, attribute, value) or None,
  label in {None, 'stale', 'contradictory', 'redundant', 'irrelevant'}, protected (bool).
The generator also returns probe questions about the attributes' *current* values and the
change point c, the first turn at which an earlier value is superseded.
A paired "twin" session has identical length but replaces every injected segment by neutral filler.
"""
import random

from . import tokens

ENTITIES = ["Asha", "Ravi", "Meera", "Karan", "Tara", "Dev"]
ATTRIBUTES = {
    "city": ["Pune", "Kochi", "Jaipur", "Mysuru", "Indore", "Surat", "Nagpur", "Agra"],
    "exam date": ["12 March", "19 March", "2 April", "27 April", "9 May", "30 May"],
    "room": ["B-204", "C-117", "A-310", "D-025", "E-442", "F-208"],
    "mentor": ["Dr. Rao", "Dr. Iyer", "Dr. Bose", "Dr. Kulkarni", "Dr. Menon", "Dr. Sethi"],
}
TOPICS = [
    "binary search trees", "hash tables", "graph traversal", "dynamic programming", "sorting stability",
    "process scheduling", "virtual memory", "TCP congestion control", "relational joins", "database indexing",
    "recursion", "linked lists", "heaps", "tries", "union-find", "shortest paths", "minimum spanning trees",
    "regular expressions", "finite automata", "compilers", "garbage collection", "cache coherence",
    "deadlocks", "semaphores", "public-key encryption", "hash functions", "normalisation", "transactions",
    "REST design", "unit testing", "version control", "linear regression", "gradient descent", "overfitting",
    "decision trees", "k-means clustering", "Bayes rule", "matrix rank", "eigenvalues", "Fourier transforms",
    "Boolean algebra", "logic gates", "pipelining", "interrupt handling", "paging", "DNS lookup",
    "load balancing", "message queues", "big-O notation", "amortised analysis", "bit manipulation",
    "floating-point error", "string matching", "topological sorting", "bloom filters", "skip lists",
    "B-trees", "red-black trees", "memoisation", "greedy algorithms",
]
USER_T = ["Can you explain {t} to me?", "What should I revise first about {t}?",
          "I keep mixing up the details of {t}. Help?", "Give me a quick summary of {t}, please."]
ASST_T = ["Sure. With {t}, start from the definition, then trace one tiny example by hand.",
          "A good order for {t} is: core idea, standard operations, then typical pitfalls.",
          "The usual trap with {t} is skipping edge cases, so test an empty input first.",
          "In short, {t} trades extra bookkeeping for speed; practise on small cases."]


def neutral_pair(k):
    t = TOPICS[k % len(TOPICS)]
    return USER_T[(k // len(TOPICS) + k) % 4].format(t=t), ASST_T[(k // len(TOPICS) + 2 * k + 1) % 4].format(t=t)


def neutral_text(k):
    return neutral_pair(k // 2)[k % 2]


IRRELEVANT_LOG = ("[build log] compiling module {m} ... warning: unused variable x{n} ... "
                  "linking ... done in {s}.{n}s ... cache miss ratio {n}% ... retrying flaky step {m}")


def _seg(sid, birth, role, text, typ, eav=None, label=None, protected=False):
    return dict(id=sid, birth=birth, role=role, text=text, tokens=tokens.count(text), type=typ,
                eav=eav, label=label, protected=protected)


def generate_session(seed, n_turns=40, n_attrs=3, n_redundant=2, n_irrelevant=3, n_contradictions=1):
    rng = random.Random(seed)
    segs, probes, sid = [], [], 0
    entity = rng.choice(ENTITIES)
    attrs = rng.sample(list(ATTRIBUTES), n_attrs)
    change_point = rng.randint(n_turns // 4, n_turns // 2)
    plan = {}  # turn -> list of ("state"|"update", attr, value)
    current = {}
    for attr in attrs:
        v1, v2 = rng.sample(ATTRIBUTES[attr], 2)
        t1 = rng.randint(1, max(1, change_point - 2))
        t2 = change_point if not current else rng.randint(change_point, change_point + n_turns // 4)
        current[attr] = v2
        plan.setdefault(t1, []).append(("state", attr, v1))
        plan.setdefault(t2, []).append(("update", attr, v2))
    redundant_src, rows = [], []

    def nid():
        nonlocal sid
        sid += 1
        return f"s{sid}"

    for t in range(1, n_turns + 1):
        for kind, attr, val in plan.get(t, []):
            if kind == "state":
                text = f"For the record, my {attr} is {val}."
                segs.append(_seg(nid(), t, "user", text, "preference", (entity, attr, val), "stale", True))
            else:
                text = f"Correction: my {attr} is now {val}, the earlier value no longer applies."
                segs.append(_seg(nid(), t, "user", text, "preference", (entity, attr, val), None, True))
        u, a = neutral_pair(t)
        segs.append(_seg(nid(), t, "user", u, "chat"))
        segs.append(_seg(nid(), t, "assistant", a, "chat"))
        if t in rng.sample(range(5, n_turns + 1), n_irrelevant):
            segs.append(_seg(nid(), t, "tool", IRRELEVANT_LOG.format(m=rng.choice("abcdef"), n=rng.randint(1, 9),
                                                                      s=rng.randint(1, 9)),
                             "tool", label="irrelevant"))
        if t % 7 == 0:
            redundant_src.append(t)
    # Redundant: re-paste an earlier neutral explanation verbatim later in the session.
    chat_segs = [s for s in segs if s["type"] == "chat" and s["role"] == "assistant"]
    for k in range(min(n_redundant, len(chat_segs) // 2)):
        src = chat_segs[k]
        birth = min(n_turns, src["birth"] + rng.randint(8, 15))
        src["label"] = "redundant"  # the older copy is the redundant one; the newest copy is kept
        segs.append(_seg(nid(), birth, "assistant", src["text"], "chat"))
    # Contradictory: the assistant states a wrong value; a later source states the right one.
    for _ in range(n_contradictions):
        attr = rng.choice(attrs)
        wrong = rng.choice([v for v in ATTRIBUTES[attr] if v != current[attr]])
        t = rng.randint(change_point + 1, min(n_turns - 3, change_point + 6))
        segs.append(_seg(nid(), t, "assistant", f"Just confirming: your {attr} is {wrong}.", "chat",
                         (entity, attr, wrong), "contradictory"))
    segs.sort(key=lambda s: (s["birth"], s["id"]))
    for attr in attrs:
        probes.append(dict(question=f"What is {entity}'s {attr} now? Reply with the value only.",
                           answer=current[attr], attr=attr))
    return dict(seed=seed, n_turns=n_turns, change_point=change_point, entity=entity,
                segments=segs, probes=probes)


def twin(session):
    """Same turn structure and similar token counts, but no rot.

    Every injected segment (old state, redundant copy, contradiction, irrelevant log) is replaced by
    neutral filler; the user's *current* value statements are kept so probes stay answerable.
    """
    segs = []
    for s in session["segments"]:
        if s["label"] is not None:
            text = neutral_text(200 + 2 * s["birth"] + len(segs))
            segs.append(dict(s, text=text, tokens=tokens.count(text), eav=None, label=None, protected=False,
                             type="chat"))
        else:
            segs.append(dict(s))
    return dict(session, segments=segs)


def to_messages(segments):
    """Render segments as chat messages (tool output is shown as a user-side message)."""
    return [{"role": "assistant" if s["role"] == "assistant" else "user", "content": s["text"]}
            for s in segments]
