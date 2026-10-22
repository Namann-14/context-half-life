ABSTRACT = [
    ("Abstract:", """Large language models (LLMs) reason well over short exchanges, but their performance
     erodes as interactions stretch across many turns. We call this decline <i>context rot</i>: the gradual
     accumulation of stale, contradictory, redundant, and irrelevant material inside the context window.
     Common fixes (truncation, summarization, compression, retrieval) shrink the context without measuring
     how quickly its contents decay."""),
    ("Objectives:", """We define a <i>Context Half-Life</i>, the number of turns after which a piece of
     information has a 50% chance of no longer helping the model answer, and ask whether it can be measured
     and used to repair a context."""),
    ("Methods:", """We estimate half-lives with survival analysis (Weibull and Kaplan–Meier fits), summarise a
     session with a Rot Index, and use both to drive a repair loop that UPDATEs outdated facts, MERGEs
     duplicates, and REMOVEs irrelevant material behind a protection set and verification with rollback.
     In a deliberately small study on one laptop (one 3-billion-parameter open model, 35 LongMemEval
     questions, 20 facts per age, synthetic rot-injection sessions) we run five experiments and report
     every outcome, including those that contradict our seven hypotheses."""),
    ("Results:", """Decay depends on content: a changing value fell to [$e2.ageing.changing.S80|pct0]% correct
     after 80 turns (Weibull half-life [$e2.ageing.changing.wb_H|f0] turns, 95% CI
     [$e2.ageing.changing.wb_H_lo|f0]–[$e2.ageing.changing.wb_H_hi|f0]), a stable preference did not decay
     at all, and a number in a tool output kept [$e2.ageing.tool.S80|pct0]%. Rewording the question so that
     it shares no content word with the evidence cut needle-in-a-haystack accuracy from
     [$e1.acc.literal|pct0]% to [$e1.acc.paraphrase|pct0]%. Detectors found stale and contradictory
     segments perfectly on synthetic sessions but flagged irrelevant text with precision of only
     [$e3.irrelevant.precision|pct0]%. Half-life-guided repair cut input tokens by
     [$e4.saving.HL|pct0]% but did not improve accuracy ([$e4.acc.HL|pct0]% against
     [$e4.acc.B0|pct0]% for full context), raised hallucination, and cost more time than it saved; of
     seven hypotheses, one was partly supported, four were not supported or could not be tested, and two
     were refuted at this scale."""),
    ("Conclusion:", """Content-dependent decay is measurable even with a 3B model, but at this scale
     measurement did not translate into better repair. We release code, raw logs, and negative results so
     that larger studies can build on them."""),
]

KEYWORDS = ("Context rot, context half-life, long-context reasoning, lost in the middle, "
            "needle-in-a-haystack, survival analysis, retrieval-augmented generation, context engineering")


def _ci(prefix, fmt="pct0", sep="–"):
    """'m (lo–hi)' for a measured quantity stored as prefix, prefix.lo, prefix.hi."""
    return f"[${prefix}|{fmt}] ([${prefix}.lo|{fmt}]{sep}[${prefix}.hi|{fmt}])"


def _wb(kind, field, fmt="f0"):
    return (f"[$e2.ageing.{kind}.{field}|{fmt}] ([$e2.ageing.{kind}.{field}_lo|{fmt}]–"
            f"[$e2.ageing.{kind}.{field}_hi|{fmt}])")
