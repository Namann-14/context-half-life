"""Content of the paper, kept separate from the document builder.

Inline markup understood by build_paper.py:
  <b>..</b>  bold      <i>..</i>  italic      <code>..</code>  monospace
  <super>..</super> / <sub>..</sub>  superscript / subscript
  [@key1, key2]  IEEE citation, numbered in order of first appearance
  [#label]       number of a figure / table / equation / listing
Prose whitespace is collapsed, so paragraphs may be wrapped freely.
"""

TITLE = "The Half-Life of Context: Measuring and Repairing Context Rot in Large Language Models"

_AFFIL = [
    "Chitkara University Institute of Engineering and Technology,",
    "Chitkara University,",
    "Punjab, India",
]
AUTHORS = [
    ("Naman Nayak", _AFFIL, "naman0746.be23@chitkara.edu.in"),
    ("Manveer Singh", _AFFIL, "manveer2063.be23@chitkara.edu.in"),
    ("Jaiveer Singh", _AFFIL, "jaiveer2104.be23@chitkara.edu.in"),
    ("Sujal Garg", _AFFIL, "sujal2143.be23@chitkara.edu.in"),
]

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
     In a deliberately small study on one laptop (one 3-billion-parameter open model, [$e4.n_questions|i] LongMemEval
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
     seven hypotheses, two were partly supported, three were not supported or could not be tested, and two
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

# ---------------------------------------------------------------------------------------------
# Code listings: extracted from the real modules in src/ (regions between "# [listing:NAME]" and
# "# [/listing]"), so the paper shows the code that produced the results. Lines must be <= 49
# characters to fit one column (checked in tests/test_listings.py).
# ---------------------------------------------------------------------------------------------
import re as _re
from pathlib import Path as _Path

_SRC = _Path(__file__).resolve().parent.parent / "src" / "context_half_life"


def _load_listings():
    found = {}
    for f in sorted(_SRC.glob("*.py")):
        text = f.read_text(encoding="utf8")
        for m in _re.finditer(r"# \[listing:(\w+)\]\n(.*?)# \[/listing\]", text, _re.S):
            found[m.group(1)] = m.group(2).rstrip("\n")
    return found


LISTINGS = _load_listings()
LISTING_PROBE = LISTINGS["probe"]
LISTING_FIT = LISTINGS["fit"]
LISTING_REPAIR = LISTINGS["repair"]

# ---------------------------------------------------------------------------------------------
# Body. Block types: h1 h2 h3 p bullets steps eq code table figure full_start full_end refs
# ---------------------------------------------------------------------------------------------
BODY = [
    # ======================================================================== I. INTRODUCTION
    ("h1", "Introduction"),
    ("p", """LLMs are increasingly deployed as long-running collaborators: assistants that remember a user
     across weeks, coding agents that act over hundreds of tool calls, and research agents that read and
     synthesize dozens of sources. The model keeps no memory between calls, so everything it knows about
     the task must sit in its <i>context window</i>, the text it rereads before every answer. This window
     is the model's working memory, rewritten continuously as messages, tool outputs, and retrieved
     documents arrive. Windows now reach hundreds of thousands to millions of tokens, which invites the
     assumption that capacity implies capability: if the information fits, the model can use it
     [@hong2025]."""),
    ("p", """The evidence says otherwise. Models use information in the middle of a long input less
     reliably than at its edges [@liu2024]; their effective context is often far shorter than claimed
     [@hsieh2024]; and when question and evidence share few words, 11 of 13 models fall below half of
     their short-context score at only 32K tokens [@modarressi2025]. Across 18 models, reliability worsens
     as input grows even on simple tasks [@hong2025], and accuracy drops by 13.9% to 85% with length even
     when all relevant evidence is retrieved perfectly [@du2025]. Conversations suffer too: chat assistants
     lose about 30% accuracy when recalling information across long histories [@wu2025], and splitting
     single-turn tasks across turns costs 39% on average, mostly through unreliability: once a model takes
     a wrong turn it rarely recovers [@laban2025]. Fig. [#fig:evidence] collects these numbers."""),
    ("figure", "fig:evidence", "fig_evidence.png",
     """Degradation reported by the studies discussed in Section I. Each number is as reported by its
     authors; definitions differ, so bars are not directly comparable.""", 3.15),
    ("p", """We use <i>context rot</i> for the gradual accumulation of stale, contradictory, redundant, and
     irrelevant material within the window. The term was popularised by the Chroma report [@hong2025],
     and practitioners describe related failures as context poisoning, distraction, confusion, and clash
     [@breunig2025b]. Length and rot are related but distinct: length is a property of the window, rot a
     property of its contents. In long-horizon agentic search, degradation depends on what has accumulated,
     not only on how much [@xia2026], while length alone still carries a residual cost [@du2025]. A useful
     account must therefore separate degradation that is <i>repairable</i>, because content has decayed,
     from degradation that is not."""),
    ("p", """Existing mitigations act on size rather than decay. Prompt compression [@jiang2023], rolling
     summarization, retrieval over history [@lewis2020], and memory layers [@packer2023, chhikara2025]
     shrink what the model reads, usually when a token budget is hit, but none estimates how fast each
     piece of information loses value. Blind shrinking has its own failure modes: summaries drop insights
     (<i>brevity bias</i>) and repeated rewriting erodes detail (<i>context collapse</i>) [@zhang2026],
     and pruning an agent's history to recent tool calls cut stale-state errors from 47% to 11% of
     non-completions but doubled premature terminations [@lodha2026]. Removing the right material requires
     measuring what has decayed."""),
    ("p", """We therefore treat context quality as measurable. Our central construct is the <b>Context
     Half-Life</b>: the age, in turns, at which a segment of context has a 50% chance of having lost its
     value to downstream reasoning, by analogy with the half-life of a radioactive sample or a medicine
     dose. We contribute:"""),
    ("bullets", [
        """<b>A metric:</b> Context Half-Life, defined through leave-one-out usefulness and survival
        analysis, with a session-level Rot Index and degradation-onset estimate.""",
        """<b>An estimator</b> for black-box LLMs that combines lightweight detectors, sampled LLM judging,
        and offline ablation-based calibration.""",
        """<b>A repair framework</b> with update, merge, and remove operations, a protection set, and
        verification with rollback, requiring no retraining.""",
        """<b>A small, fully reported empirical study:</b> five experiments with a local 3-billion-parameter
        model (needle in a haystack, fact ageing, synthetic rot injection, repair on a LongMemEval subset,
        ablations), with open code and raw logs, including results that contradict our hypotheses.""",
    ]),
    ("p", """Four research questions guide the study. <b>RQ1:</b> Can the value of contextual information be
     quantified as a decay process with a stable, predictive half-life? <b>RQ2:</b> Does half-life localise
     degradation (which segments, from which turn) better than context length? <b>RQ3:</b> Does
     half-life-guided repair improve accuracy and hallucination rate over baselines at equal or lower token
     cost? <b>RQ4:</b> Which operations contribute most, and at what latency? An earlier draft of this paper
     proposed the framework and fixed seven hypotheses before any experiment was run; here we test them at
     small scale and report each as supported, partly supported, refuted, or not testable. Section II
     explains how LLMs read context, Section III reviews related work, Section IV presents the method and
     the hypotheses, Section V the experimental setup, Section VI the results, Section VII the discussion and
     limitations, and Section VIII concludes."""),

    # ======================================================================== II. BACKGROUND
    ("h1", "Background: How an LLM Reads Its Context"),
    ("h2", "Tokens, attention, and dilution"),
    ("p", """LLMs read text as <i>tokens</i>, frequent words or word pieces; in English one token is roughly
     three-quarters of a word. The context window must hold the instructions, the whole conversation, any
     retrieved documents, and the new question, and because the model is stateless the full history is
     resent on every turn [@ollama]. Transformers [@vaswani2017] decide what matters through
     <i>attention</i>: each token scores the earlier tokens, and the softmax function turns scores into
     weights that are positive and sum to 1. Attention is therefore a fixed budget shared by everything in
     the window [@anthropic2025]. If one key token scores s points above n − 1 equal competitors, its share
     is"""),
    ("eq", "eq:share", "w(n) = e<super>s</super> / (e<super>s</super> + n − 1)"),
    ("figure", "fig:dilution", "fig_dilution.png",
     """Attention dilution in the toy model of Eq. ([#eq:share]): the key token's share falls as tokens are
     added, even when it is strongly preferred (calculation, not measured data).""", 2.9),
    ("p", """With s = 4, the key token receives about 86% of the attention among 10 tokens but only 5% among
     1,000 (Fig. [#fig:dilution]). Real models have many heads and layers, so this toy model is an
     intuition, not a description; still, it shows why one important sentence can be drowned out as the
     window fills, and why distractors that resemble the answer are especially harmful [@hong2025, shi2023].
     Since every token is compared with every other, computation also grows roughly with the square of the
     input length."""),
    ("h2", "Position effects and needle-in-a-haystack tests"),
    ("p", """Position matters as well as length. In multi-document question answering, accuracy is highest
     when the relevant document comes first or last and lowest in the middle; for one model a middle-placed
     answer did worse than no documents at all [@liu2024]. The start benefits from <i>primacy</i>, since
     the first tokens attract outsized attention (<i>attention sinks</i> [@xiao2024]), and the end from
     <i>recency</i>. The simplest probe is the needle-in-a-haystack (NIAH) test [@kamradt2023]: hide one
     out-of-place sentence at a chosen depth in long filler text and ask a question only it answers
     (Fig. [#fig:niah]). Because the needle and question usually share words, later tests made it harder:
     RULER adds multi-hop and aggregation tasks [@hsieh2024], NoLiMa removes word overlap, which drops
     GPT-4o from 99.3% to 69.7% at 32K tokens [@modarressi2025], and the Chroma study varies similarity and
     distractors [@hong2025]. Practical guides follow from these results: put long documents first and the
     question last, which improved responses by up to 30% in Anthropic's tests [@anthropic_lc], and repeat
     key instructions at both ends [@openai_gpt41]."""),
    ("figure", "fig:niah", "fig_niah_position.png",
     """(a) Needle-in-a-haystack setup: a needle at depth d in L tokens of filler, then a question.
     (b) Schematic of the lost-in-the-middle shape reported by Liu et al. [@liu2024] (shape only, no
     data).""", 3.0),
    ("h2", "Why a half-life?"),
    ("p", """When something loses a fixed fraction of what remains per unit time, it follows
     S(a) = e<super>−λa</super> with half-life H = ln 2 / λ ≈ 0.693 / λ. Human memory behaves similarly:
     Ebbinghaus's forgetting curves fall quickly and then flatten [@ebbinghaus1885]. We ask the same of a
     context: after how many turns does a piece of information stop helping? Unlike atoms, information has
     no universal rate (a tool output can be stale within minutes, an allergy matters forever), so we
     estimate separate half-lives per kind of content."""),

    # ======================================================================== III. RELATED WORK
    ("h1", "Related Work"),
    ("h2", "Degradation in long inputs and long interactions"),
    ("p", """RULER found that only about half of the evaluated models held up at 32K tokens despite claiming
     larger windows [@hsieh2024]; NoLiMa showed that earlier robustness partly reflected word matching
     [@modarressi2025]; the Chroma report found across 18 models that degradation accelerates as
     question–evidence similarity falls and that haystack structure changes outcomes [@hong2025]; and Du et
     al. showed that length hurts even when irrelevant tokens are replaced by whitespace or masked, proposing
     recitation of evidence as a mitigation [@du2025]. On LongBench v2, with contexts of 8K to 2M words, the
     best model answering directly reached 50.1% [@bai2025]. In interaction, Laban et al. decomposed the
     multi-turn drop over 200,000 simulated conversations into a small loss of aptitude and a large rise in
     unreliability [@laban2025]; LongMemEval tests extraction, multi-session and temporal reasoning,
     knowledge updates, and abstention over histories of about 115K tokens [@wu2025]; Xia et al. showed
     that deleting all history nearly removes rot but leaves many tasks unfinished [@xia2026]; and Lodha
     et al. raised complete task itemization from 71.0% to 91.6% with roughly 63% fewer tokens through
     pruning and summarization [@lodha2026]. These studies establish that degradation is real and
     content-sensitive, but none assigns a decay rate to the content itself."""),
    ("h2", "Context management and memory"),
    ("p", """Breunig's four failure patterns map onto our decay modes: clash and poisoning onto stale and
     contradictory material, confusion and distraction onto redundant and irrelevant material
     [@breunig2025b], and models are measurably distracted by irrelevant context [@shi2023]. Remedies span
     token compression (LLMLingua [@jiang2023]), retrieval-augmented generation [@lewis2020], and memory
     systems: MemGPT pages memory like an operating system [@packer2023]; generative agents rank memories
     with an exponential recency decay whose rate is fixed by design, the closest precedent to ours
     [@park2023]; Mem0 consolidates salient facts, reporting about 91% lower p95 latency and over 90% token
     savings [@chhikara2025]; Zep marks superseded facts invalid instead of deleting them, gaining up to
     18.5% accuracy on LongMemEval [@rasmussen2025]; ACE updates context as an evolving playbook to avoid
     collapse [@zhang2026]; and AdaCoM learns to manage a frozen agent's context, finding that weaker
     agents need more aggressive compression [@yi2026]. Production guidance adds compaction and the
     clearing of stale tool results [@anthropic2025]. Table [#tab:position] compares these families."""),
    ("full_start",),
    ("table", "tab:position", "Comparison of context-management approaches",
     ["Approach", "Typical trigger", "Decision signal", "Measures decay explicitly?"],
     [
         ["Truncation / sliding window", "Token budget", "Recency", "No"],
         ["Rolling summarization", "Token budget or schedule", "LLM judgment of salience", "No"],
         ["Prompt compression (LLMLingua) [@jiang2023]", "Token budget", "Token informativeness", "No"],
         ["RAG over history [@lewis2020]", "Every query", "Query–passage similarity", "No"],
         ["Memory layers (MemGPT, Mem0) [@packer2023, chhikara2025]", "Write time", "Salience, consolidation",
          "No"],
         ["Temporal graphs (Zep) [@rasmussen2025]", "Write time", "Fact validity intervals",
          "Validity, not value to reasoning"],
         ["Learned managers (AdaCoM) [@yi2026]", "Learned policy", "Reinforcement-learning reward",
          "Implicit in policy"],
         ["<b>Context Half-Life (this work)</b>", "Measured Rot Index and half-life",
          "Estimated usefulness over time", "<b>Yes</b>"],
     ],
     [2.2, 1.45, 1.75, 1.1], {"size": 8}),
    ("full_end",),
    ("p", """The gap is a missing measurement: prior systems decide how much to keep, but none estimates how
     long each piece of information stays useful and uses that estimate to choose among update, merge, and
     remove. The half-life signal is complementary: memory layers can supply segments, learned managers can
     execute actions, and the estimate tells them what to act on and when."""),

    # ======================================================================== IV. METHODOLOGY
    ("h1", "Methodology"),
    ("h2", "Setting, utility, and decay modes"),
    ("p", """A frozen <i>reader</i> model M answers queries x(t) over T turns. At turn t the context
     C(t) = (s<sub>1</sub>, …, s<sub>n</sub>) is a list of <i>segments</i> (messages, tool outputs,
     retrieved passages, memory entries), each with a birth turn b(s), token length ℓ(s), a type, and
     where possible entity–attribute–value triples such as [user, city, Pune]. Answers are scored by
     Q(C, x) ∈ [0, 1], for example 1 if correct. Writing C for C(t) and x for x(t), a segment's
     <i>utility</i> is how much quality changes when it is deleted:"""),
    ("eq", "eq:utility", "u(s | C, x) = Q(C, x) − Q(C ∖ {s}, x)"),
    ("p", """Positive utility helps, near-zero utility is inert but costs tokens, and negative utility
     misleads. Because a segment irrelevant now may matter later (a dietary restriction given in turn 3 and
     needed in turn 80), we average Eq. ([#eq:utility]) over a probe set of current and plausible future
     queries, written u(s, t). Rot takes four forms, shown in Table [#tab:modes] with a running example: a
     student, Asha, using a study assistant."""),
    ("table", "tab:modes", "Decay modes, how they are detected, and how they are repaired",
     ["Decay mode (example)", "Detector", "Operation", "Safeguard"],
     [
         ["<b>Stale</b>: a later value supersedes it (exam moved from 12 to 19 March)",
          "Entity–attribute–value supersession", "UPDATE with change record",
          "Probe the new value; keep history"],
         ["<b>Contradictory</b>: two claims cannot both hold (assistant said six units; syllabus lists five)",
          "Pairwise entailment plus LLM judge", "Resolve by source and recency, else keep both and flag",
          "Protected segments never silently dropped"],
         ["<b>Redundant</b>: already stated elsewhere (formula sheet pasted three times)",
          "Embedding similarity plus two-way entailment", "MERGE", "Atomic-fact coverage check"],
         ["<b>Irrelevant</b>: no expected future use (log of a bug fixed long ago)",
          "Relevance to the current task", "REMOVE to archive", "Reversible recall"],
     ],
     [1.05, 0.75, 0.75, 0.6], {"size": 7}),
    ("h2", "Context Half-Life and the Rot Index"),
    ("p", """Let the age of a segment be a = t − b(s) turns. It <i>decays</i> at the first age at which its
     expected utility falls to a small tolerance ε:"""),
    ("eq", "eq:decay", "D(s) = min { a ≥ 0 : u(s, b(s) + a) ≤ ε }"),
    ("p", """If a session ends first, the decay time is <i>right-censored</i>, which survival analysis
     handles naturally [@kaplan1958]. The survival function S(a) = P(D > a) is the probability that a
     segment is still useful at age a, and the Context Half-Life is its median:"""),
    ("eq", "eq:halflife", "H = min { a : S(a) ≤ 0.5 }"),
    ("p", """With a constant decay rate λ, S(a) = e<super>−λa</super> and H = ln 2 / λ; for λ = 0.0231 per
     turn, H ≈ 30 turns, so a quarter of such segments survive 60 turns. Because decay need not be
     constant, we also fit the Weibull form S(a) = exp(−(a/η)<super>κ</super>) [@weibull1951], with
     H = η·(ln 2)<super>1/κ</super>: κ > 1 means accelerating decay (volatile tool output), κ < 1
     decelerating decay (durable preferences), as Fig. [#fig:survival] illustrates. Covariates such as
     segment type make the half-life conditional, H(z)."""),
    ("figure", "fig:survival", "fig_survival.png",
     """Schematic survival curves for three segment types; dots mark each half-life. Parameters are
     illustrative: Weibull (η = 6, κ = 2), exponential (H = 20), and Weibull (η = 120, κ = 0.7).""", 2.9),
    ("p", """For a whole session, the <i>live fraction</i> L(t) and the <i>Rot Index</i> R(t) weight each
     segment's estimated survival Ŝ by its length, with sums over the segments in C(t):"""),
    ("eq", "eq:live", "L(t) = Σ ℓ(s)·Ŝ(t − b(s)) / Σ ℓ(s)"),
    ("eq", "eq:rot", "R(t) = 1 − L(t)"),
    ("p", """R(t) is the expected fraction of the window's tokens that has decayed. For example, a 2,000-token
     context holding a 200-token system prompt (Ŝ = 1.0), a 1,200-token old tool output (Ŝ = 0.2), a
     100-token preference (Ŝ = 0.95), and 500 tokens of recent chat (Ŝ = 0.6) has L ≈ 0.42 and R ≈ 0.58,
     and the tool output is the obvious repair target. R(t) splits by decay mode, telling the system what
     kind of repair is needed. The <i>session half-life</i> H(C) is the first turn with L(t) ≤ 0.5, and a
     change-point fit of accuracy against R(t) and token count gives the onset turn t*. Fig.
     [#fig:session] simulates a 100-turn chat using the curves of Fig. [#fig:survival]: decayed tokens
     soon dominate, R(t) crosses a repair threshold R* = 0.4 at turn 15, and the session passes its
     half-life at turn 21."""),
    ("figure", "fig:session", "fig_session.png",
     """Simulated session (every turn adds 210 chat tokens, every second turn a 600-token tool output,
     every fifteenth a preference). Top: expected live and decayed tokens. Bottom: Rot Index with the
     repair trigger and session half-life (model calculation, not measured data).""", 2.9),
    ("h2", "Estimating the half-life for black-box models"),
    ("p", """Eq. ([#eq:utility]) needs one extra reader call per segment and probe, so we estimate in three
     tiers. <b>Tier 1 (every turn)</b> uses cheap detectors: entity–attribute–value extraction flags
     superseded values; sentence embeddings [@reimers2019] (vectors whose cosine similarity is near 1 for
     texts with the same meaning) flag near-duplicates and score relevance to the current task; and an
     entailment model checks pairs that mention the same entity for contradictions. User-stated facts and
     preferences are never scored irrelevant by default. <b>Tier 2</b> asks a smaller auxiliary LLM to
     confirm flagged segments with a short rubric, plus a random audit sample to measure detector accuracy.
     <b>Tier 3 (offline)</b> computes leave-one-out utilities with the real reader on development
     conversations, removing near-duplicate groups together because duplicates hide each other's value.
     This yields one row per segment per age with a 0/1 decay indicator, on which we fit a discrete-time
     hazard model, the probability of decaying at age a given survival so far:"""),
    ("eq", "eq:hazard", "h(a | z) = P(D = a | D ≥ a, z) = σ(w · φ(s, C, a))"),
    ("p", """Here σ is the logistic function and φ holds simple features: type, age, later segments touching
     the same attribute, contradiction and redundancy scores, task relevance, later references by the
     assistant, position, and length. This is ordinary logistic regression; survival follows as
     Ŝ(a) = Π<sub>j≤a</sub>(1 − h(j | z)), and type-level half-lives come from Kaplan–Meier curves
     [@kaplan1958] with bootstrap intervals [@efron1993]. Online cost is O(n) embedding operations per turn
     plus a few judge calls; ablation is paid once, offline."""),
    ("h2", "Half-life-guided context repair"),
    ("p", """The repair layer sits between the application and the frozen reader and runs the loop of Fig.
     [#fig:loop] each turn; no model weights or application logic change. It applies four operations:"""),
    ("bullets", [
        "<b>KEEP</b> the segment unchanged.",
        """<b>UPDATE</b> a stale segment to the current value while keeping a short change record, since
        temporal questions may need the history; superseded facts are invalidated rather than deleted
        [@rasmussen2025].""",
        """<b>MERGE</b> redundant segments into one canonical segment that must still contain every distinct
        atomic fact [@min2023], guarding against context collapse [@zhang2026].""",
        """<b>REMOVE</b> irrelevant segments to an indexed archive from which a later query can recall them
        [@lewis2020], so removal is reversible.""",
    ]),
    ("p", """A <b>protection set</b> Π is never edited without verification: instructions, the current goal,
     user constraints and preferences, unsuperseded personal facts, the last k turns (avoiding the premature
     terminations caused by aggressive pruning [@lodha2026]), and anything the assistant recently relied
     on. <b>Planning</b> applies tuned thresholds to the estimated decay-mode probabilities; contradictions
     are resolved by source and recency (a user's statement outranks an assistant's guess), or both sides
     are kept with an uncertainty note. Repair is triggered adaptively, when R(t) exceeds R* or the session
     passes H(C), with a token budget only as a safety net. <b>Verification</b> asks probe questions on the
     original and repaired contexts: unchanged facts must give identical answers and superseded facts the
     new value; failing operations are rolled back. Fig. [#fig:repair] applies this to Asha's chat at turn
     60, cutting 5,625 tokens to 1,945 (−65%) while probes such as "When is my exam?" (19 March) and "Any
     allergies?" (peanuts) must still pass."""),
    ("full_start",),
    ("figure", "fig:loop", "fig_repair_loop.png",
     """The half-life-guided repair loop, executed once per turn between the application and the frozen
     LLM. Shaded steps (3 and 5) are where the Context Half-Life estimate drives decisions.""", 6.4),
    ("full_end",),
    ("figure", "fig:repair", "fig_before_after.png",
     """Worked example: repairing a study-assistant context at turn 60. Colours give the diagnosis; the
     updated exam date keeps a change record, and the error log stays recallable from the archive
     (illustrative token counts).""", 3.0),
    ("h2", "Reference implementation"),
    ("p", """The core measurements need only Python, a laptop, and a free local model served by Ollama
     [@ollama], such as the 3-billion-parameter Llama 3.2; a hosted API can be swapped in by changing one
     function. A NIAH grid comes first: insert a needle at depths of 0–100% across context lengths, ask
     the question several times per cell, and plot accuracy as a heat map, then repeat with a paraphrased
     question and near-miss distractors. Half-life needs <i>age</i> rather than position. Listing
     [#lst:probe] plants a fact, adds a chosen number of filler turns from any dialogue dataset, and
     probes; repeating this at several ages with many different
     facts gives an empirical survival curve."""),
    ("code", "lst:probe", "Fact-ageing probe with a local model", LISTING_PROBE),
    ("p", """The survival curve is fitted by maximum likelihood. Listing [#lst:fit] models the number of
     successful probes at each age as binomial with success probability S(a) = p<sub>0</sub>
     exp(−(a/η)<super>κ</super>); fixing κ = 1 gives the exponential model with λ = 1/η, and the
     half-life follows as H = η (ln 2)<super>1/κ</super>. Several starting points guard against local
     optima, and facts are resampled with replacement for confidence intervals. Repeating the probe for
     preferences, changing values, and numbers buried in tool outputs yields the type-level half-lives
     of RQ1."""),
    ("code", "lst:fit", "Estimating λ and the half-life H from probe results", LISTING_FIT),
    ("p", """A small generator then injects the four decay modes at known ages to provide answer keys for the
     detectors and the onset estimate t*. Repair strategies are plain functions from a segment list to a
     new list: a sliding window; a rolling summary buffer that condenses the oldest half when a budget is
     exceeded [@anthropic2025]; a fact card that rewrites changed values and logs old ones (UPDATE);
     embedding-based de-duplication and relevance pruning (Listing [#lst:repair]); prompt restructuring
     with documents first, question last, and evidence quoted before answering [@anthropic_lc, du2025];
     and retrieval of archived segments by similarity [@lewis2020]. The thresholds in Listing
     [#lst:repair] are starting points to tune on development data."""),
    ("code", "lst:repair", "Embedding-based MERGE and REMOVE with a protection set", LISTING_REPAIR),
    ("h2", "Hypotheses fixed before the experiments"),
    ("p", """Seven hypotheses were written in an earlier draft of this paper, before any experiment was run;
     each states what would refute it, and we report every one as supported, partly supported, refuted, or
     not testable in Section VII."""),
    ("p", """<b>H1: Decay differs by content type.</b> Tool outputs and changing state should have short
     half-lives and preferences long ones, with some non-exponential shapes (κ ≠ 1). Refuted if type-level
     survival curves are indistinguishable or the hazard model performs near chance on held-out data."""),
    ("p", """<b>H2: Half-life localises degradation better than length.</b> R(t) and H(C) should explain more
     accuracy decline than token count, and t* should land near injected change points, since rot depends
     on content [@xia2026, hong2025]; the residual length effect [@du2025] is reported as unrepairable.
     Refuted if token count dominates R(t) in nested models."""),
    ("p", """<b>H3: Repair helps most where rot is structural:</b> in LongMemEval's knowledge-update,
     multi-session, and temporal categories, with a target of +3 percentage points over full context at no
     more than 70% of its tokens. Refuted if gains are uniform across question types or absent."""),
    ("p", """<b>H4: Selective repair beats blind shrinking at equal budget</b>, with fewer lost task states,
     premature terminations [@lodha2026], and detail losses from rewriting [@zhang2026]. Refuted if a
     blinded error analysis shows no difference."""),
    ("p", """<b>H5: Each operation has a signature:</b> REMOVE gives most token savings, UPDATE most of the
     knowledge-update gains, MERGE fewer redundancy errors; dropping protection or verification increases
     regressions."""),
    ("p", """<b>H6: Hallucination falls without hurting abstention</b>, because stale and contradictory
     content breeds confident wrong answers. Refuted if repair removes evidence needed to abstain."""),
    ("p", """<b>H7: Overhead pays for itself</b>: beyond some session length the smaller reader input
     outweighs detector and judge costs, as memory systems already show [@chhikara2025]. Refuted if no
     break-even exists within benchmark lengths."""),
    ("h2", "What the implementation does differently from the design"),
    ("p", """The reference implementation simplifies the design above in ways that matter for reading the
     results. First, the Rot Index used in the experiments is <i>detector-based</i>: R̂(t) is the share of
     tokens in segments flagged by any detector, not the survival-weighted sum of Eq. ([#eq:rot]); the
     survival-weighted form is used only in the illustrative simulation of Fig. [#fig:session]. Second,
     the Tier 3 leave-one-out utilities were not computed, so no hazard model of Eq. ([#eq:hazard]) was
     fitted; instead, a logistic model of probe failure on content type and age is scored by leave-facts-out
     AUC. Third, entity–attribute–value extraction is rule-based on the synthetic sessions and done by the
     3B model on LongMemEval, and contradiction detection (a natural-language-inference cross-encoder) is
     used only on the synthetic sessions. Fourth, the REMOVE archive is kept but never recalled, so removal
     is reversible in principle and not in the measured pipeline."""),

    # ======================================================================== V. EXPERIMENTAL SETUP
    ("h1", "Experimental Setup"),
    ("h2", "Hardware, software, and run policy"),
    ("p", """All experiments ran on one laptop: an Intel Core Ultra 7 255HX CPU, 15.4 GB of RAM, and an NVIDIA
     GeForce RTX 5050 Laptop GPU with 8 GB of memory, under Windows 11. Models were served by Ollama 0.40.8
     [@ollama] (Python client 0.6.3); analysis used Python 3.14.4, NumPy 2.5.4, SciPy 1.18.1, pandas 3.1.0,
     scikit-learn 1.9.1, and lifelines 0.30.0 [@davidson2019]; embeddings and the entailment model ran on the
     CPU through sentence-transformers 6.2.0 and PyTorch 2.14.1. Exact versions are stored with the results.
     To keep the GPU cool the runner sends one request at a time, pauses briefly after each call, and waits
     when the GPU passes 78 °C. Reader calls alone totalled about [$run.reader_min|f0] minutes."""),
    ("h2", "Models, decoding, and seeds"),
    ("p", """The reader in every experiment is <code>llama3.2:3b</code> (Llama 3.2, 3.2 B parameters, Q4_K_M
     quantization, digest a80c4f17acd5) [@grattafiori2024]; the same model serves as the auxiliary model for
     attribute extraction and for rolling summaries. The answer judge in E4 is a different model family,
     <code>qwen2.5:3b</code> (3.1 B parameters, Q4_K_M, digest 357c53fb659c) [@qwen2024]. Decoding is greedy
     (temperature 0) with a global seed of 20261022, so reruns reproduce every answer on the same software.
     Sentence embeddings come from all-MiniLM-L6-v2 [@reimers2019, wang2020] and contradictions are scored by
     the cross-encoder nli-deberta-v3-xsmall [@he2023]. A single reference tokenizer (cl100k, via tiktoken)
     measures all token budgets, so “input tokens” means the same thing in every condition. Larger models,
     including hosted ones, were not run."""),
    ("h2", "Data and subset selection"),
    ("p", """E1 haystacks are cut from three public-domain novels from Project Gutenberg [@gutenberg]. E2 draws
     its filler turns from LongMemEval histories [@wu2025] (cleaned release, MIT licence, dataset revision
     98d7416), skipping every evidence session, with each message cut to 120 words. The facts of E2 and all
     sessions of E3 are <b>synthetic</b>, generated from templates with seeded random values. E4 uses a
     stratified random subset of LongMemEval: the plan was 50 questions (12 knowledge-update, 12 temporal,
     10 multi-session, 8 single-session, 8 abstention), but only questions whose evidence sessions fit in
     4,500 tokens qualify, because each haystack is padded with the question's own distractor sessions to
     about 8,000 tokens in date order. That left [$e4.n_questions|i] questions:
     [$e4.n.knowledge-update|i] knowledge-update, [$e4.n.temporal-reasoning|i] temporal,
     [$e4.n.multi-session|i] multi-session, [$e4.n.single-session-user|i] single-session, and
     [$e4.n.abstention|i] abstention."""),
    ("h2", "Protocols"),
    ("p", """<b>E1 (needle in a haystack).</b> Five lengths (1K to 16K tokens), eleven depths (0–100%), three
     needles, and two wordings give [$e1.n_calls|i] calls. The literal question reuses the needle's words;
     the paraphrase shares no content word with it, which the code checks. Correctness is a normalised
     string match on the answer."""),
    ("p", """<b>E2 (fact-ageing half-life).</b> Three synthetic fact types: a stable preference (a project
     codename), a changing value (a city, corrected right after it is first stated, so age counts turns since
     the correction), and a number buried in a roughly 250-token tool output. Each fact is probed at ages 0,
     5, 10, 20, 40, and 80 turns of filler, with 20 facts per type; filler is nested, so the age-5 context is
     a prefix of the age-10 context. A second, <i>length-matched</i> run (10 facts per type) fixes the total
     at 80 filler turns and varies only how many turns follow the fact, separating age from length.
     Per type we fit exponential and Weibull survival curves by binomial maximum likelihood, bootstrap facts
     (500 resamples) for confidence intervals, draw Kaplan–Meier curves from each fact's first failure
     [@kaplan1958], compare types with a log-rank test, test κ = 1 with a likelihood-ratio test, and score a
     logistic model of failure on type and age by leave-facts-out AUC."""),
    ("p", """<b>E3 (rot injection, synthetic).</b> We generate 40 sessions of 40 turns with known labels: three
     attributes that change value (the old statement is <i>stale</i>), two verbatim re-pastes (the older copy is
     <i>redundant</i>), three build logs (<i>irrelevant</i>), and one wrong assistant claim
     (<i>contradictory</i>). Eight sessions are a development split on which the duplicate and relevance
     thresholds are tuned; the other [$e3.n_test_sessions|i] are the test split. Detectors see only text. R̂(t) is
     computed on the prefix of each session, and the onset t* is the least-squares mean-shift change point
     of that series. A reader probes each attribute's current value at ten checkpoints (every four turns); a
     <i>twin</i> session with the same turn structure but every injected segment replaced by neutral filler
     is probed at the end."""),
    ("p", """<b>E4 and E5 (repair comparison and ablations).</b> For each question the haystack is rendered as a
     transcript and the reader answers once per condition. Conditions: full context (B0), sliding window
     (B1), rolling summary (B2), random and oldest-first removal, half-life-guided repair (HL), and an oracle
     that sees only the evidence sessions. HL extracts user-stated attributes with the 3B model from messages
     that contain a change cue (a time word or a digit), canonicalises attribute names by embedding
     similarity (cosine ≥ 0.85), flags stale values, near-duplicates (cosine above [$e3.dup|f2]), and segments
     with relevance to the question below [$e3.rel|f2] (both thresholds tuned on E3's development split),
     protects user-stated values and the last six segments, and repairs when R̂ exceeds 0.10 (fixed in
     advance, not tuned). Verification re-asks the question and rolls the repair back if the answer turns
     into an abstention that the full context did not give; no gold label is used. B1, B2, random, and
     oldest-first receive, for each question, the token budget that HL ended up with. E5 re-runs HL
     without UPDATE, without MERGE, without REMOVE, without the protection set, without verification, and
     with a token-budget trigger (repair only above 90% of the target length). Identical prompts are answered
     once and the answer is reused."""),
    ("h2", "Metrics and statistics"),
    ("p", """Table [#tab:metrics] defines the metrics. Hallucination is a confident wrong answer: an incorrect
     answer that is not an abstention, or any non-abstaining answer to an unanswerable question. Correctness
     is judged by the second model with LongMemEval-style prompts [@wu2025]. Comparisons are paired by
     question: exact McNemar test [@mcnemar1947], paired bootstrap intervals with 10,000 resamples
     [@efron1993], and Holm's correction [@holm1979] over the five comparisons of HL against the other
     strategies. Intervals are percentile bootstrap intervals over questions or facts, and with samples this
     small they are wide."""),
    ("table", "tab:metrics", "Evaluation metrics (reasoning-quality rubric and human audit were not run)",
     ["Dimension", "How it is computed"],
     [
         ["Task accuracy", "Correct answers ÷ questions (LLM judge; string match for E1–E3)"],
         ["Hallucination rate", "Share of confident wrong answers, plus any answer to an unanswerable question"],
         ["Token efficiency", "Input tokens per query; accuracy per 1,000 tokens"],
         ["Latency", "Median and 95th-percentile reader time; repair overhead reported separately"],
         ["Context health", "Type-level half-life H, Rot Index R̂(t), onset turn t*"],
     ],
     [0.95, 2.2], {"size": 7.5}),
    ("h2", "Deviations from the planned study"),
    ("p", """Because the study had to fit about two hours on one laptop, it is much smaller than the design in
     the earlier draft. Section VII lists the consequences; here we state the facts."""),
    ("bullets", [
        """One 3B reader and a 3B judge instead of two open-weight and two proprietary readers; the judge
        agrees with plain string matching on only [$e4.judge_agree|pct0]% of
        [$e4.judge_n_answerable|i] answerable-question answers.""",
        """[$e4.n_questions|i] questions with about 8K-token contexts instead of 100 questions with contexts of
        up to 115K tokens; LongBench v2, NoLiMa, and the Chroma toolkit were not run.""",
        """No LLMLingua, memory-layer, or learned-manager baselines; no reasoning-quality rubric; no human
        audit of the judge; no blinded error analysis (H4).""",
        """The Rot Index is detector-based, and no leave-one-out utilities or hazard model were computed
        (Section IV-G).""",
        """E3 is not a clean held-out test. While debugging, we ran the detectors on the whole synthetic set,
        found that the first generator reused ten filler sentences (so the filler itself was redundant) and
        that the value extractor mishandled titles such as “Dr.”, fixed both, and re-ran everything before
        reporting; only the tuned thresholds were restricted to the development sessions.""",
    ]),
    ("h2", "Code and data availability"),
    ("p", """All code, raw per-call logs (JSON Lines), summary tables, and the build scripts of this paper are
     in a public repository [@repo]. Every number in Section VI is read from a file under
     <code>results/</code> when the paper is built, and the build fails if a quoted number is missing."""),

    # ======================================================================== VI. RESULTS
    ("h1", "Results"),
    ("h2", "E1: needle in a haystack"),
    ("p", """Accuracy with the literal question is [$e1.acc.literal|pct0]% overall
     (95% CI [$e1.acc.literal.lo|pct0]–[$e1.acc.literal.hi|pct0]) and falls from
     [$e1.acc.literal.2048|pct0]% at 2K tokens to [$e1.acc.literal.8192|pct0]% at 8K and
     [$e1.acc.literal.16384|pct0]% at 16K (Fig. [#fig:e1]). Rewording the question so that it shares no
     content word with the needle lowers overall accuracy to [$e1.acc.paraphrase|pct0]%, a paired difference
     of [$e1.para_minus_lit|sgn1] points (95% CI [$e1.para_minus_lit.lo|sgn1] to
     [$e1.para_minus_lit.hi|sgn1]; McNemar [$e1.mcnemar_p|pv]); at 16K tokens the paraphrased question is
     answered correctly only [$e1.acc.paraphrase.16384|pct0]% of the time. The famous lost-in-the-middle dip
     [@liu2024] does not appear: literal accuracy at depths 30–70% is [$e1.lit.mid_depth|pct0]%, against
     [$e1.lit.end_depth|pct0]% at depths of at most 10% or at least 90%. With three needles per cell, each
     heat-map cell can only take the values 0, 33, 67, and 100%, so single cells should not be interpreted;
     the trends by length and wording are what the data support."""),
    ("full_start",),
    ("figure", "fig:e1", "fig_e1_niah.png",
     """E1 (measured, llama3.2:3b). (a, b) Accuracy (%) by context length and needle depth for the literal and
     the paraphrased question (3 needles per cell). (c) Accuracy by length.""", 6.4),
    ("full_end",),
    ("h2", "E2: fact-ageing half-life"),
    ("p", """Table [#tab:e2] and Fig. [#fig:e2] show that content type matters. A <i>changing value</i> is
     answered correctly at every age up to 20 turns, then drops to [$e2.ageing.changing.S40|pct0]% at 40 turns
     and [$e2.ageing.changing.S80|pct0]% at 80; its Weibull half-life is
     [$e2.ageing.changing.wb_H|f0] turns with shape κ = [$e2.ageing.changing.wb_kappa|f2]
     (95% CI [$e2.ageing.changing.wb_kappa_lo|f2]–[$e2.ageing.changing.wb_kappa_hi|f2]), meaning accelerating
     decay, and the likelihood-ratio test rejects a constant rate ([$e2.ageing.changing.lrt_p|pv]). The
     mechanism is staleness: at 80 turns the model answered with the <i>old</i> city in
     [$e2.ageing.stale_rate.80|pct0]% of the probes. A <i>stable preference</i> never decayed within 80
     turns, so its half-life is right-censored (above 80), and a <i>number in a tool output</i> was still
     found in [$e2.ageing.tool.S80|pct0]% of probes at 80 turns; its fitted half-life lies beyond the
     measured horizon, and the very large κ simply reflects a single step between 40 and 80 turns, so
     the narrow interval for the tool-output Weibull fit should not be read as precision. The log-rank test
     separates the three types ([$e2.ageing.logrank_p|pv]), and a logistic model of failure on type and
     age reaches a leave-facts-out AUC of [$e2.ageing.hazard_auc|f2]."""),
    ("table", "tab:e2", "E2 survival fits, ageing design (20 facts per type; 95% bootstrap CIs in parentheses)",
     ["Fact type", "S(80)", "Weibull H (turns)", "κ", "Exp. H (turns)"],
     [
         ["Stable preference", "[$e2.ageing.preference.S80|pct0]%", "> 80 (censored)", "–", "–"],
         ["Changing value", "[$e2.ageing.changing.S80|pct0]%", _wb("changing", "wb_H"),
          _wb("changing", "wb_kappa", "f1"), _wb("changing", "exp_H")],
         ["Number in tool output", "[$e2.ageing.tool.S80|pct0]%", "beyond horizon<super>a</super>",
          "poorly identified<super>a</super>", _wb("tool", "exp_H") + "<super>a</super>"],
     ],
     [0.78, 0.38, 0.72, 0.62, 0.65], {"size": 7}),
    ("p", """<super>a</super> Extrapolated beyond the 80-turn horizon from a single step in the data. The
     exponential half-life of the preference is not estimable because no failure occurred."""),
    ("full_start",),
    ("figure", "fig:e2", "fig_e2_survival.png",
     """E2 (measured, synthetic facts). Fraction of facts answered correctly by age. Dots: observed;
     faint steps: Kaplan–Meier curves from first failure; dashed: Weibull fits (not drawn for the censored
     preference). (a) Filler follows the fact (20 facts per type). (b) Length-matched control (10 facts
     per type).""", 6.4),
    ("full_end",),
    ("p", """The length-matched control (Fig. [#fig:e2]b) does <i>not</i> reproduce this separation: with
     the total length fixed at 80 turns and only 10 facts per type, the log-rank test finds no difference
     between types ([$e2.matched.logrank_p|pv]) and the stable preference dips to
     [$e2.matched.preference.S20|pct0]% at age 20 before recovering, which is sampling noise at this
     sample size. Age and length are therefore confounded in the main design, and the half-lives above
     describe decay in a growing context, not age alone."""),
    ("h2", "E3: rot injection (synthetic sessions)"),
    ("p", """Table [#tab:e3] reports detector quality on the [$e3.n_test_sessions|i] test sessions.
     Because the stale and contradictory statements follow fixed templates, rule-based attribute extraction
     plus the entailment model find them perfectly, which says more about the generator than about real
     conversations. The redundancy detector has full recall but precision of only
     [$e3.redundant.precision|pct0]%, and the relevance detector flags [$e3.irrelevant.n_pred|i] segments for
     [$e3.irrelevant.n_true|i] true irrelevant ones (precision [$e3.irrelevant.precision|pct0]%), because
     study-topic chat is also distant from the current question."""),
    ("table", "tab:e3", "E3 detector quality on synthetic test sessions (95% CI over sessions)",
     ["Mode", "True", "Flagged", "Precision (%)", "Recall (%)"],
     [
         ["Stale", "[$e3.stale.n_true|i]", "[$e3.stale.n_pred|i]", _ci("e3.stale.precision"),
          _ci("e3.stale.recall")],
         ["Contradictory", "[$e3.contradictory.n_true|i]", "[$e3.contradictory.n_pred|i]",
          _ci("e3.contradictory.precision"), _ci("e3.contradictory.recall")],
         ["Redundant", "[$e3.redundant.n_true|i]", "[$e3.redundant.n_pred|i]", _ci("e3.redundant.precision"),
          _ci("e3.redundant.recall")],
         ["Irrelevant", "[$e3.irrelevant.n_true|i]", "[$e3.irrelevant.n_pred|i]", _ci("e3.irrelevant.precision"),
          _ci("e3.irrelevant.recall")],
     ],
     [0.78, 0.4, 0.5, 0.72, 0.72], {"size": 7}),
    ("p", """The onset estimate recovers the injected change point only weakly (Fig. [#fig:e3]b). The mean
     absolute error is [$e3.onset_rot.mae|f1] turns (95% CI [$e3.onset_rot.mae_ci.lo|f1]–[$e3.onset_rot.mae_ci.hi|f1]), against [$e3.onset_ref.mae_uniform|f1] for a guess drawn uniformly over
     the session; the estimate is biased late by [$e3.onset_rot.bias|f1] turns on average, only
     [$e3.onset_rot.within5|pct0]% of sessions fall within five turns, and the correlation between true and
     estimated onset is [$e3.onset_rot.corr|f2]. The onset found from reader accuracy is no better (mean
     absolute error [$e3.onset_acc.mae|f1] turns), because reader accuracy is noisy and flat (Fig.
     [#fig:e3]c). The injected rot also barely hurt the reader: at the end of the session, accuracy was
     [$e3.twin.acc_rot|pct0]% with rot and [$e3.twin.acc_twin|pct0]% in the rot-free twin, a difference of
     [$e3.twin.diff|sgn1] points (95% CI [$e3.twin.diff.lo|sgn1] to [$e3.twin.diff.hi|sgn1];
     [$e3.twin.mcnemar_p|pv]). Adding R̂ to a logistic model that already contains the token count improves
     the fit only marginally (likelihood-ratio [$e3.h2.lrt_p|pv])."""),
    ("full_start",),
    ("figure", "fig:e3", "fig_e3_detect.png",
     """E3 (measured, synthetic sessions). (a) Detector precision and recall by decay mode. (b) Estimated
     onset t* against the injected change point c (dashed line: perfect recovery; points jittered
     horizontally). (c) Reader accuracy at each checkpoint turn; the shaded band is the range of c.""", 6.4),
    ("full_end",),
    ("h2", "E4: repair comparison"),
    ("p", """Table [#tab:e4] and Fig. [#fig:e4] compare the strategies on [$e4.n_questions|i] questions.
     HL repair fired on [$e4.triggered_frac|pct0]% of questions (mean R̂ = [$e4.r_hat_mean|f2]) and cut the input from
     [$e4.tokens.B0|i] to [$e4.tokens.HL|i] tokens, but accuracy fell from [$e4.acc.B0|pct0]% to
     [$e4.acc.HL|pct0]% and hallucination rose from [$e4.halluc.B0|pct0]% to [$e4.halluc.HL|pct0]%. None of
     the paired differences against HL is significant after Holm's correction (Table [#tab:e4cmp]); the
     point estimate against full context is [$e4.cmp.HL_vs_B0.diff|sgn1] points, HL ties the sliding
     window, random removal, and oldest-first removal, and its edge over the rolling summary is
     [$e4.cmp.HL_vs_B2.diff|sgn1] points. In short, HL is about as good as other ways of shrinking the
     context by [$e4.saving.HL|pct0]%, and none of them matched full context. The oracle, which sees only the evidence
     sessions, scores [$e4.acc.ORACLE|pct0]%, equal to full context, so the reader's own ability, not the
     distractors, limits accuracy on this subset."""),
    ("full_start",),
    ("table", "tab:e4", "E4 main comparison (95% bootstrap CIs; reader latency in seconds)",
     ["Condition", "Accuracy (%)", "Halluc. (%)", "Input tokens", "Acc. per 1K tok.", "p50 (s)", "p95 (s)"],
     [[name, _ci(f"e4.acc.{c}"), f"[$e4.halluc.{c}|pct0]", f"[$e4.tokens.{c}|i]",
       f"[$e4.acc_per_1k.{c}|f3]", f"[$e4.p50.{c}|f1]", f"[$e4.p95.{c}|f1]"]
      for name, c in [("B0 full context", "B0"), ("B1 sliding window", "B1"), ("B2 rolling summary", "B2"),
                      ("Random removal", "RND"), ("Oldest first", "OLD"), ("HL repair (this work)", "HL"),
                      ("Oracle (evidence only)", "ORACLE")]],
     [1.45, 1.2, 0.65, 0.8, 0.85, 0.7, 0.7], {"size": 8}),
    ("figure", "fig:e4", "fig_e4_repair.png",
     """E4 (measured, 35 LongMemEval questions). (a) Accuracy against mean input tokens with 95% CIs; B1,
     random, and oldest-first coincide. (b) Accuracy by question type with the number of questions.
     (c) Median and 95th-percentile reader latency.""", 6.4),
    ("full_end",),
    ("table", "tab:e4cmp", "HL against each strategy: paired difference in accuracy",
     ["Comparison", "Diff. (points)", "Holm p"],
     [[f"HL − {name}", f"[$e4.cmp.HL_vs_{c}.diff|sgn1] ([$e4.cmp.HL_vs_{c}.lo|sgn1] to "
                       f"[$e4.cmp.HL_vs_{c}.hi|sgn1])", f"[$e4.cmp.HL_vs_{c}.p_holm|f2]"]
      for name, c in [("B0", "B0"), ("B1", "B1"), ("B2", "B2"), ("Random", "RND"), ("Oldest", "OLD")]],
     [0.85, 1.65, 0.65], {"size": 7.5}),
    ("p", """By question type (Fig. [#fig:e4]b), the picture is mixed and every cell is tiny. On the
     [$e4.n.temporal-reasoning|i] temporal questions HL scores [$e4.cat.temporal-reasoning.HL|pct0]% against
     [$e4.cat.temporal-reasoning.B0|pct0]% for full context, the clearest loss; on the
     [$e4.n.multi-session|i] multi-session questions it scores [$e4.cat.multi-session.HL|pct0]% against
     [$e4.cat.multi-session.B0|pct0]%; on abstention it ties full context at
     [$e4.cat.abstention.HL|pct0]%. Only [$e4.n.knowledge-update|i] knowledge-update questions fit the
     length cap, and all strategies answered both, so the case the method is designed for was not
     tested. The stale-value detector found [$e4.n_stale_mean|f1] stale segments per question, so UPDATE
     never fired on real conversations; the detector flagged [$e4.n_redundant_mean|f1] redundant and
     [$e4.n_irrelevant_mean|f1] irrelevant segments per question, so nearly all of the token saving comes
     from REMOVE."""),
    ("p", """Repair is slow in this implementation. The reader needs [$e4.latency.hl_reader_mean|f1] s on the
     repaired context against [$e4.latency.b0_mean|f1] s on the full one, a saving of
     [$e4.latency.saved_reader_s|f1] s, but detection and repair on the CPU take
     [$e4.repair_s_mean|f1] s per question, so the total is [$e4.latency.hl_total_mean|f1] s."""),
    ("h2", "E5: ablations"),
    ("p", """Table [#tab:e5] removes one component at a time. Without UPDATE, without MERGE, without the
     protection set, without verification, and with a token-budget trigger, accuracy equals that of
     full HL, because UPDATE and MERGE almost never fired, the protection
     set and verification rarely mattered (verification rolled back
     [$e4.rolled_back.HL|pct1]% of questions, one question in [$e4.n_questions|i]), and the token trigger
     fired whenever R̂ did. Only removing REMOVE changes anything: accuracy rises to
     [$e4.acc.HL_noremove|pct0]% while the input stays at [$e4.tokens.HL_noremove|i] tokens, which confirms
     that REMOVE alone delivers the savings and also the losses."""),
    ("table", "tab:e5", "E5 ablations of HL repair (paired difference against full HL)",
     ["Variant", "Acc. (%)", "Diff. vs HL (points)", "Tok.", "Hall. (%)"],
     [[name, f"[$e4.acc.{c}|pct0]",
       ("reference" if c == "HL" else
        f"[$e5.diff.{c}|sgn1] ([$e5.diff.{c}.lo|sgn1] to [$e5.diff.{c}.hi|sgn1])"),
       f"[$e4.tokens.{c}|i]", f"[$e4.halluc.{c}|pct0]"]
      for name, c in [("Full HL", "HL"), ("− UPDATE", "HL_noupdate"), ("− MERGE", "HL_nomerge"),
                      ("− REMOVE", "HL_noremove"), ("− protection", "HL_noprotect"),
                      ("− verification", "HL_noverify"), ("Token trigger", "HL_tok")]],
     [0.72, 0.42, 1.05, 0.48, 0.48], {"size": 7}),

    # ======================================================================== VII. DISCUSSION
    ("h1", "Discussion"),
    ("h2", "Verdict on each hypothesis"),
    ("p", """Table [#tab:verdict] gives the verdict on each of the seven hypotheses of Section IV-F, with the
     evidence that decides it. Two are partly supported, three are not supported or could not be tested, and
     two are refuted."""),
    ("table", "tab:verdict", "Verdict on the seven hypotheses",
     ["H", "Verdict", "Evidence"],
     [
         ["H1", "Partly supported",
          "Types separate in the ageing design (log-rank [$e2.ageing.logrank_p|pv]; AUC [$e2.ageing.hazard_auc|f2]; "
          "changing κ = [$e2.ageing.changing.wb_kappa|f1]) but not in the length-matched control "
          "([$e2.matched.logrank_p|pv]); n is small."],
         ["H2", "Not supported",
          "Onset error [$e3.onset_rot.mae|f1] turns vs [$e3.onset_ref.mae_uniform|f1] for a uniform guess; "
          "R̂ adds little to token count ([$e3.h2.lrt_p|pv]); rot barely hurt the reader."],
         ["H3", "Not supported; mostly not testable",
          "[$e4.n.knowledge-update|i] knowledge-update questions; HL [$e4.cmp.HL_vs_B0.diff|sgn1] points vs "
          "full context overall."],
         ["H4", "Not supported",
          "HL ties B1, random, and oldest-first; a [$e4.cmp.HL_vs_B2.diff|sgn1]-point edge over B2 is "
          "not significant; no error analysis was run."],
         ["H5", "Partly supported",
          "REMOVE alone gives the token savings; UPDATE and MERGE never fired, so their signatures could not "
          "be tested."],
         ["H6", "Refuted",
          "Hallucination [$e4.halluc.B0|pct0]% → [$e4.halluc.HL|pct0]%; abstention accuracy unchanged "
          "([$e4.cat.abstention.HL|pct0]%)."],
         ["H7", "Refuted at 8K tokens",
          "Total time [$e4.latency.hl_total_mean|f1] s vs [$e4.latency.b0_mean|f1] s; no break-even in the "
          "lengths measured."],
     ],
     [0.3, 0.8, 2.05], {"size": 7}),
    ("h2", "What the results do and do not show"),
    ("p", """The strongest finding is empirical and supports the premise: information decays at different rates
     depending on what it is, and the decay can be measured with ordinary survival tools even on a
     3B model. The changing value, the case that is stale by construction, decays with an increasing hazard,
     and the model's mistakes are the old value rather than random errors; a stable preference does not decay
     at all. This pattern is what the half-life idea predicts. The needle-in-a-haystack result adds that
     retrieval depends heavily on question wording, in line with earlier reports that matching words inflate
     long-context scores [@modarressi2025], while the position effect reported for larger models [@liu2024]
     is not visible for this one."""),
    ("p", """The weakest finding is the second half of the thesis: using the measurement to repair the
     context did not help. Several explanations are plausible, and our data do not separate them. The reader
     is small, and the oracle result shows that it fails on about half of the questions even when given
     only the evidence, so there is little headroom for any context repair. The judge is a 3B model that agrees
     with string matching on about three answers in four, so accuracy differences of a few points are within
     its noise. The relevance detector is crude: it uses sentence-embedding similarity to the question, which
     removes evidence for multi-hop and temporal questions whose evidence does not resemble the question, and
     it fired on every question. The stale-value detector depends on the same small model and found nothing.
     Finally, all contexts were about 8K tokens, a length at which a 3B model is not yet overwhelmed, so the
     potential gain from shrinking was small, and the embedding and extraction steps were slow on a laptop CPU.
     None of these is evidence that half-life-guided repair cannot work; each is a reason the present test was
     weak."""),
    ("p", """The synthetic E3 results should be read with caution. They show that the machinery works when the
     rot is cleanly templated, but the generator and the detectors were written by the same authors,
     the detectors' thresholds were tuned on the same generator, and the one measurable effect we hoped
     for, a drop in reader accuracy after the change point, did not appear at this scale."""),
    ("h2", "Implications"),
    ("p", """Three practical points follow. First, measure staleness separately from length: content-dependent
     decay appeared even with a short, constant context, and a fixed truncation rule would discard stable
     preferences and changing values alike. Second, any context-repair method needs a ceiling check such
     as our oracle condition; here it showed immediately that the reader, not the context, was the
     bottleneck. Third, repair that costs more compute than the reader time it saves needs long contexts
     or cheaper detectors to pay off, so detector cost belongs in the evaluation, not just in the discussion."""),
    ("h2", "Threats to validity and limitations"),
    ("bullets", [
        """<b>Scale and power:</b> one 3B model, one seed, 20 facts per age, and [$e4.n_questions|i] questions
        give wide intervals; differences of ten points are not detectable. Failure to find an effect is not
        evidence of no effect.""",
        """<b>Confounding:</b> in E2 age and length grow together; the length-matched control is half the size
        and did not replicate the separation of types.""",
        """<b>Synthetic data:</b> E2 facts and all E3 sessions are template-generated, the detectors read the same
        templates, and real conversations are messier.""",
        """<b>Evaluation:</b> the judge is a weak, same-scale model with
        [$e4.judge_agree|pct0]% agreement with string matching [@zheng2023]; LongMemEval items may be
        contaminated; no human audit was done.""",
        """<b>Coverage:</b> hosted and larger models, LongBench v2, NoLiMa, the Chroma toolkit, and other
        memory systems were not evaluated, and the knowledge-update stratum was almost empty.""",
        """<b>Systems and security:</b> editing early context can invalidate prompt caches, and a repair layer is
        itself an attack surface, since a poisoned tool result could trigger removal of real constraints.""",
    ]),

    # ======================================================================== VIII. CONCLUSION
    ("h1", "Conclusion and Future Scope"),
    ("p", """We proposed to measure how quickly the contents of an LLM context lose value and to repair the
     context accordingly. In a small, fully reported study with a 3B open model we found that decay does
     depend on content type, that a changing value loses usefulness with an accelerating hazard while a stable
     preference does not, and that question wording matters more than context length. We did not find that the
     measurement improves repair: half-life-guided repair saved about [$e4.saving.HL|pct0]% of the tokens,
     did not raise accuracy, increased hallucination, and cost more time than it saved. Two of seven
     hypotheses were partly supported, three were not supported or could not be tested, and two were
     refuted at this scale."""),
    ("p", """The next steps are to test the same protocol where the claim is most likely to hold: readers of
     8B parameters and above and a hosted model [@grattafiori2024]; a larger knowledge-update subset with an
     entailment-based staleness detector instead of small-model extraction; contexts of 32K tokens and more,
     where shrinking should matter and where LongBench v2 and NoLiMa apply; GPU-side embeddings to reduce
     overhead; recall from the archive; learned hazard and repair policies [@yi2026]; a human audit of the
     judge; and a dedicated decay benchmark with ground-truth half-lives, compared with human forgetting
     curves [@ebbinghaus1885]. Cache-aware repair scheduling and defences against poisoned tool outputs
     remain open. The code and every raw log are public so that these studies can start from our negative
     results rather than repeat them."""),
    ("refs",),
]

# ---------------------------------------------------------------------------------------------
# References (IEEE style). Numbered automatically in order of first citation.
# ---------------------------------------------------------------------------------------------
REFERENCES = {
    "hong2025": 'K. Hong, A. Troynikov, and J. Huber, "Context rot: How increasing input tokens impacts LLM '
                'performance," Chroma, Tech. Rep., Jul. 2025. [Online]. Available: '
                'https://research.trychroma.com/context-rot',
    "liu2024": 'N. F. Liu, K. Lin, J. Hewitt, A. Paranjape, M. Bevilacqua, F. Petroni, and P. Liang, "Lost in '
               'the middle: How language models use long contexts," <i>Trans. Assoc. Comput. Linguistics</i>, '
               'vol. 12, pp. 157–173, 2024.',
    "hsieh2024": 'C.-P. Hsieh, S. Sun, S. Kriman, S. Acharya, D. Rekesh, F. Jia, Y. Zhang, and B. Ginsburg, '
                 '"RULER: What\'s the real context size of your long-context language models?" in <i>Proc. '
                 'Conf. Language Modeling (COLM)</i>, 2024, arXiv:2404.06654.',
    "modarressi2025": 'A. Modarressi, H. Deilamsalehy, F. Dernoncourt, T. Bui, R. A. Rossi, S. Yoon, and '
                      'H. Schütze, "NoLiMa: Long-context evaluation beyond literal matching," in <i>Proc. 42nd '
                      'Int. Conf. Machine Learning (ICML)</i>, PMLR, vol. 267, 2025, pp. 44554–44570.',
    "du2025": 'Y. Du, M. Tian, S. Ronanki, S. Rongali, S. B. Bodapati, A. Galstyan, A. Wells, R. Schwartz, '
              'E. A. Huerta, and H. Peng, "Context length alone hurts LLM performance despite perfect '
              'retrieval," in <i>Findings Assoc. Comput. Linguistics: EMNLP 2025</i>, 2025, arXiv:2510.05381.',
    "wu2025": 'D. Wu, H. Wang, W. Yu, Y. Zhang, K.-W. Chang, and D. Yu, "LongMemEval: Benchmarking chat '
              'assistants on long-term interactive memory," in <i>Proc. Int. Conf. Learning Representations '
              '(ICLR)</i>, 2025, arXiv:2410.10813.',
    "laban2025": 'P. Laban, H. Hayashi, Y. Zhou, and J. Neville, "LLMs get lost in multi-turn conversation," '
                 'arXiv:2505.06120, 2025.',
    "breunig2025b": 'D. Breunig, "How to fix your context," dbreunig.com, Jun. 2025. [Online]. Available: '
                    'https://www.dbreunig.com/2025/06/26/how-to-fix-your-context.html',
    "xia2026": 'S. Xia, Y. Wang, Z. Huang, and P. Liu, "Diagnosing and mitigating context rot in long-horizon '
               'search," arXiv:2606.29718, 2026.',
    "jiang2023": 'H. Jiang, Q. Wu, C.-Y. Lin, Y. Yang, and L. Qiu, "LLMLingua: Compressing prompts for '
                 'accelerated inference of large language models," in <i>Proc. Conf. Empirical Methods in '
                 'Natural Language Processing (EMNLP)</i>, 2023, arXiv:2310.05736.',
    "lewis2020": 'P. Lewis et al., "Retrieval-augmented generation for knowledge-intensive NLP tasks," in '
                 '<i>Advances in Neural Information Processing Systems (NeurIPS)</i>, vol. 33, 2020.',
    "packer2023": 'C. Packer, S. Wooders, K. Lin, V. Fang, S. G. Patil, I. Stoica, and J. E. Gonzalez, '
                  '"MemGPT: Towards LLMs as operating systems," arXiv:2310.08560, 2023.',
    "chhikara2025": 'P. Chhikara, D. Khant, S. Aryan, T. Singh, and D. Yadav, "Mem0: Building '
                    'production-ready AI agents with scalable long-term memory," arXiv:2504.19413, 2025.',
    "zhang2026": 'Q. Zhang et al., "Agentic context engineering: Evolving contexts for self-improving language '
                 'models," in <i>Proc. Int. Conf. Learning Representations (ICLR)</i>, 2026, arXiv:2510.04618.',
    "lodha2026": 'A. Lodha, M. Pahlavikhah Varnosfaderani, A. Chakraborty, and A. Mithal, "Less context, '
                 'better agents: Efficient context engineering for long-horizon tool-using LLM agents," '
                 'arXiv:2606.10209, 2026.',
    "ollama": 'Ollama, "Ollama Python library," GitHub repository. [Online]. Available: '
              'https://github.com/ollama/ollama-python',
    "vaswani2017": 'A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, Ł. Kaiser, and '
                   'I. Polosukhin, "Attention is all you need," in <i>Advances in Neural Information Processing '
                   'Systems (NeurIPS)</i>, vol. 30, 2017, pp. 5998–6008.',
    "anthropic2025": 'Anthropic, "Effective context engineering for AI agents," Anthropic Engineering Blog, '
                     '2025. [Online]. Available: '
                     'https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents',
    "shi2023": 'F. Shi, X. Chen, K. Misra, N. Scales, D. Dohan, E. Chi, N. Schärli, and D. Zhou, "Large '
               'language models can be easily distracted by irrelevant context," in <i>Proc. 40th Int. Conf. '
               'Machine Learning (ICML)</i>, 2023.',
    "xiao2024": 'G. Xiao, Y. Tian, B. Chen, S. Han, and M. Lewis, "Efficient streaming language models with '
                'attention sinks," in <i>Proc. Int. Conf. Learning Representations (ICLR)</i>, 2024, '
                'arXiv:2309.17453.',
    "kamradt2023": 'G. Kamradt, "Needle in a haystack: Pressure testing LLMs," GitHub repository, 2023. '
                   '[Online]. Available: https://github.com/gkamradt/LLMTest_NeedleInAHaystack',
    "anthropic_lc": 'Anthropic, "Long context prompting tips," Claude Developer Platform Documentation. '
                    '[Online]. Available: https://platform.claude.com/docs/en/build-with-claude/'
                    'prompt-engineering/long-context-tips',
    "openai_gpt41": 'OpenAI, "GPT-4.1 prompting guide," OpenAI Cookbook, Apr. 2025. [Online]. Available: '
                    'https://cookbook.openai.com/examples/gpt4-1_prompting_guide',
    "ebbinghaus1885": 'H. Ebbinghaus, <i>Über das Gedächtnis: Untersuchungen zur experimentellen '
                      'Psychologie</i>. Leipzig, Germany: Duncker & Humblot, 1885.',
    "bai2025": 'Y. Bai et al., "LongBench v2: Towards deeper understanding and reasoning on realistic '
               'long-context multitasks," in <i>Proc. 63rd Annu. Meeting Assoc. Comput. Linguistics (Vol. 1: '
               'Long Papers)</i>, 2025, doi: 10.18653/v1/2025.acl-long.183.',
    "park2023": 'J. S. Park, J. C. O\'Brien, C. J. Cai, M. R. Morris, P. Liang, and M. S. Bernstein, '
                '"Generative agents: Interactive simulacra of human behavior," in <i>Proc. 36th Annu. ACM Symp. '
                'User Interface Software and Technology (UIST)</i>, 2023.',
    "rasmussen2025": 'P. Rasmussen et al., "Zep: A temporal knowledge graph architecture for agent memory," '
                     'arXiv:2501.13956, 2025.',
    "yi2026": 'L. Yi et al., "Learning agent-compatible context management for long-horizon tasks," '
              'arXiv:2605.30785, 2026.',
    "kaplan1958": 'E. L. Kaplan and P. Meier, "Nonparametric estimation from incomplete observations," '
                  '<i>J. Amer. Statist. Assoc.</i>, vol. 53, no. 282, pp. 457–481, 1958.',
    "weibull1951": 'W. Weibull, "A statistical distribution function of wide applicability," <i>J. Appl. '
                   'Mech.</i>, vol. 18, pp. 293–297, 1951.',
    "reimers2019": 'N. Reimers and I. Gurevych, "Sentence-BERT: Sentence embeddings using Siamese '
                   'BERT-networks," in <i>Proc. Conf. Empirical Methods in Natural Language Processing '
                   '(EMNLP-IJCNLP)</i>, 2019, pp. 3982–3992.',
    "efron1993": 'B. Efron and R. J. Tibshirani, <i>An Introduction to the Bootstrap</i>. New York, NY, USA: '
                 'Chapman & Hall, 1993.',
    "min2023": 'S. Min et al., "FActScore: Fine-grained atomic evaluation of factual precision in long form '
               'text generation," in <i>Proc. Conf. Empirical Methods in Natural Language Processing '
               '(EMNLP)</i>, 2023.',
    "mcnemar1947": 'Q. McNemar, "Note on the sampling error of the difference between correlated proportions '
                   'or percentages," <i>Psychometrika</i>, vol. 12, no. 2, pp. 153–157, 1947.',
    "zheng2023": 'L. Zheng et al., "Judging LLM-as-a-judge with MT-Bench and Chatbot Arena," in <i>Advances in '
                 'Neural Information Processing Systems (NeurIPS)</i>, vol. 36, Datasets and Benchmarks Track, '
                 '2023.',
    "grattafiori2024": 'A. Grattafiori et al., "The Llama 3 herd of models," arXiv:2407.21783, 2024.',
    "qwen2024": 'A. Yang et al., "Qwen2.5 technical report," arXiv:2412.15115, 2024.',
    "wang2020": 'W. Wang, F. Wei, L. Dong, H. Bao, N. Yang, and M. Zhou, "MiniLM: Deep self-attention '
                'distillation for task-agnostic compression of pre-trained transformers," in <i>Advances in '
                'Neural Information Processing Systems (NeurIPS)</i>, vol. 33, 2020, pp. 5776–5788.',
    "he2023": 'P. He, J. Gao, and W. Chen, "DeBERTaV3: Improving DeBERTa using ELECTRA-style pre-training with '
              'gradient-disentangled embedding sharing," in <i>Proc. Int. Conf. Learning Representations '
              '(ICLR)</i>, 2023, arXiv:2111.09543.',
    "davidson2019": 'C. Davidson-Pilon, "lifelines: Survival analysis in Python," <i>J. Open Source Softw.</i>, '
                    'vol. 4, no. 40, p. 1317, 2019.',
    "holm1979": 'S. Holm, "A simple sequentially rejective multiple test procedure," <i>Scand. J. Statist.</i>, '
                'vol. 6, no. 2, pp. 65–70, 1979.',
    "gutenberg": 'Project Gutenberg, "Free eBooks." [Online]. Available: https://www.gutenberg.org',
    "repo": 'N. Nayak, M. Singh, J. Singh, and S. Garg, "context-half-life: Code, raw logs, and paper source," '
            'GitHub repository, 2026. [Online]. Available: https://github.com/Namann-14/context-half-life',
}
