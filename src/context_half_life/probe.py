"""Fact-ageing probe: plant a fact, age it with filler turns, ask for it back."""
import random


# [listing:probe]
def msg(role, text):
    return {"role": role, "content": text}


def build_context(fact, filler, age, rng):
    """Fact first, then `age` filler turns."""
    msgs = [msg("user", fact["statement"]),
            msg("assistant", "Noted!")]
    for u, a in rng.sample(filler, age):
        msgs += [msg("user", u),
                 msg("assistant", a)]
    msgs.append(msg("user", fact["question"]))
    return msgs


def still_useful(chat, fact, filler, age, rng):
    msgs = build_context(fact, filler, age, rng)
    reply = chat.chat(msgs).text.lower()
    return fact["answer"].lower() in reply
# [/listing]


def nested_filler(pool, age, seed):
    """First `age` pairs of a seeded shuffle, so age 5 is a prefix of age 10."""
    r = random.Random(seed)
    order = list(range(len(pool)))
    r.shuffle(order)
    return [pool[i] for i in order[:age]]


_FOODS = ["mango", "pistachio", "cardamom", "walnut", "papaya", "jaggery", "sesame", "tamarind"]
_CITIES = ["Pune", "Kochi", "Jaipur", "Mysuru", "Indore", "Surat", "Nagpur", "Agra", "Bhopal", "Patna",
           "Ranchi", "Shimla", "Madurai", "Vellore", "Raipur", "Dehradun"]
_SERVICES = ["billing", "search", "auth", "gateway", "queue", "export", "sync", "report"]
_COLOURS = ["amber", "indigo", "olive", "coral", "slate"]


def make_fact(kind, i, rng):
    """kind: 'preference' | 'changing' | 'tool'. Generated values: no real personal data."""
    if kind == "preference":
        code = f"{rng.choice(_COLOURS)}-{100 + i}"
        return dict(kind=kind,
                    statement=f"By the way, my favourite spice is {_FOODS[i % len(_FOODS)]}, "
                              f"and my project codename is {code}.",
                    question="What is my project codename? Reply with the codename only.",
                    answer=code)
    if kind == "changing":
        c1, c2 = rng.sample(_CITIES, 2)
        return dict(kind=kind, statement=f"I currently live in {c1}.",
                    update=f"Update: I have moved, and I now live in {c2}.",
                    question="Which city do I live in now? Reply with the city only.",
                    answer=c2, stale=c1)
    if kind == "tool":
        svc = _SERVICES[i % len(_SERVICES)]
        val = rng.randint(1000, 9999)
        lines = [f"[tool:status] {s} ok latency={rng.randint(5, 90)}ms" for s in _SERVICES if s != svc]
        lines.append(f"[tool:status] {svc} ok build={val} latency={rng.randint(5, 90)}ms")
        lines += [f"[tool:trace] span={rng.randint(10**5, 10**6)} ms={rng.randint(1, 50)}" for _ in range(12)]
        return dict(kind=kind, statement="Tool output:\n" + "\n".join(lines),
                    question=f"From the tool output earlier, what is the build number of the {svc} "
                             f"service? Digits only.",
                    answer=str(val))
    raise ValueError(kind)
