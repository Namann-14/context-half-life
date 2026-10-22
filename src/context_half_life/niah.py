"""Needle-in-a-haystack grid with literal and zero-overlap paraphrased questions."""
import re

# Each needle: statement, literal question, paraphrased question sharing no content word, answer.
NEEDLES = [
    dict(statement="The secret ingredient in Maria's famous stew is cardamom.",
         literal="What is the secret ingredient in Maria's famous stew?",
         paraphrase="Which spice does the lady known for her soup always add?", answer="cardamom"),
    dict(statement="The access code for the old observatory gate is 7316.",
         literal="What is the access code for the old observatory gate?",
         paraphrase="Which digits open the entrance of the stargazing building?", answer="7316"),
    dict(statement="Captain Idris keeps his compass inside a blue tin box.",
         literal="Where does Captain Idris keep his compass?",
         paraphrase="In what container does the ship's skipper store his navigation tool?",
         answer="blue tin box"),
    dict(statement="The village of Orrin celebrates its harvest festival on the third of October.",
         literal="When does the village of Orrin celebrate its harvest festival?",
         paraphrase="On what date do the people of that hamlet hold their crop celebration?",
         answer="third of october"),
    dict(statement="Professor Vale's missing manuscript was found behind a brass radiator.",
         literal="Where was Professor Vale's missing manuscript found?",
         paraphrase="Which metal heating unit hid the lecturer's lost papers?",
         answer="brass radiator"),
]

_STOP = set("a an the of in on at to is was were what which who when where how does do did for by with "
            "from and or that this these those it its his her their my our your s".split())


def content_words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP}


def overlap(needle, question):
    return content_words(needle["statement"]) & content_words(question)


def check_needles():
    """Literal wording must overlap the needle; paraphrases must share no content word."""
    for n in NEEDLES:
        assert overlap(n, n["literal"]), n
        assert not overlap(n, n["paraphrase"]), (n["paraphrase"], overlap(n, n["paraphrase"]))


def build_haystack(text, needle, n_tokens, depth, count):
    """Cut `text` to n_tokens (measured by `count`) and insert the needle at fractional depth."""
    words = text.split()
    lo, hi = 0, len(words)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if count(" ".join(words[:mid])) <= n_tokens:
            lo = mid
        else:
            hi = mid - 1
    words = words[:lo]
    pos = int(round(depth * len(words)))
    return " ".join(words[:pos] + [needle["statement"]] + words[pos:])
