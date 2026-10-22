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
     It drives hallucination, unsettles reasoning, and wastes tokens, yet common fixes (truncation,
     summarization, compression, retrieval) shrink the context without measuring how quickly its contents
     decay."""),
    ("Objectives:", """We ask whether context quality can be measured rather than assumed, and define a
     <i>Context Half-Life</i>: the number of turns after which a piece of information has a 50% chance of
     no longer helping the model answer."""),
    ("Methods:", """Borrowing survival analysis from reliability and medical statistics, we estimate
     half-lives by ageing facts inside conversations, summarise a session with a Rot Index, and use both
     to drive a repair loop that UPDATEs outdated facts, MERGEs duplicates, and REMOVEs irrelevant
     material, while a protection set and verification with rollback shield knowledge that still matters.
     Repair works entirely at the context layer, so any LLM benefits without retraining. A lightweight
     reference implementation uses needle-in-a-haystack tests, rolling summaries, embedding-based
     de-duplication, and relevance pruning."""),
    ("Expected results:", """The framework will be evaluated on LongMemEval, LongBench v2, the Chroma
     Context Rot benchmark, and a synthetic rot-injection suite, using accuracy, reasoning quality,
     hallucination rate, token efficiency, and latency. We pre-register seven hypotheses and report no
     empirical numbers of our own."""),
    ("Conclusion:", """Measuring context quality reframes long-context reliability as maintenance that is
     repairable, quantifiable, and improvable without touching the model."""),
]

KEYWORDS = ("Context rot, context half-life, long-context reasoning, lost in the middle, "
            "needle-in-a-haystack, retrieval-augmented generation, context engineering")

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
        """<b>An evaluation protocol and reference implementation:</b> pre-registered experiments on public
        benchmarks plus a rot-injection suite, and short Python listings that reproduce the core
        measurements with free tools.""",
    ]),
    ("p", """Four research questions guide the study. <b>RQ1:</b> Can the value of contextual information be
     quantified as a decay process with a stable, predictive half-life? <b>RQ2:</b> Does half-life localise
     degradation (which segments, from which turn) better than context length? <b>RQ3:</b> Does
     half-life-guided repair improve accuracy, reasoning, and hallucination rate over baselines at equal or
     lower token cost? <b>RQ4:</b> Which operations contribute most, and at what latency? This paper
     specifies the framework and pre-registers its evaluation; it reports no empirical results, and worked
     examples use labelled illustrative values. Section II explains how LLMs read context, Section III
     reviews related work, Section IV presents the method, Section V the hypotheses and limitations, and
     Section VI concludes."""),

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
    ("h2", "Experimental design"),
    ("p", """<b>Benchmarks.</b> LongMemEval [@wu2025] (500 questions; the standard variant of about 115K
     tokens, a 500-session variant with retrieval, and an oracle upper bound), whose knowledge-update and
     temporal questions test staleness and whose abstention questions test hallucination; LongBench v2
     [@bai2025], whose mostly single-document tasks contain little stale content and so test whether gains
     depend on structural rot; the Chroma toolkit [@hong2025] for controlled manipulations of similarity,
     distractors, and structure; and our rot-injection suite with known decay times. Each is split 20%
     development and 80% test; all thresholds and prompts are frozen on the development split."""),
    ("p", """<b>Readers and baselines.</b> Two proprietary and two open-weight readers at fixed versions are
     compared against full context, a sliding window, rolling summarization, LLMLingua-style compression at
     matched budget [@jiang2023], retrieval over history [@wu2025], a Mem0-style memory [@chhikara2025],
     and where reproducible a learned manager [@yi2026]. Random and oldest-first repair at equal budget
     isolate the half-life signal; an oracle using true ablation utilities gives an upper bound."""),
    ("p", """<b>Metrics</b> are summarised in Table [#tab:metrics]. Hallucination is scored against the
     original history, so repair cannot hide errors by deleting evidence. The metric itself is validated
     by calibration (Brier score, time-dependent AUC), recovery of known half-lives and change points in
     the injection suite, rank correlation of R(t) with accuracy decline, likelihood-ratio tests of R(t)
     beyond token count, dose–response against random repair, and stability across readers and judges.
     Ablations remove each operation, the protection set, verification, and the adaptive trigger.
     Comparisons are paired: McNemar's test [@mcnemar1947], paired bootstrap intervals with 10,000
     resamples [@efron1993], and a multiple-comparison correction, reported as effect sizes with
     intervals."""),
    ("table", "tab:metrics", "Evaluation metrics",
     ["Dimension", "How it is computed"],
     [
         ["Task accuracy", "Correct answers ÷ questions (benchmark's own scorer or LLM-judge protocol)"],
         ["Reasoning quality", "Rubric score 0–4 from two LLM judges, with a human audit"],
         ["Hallucination rate", "Share of answers with a claim unsupported by the original history [@min2023]"],
         ["Token efficiency", "Input tokens per query; accuracy per 1,000 tokens"],
         ["Latency", "Median and 95th-percentile time; repair overhead; break-even session length"],
         ["Context health", "Type-level half-life H, Rot Index R(t), onset turn t*"],
     ],
     [0.95, 2.2], {"size": 7.5}),

    # ======================================================================== V. DISCUSSION
    ("h1", "Anticipated Results and Discussion"),
    ("h2", "Hypotheses"),
    ("p", """No empirical results are reported; each hypothesis states what would refute it, and numerical
     targets are design choices to be confirmed on development data."""),
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
    ("h2", "Implications and limitations"),
    ("p", """If H1–H3 hold, the unit of management shifts from the window to the segment: a system can ask
     how much of its context is still alive and repair before accuracy falls, logging R(t) beside latency
     and cost as a health signal. The estimator needs no access to model internals, so it suits API-only
     models and can feed memory layers, incremental context updates, or learned managers such as AdaCoM
     [@yi2026]. The main limitations are:"""),
    ("bullets", [
        """<b>Dependence:</b> half-life is conditional on the reader and the probe distribution, not a
        property of text alone.""",
        """<b>Estimation error:</b> leave-one-out utilities miss interactions, and false positives can delete
        needed content; protection, verification, and the archive limit but do not remove this risk.""",
        """<b>Evaluation:</b> LLM judges show position, verbosity, and self-preference biases [@zheng2023],
        benchmarks may be contaminated, and small pilots give wide intervals.""",
        """<b>Systems and security:</b> editing early context can invalidate prompt caches, and a repair
        layer is itself an attack surface (a poisoned tool result could trigger removal of real
        constraints), so every operation is logged and protected instructions are never changed
        unverified.""",
    ]),

    # ======================================================================== VI. CONCLUSION
    ("h1", "Conclusion and Future Scope"),
    ("p", """Long-horizon reliability is usually treated as a capacity problem; the evidence reviewed here
     shows it is also a maintenance problem. This paper proposed to measure decay directly. Context
     Half-Life defines it through a segment's counterfactual usefulness and summarises it as a median
     survival age, while the Rot Index and session half-life show where and when rot sets in. A three-tier
     estimator makes the metric usable with black-box models, and a verified update–merge–remove loop acts
     on it without retraining. The pre-registered evaluation is designed so that each claim can fail: if
     the hypotheses hold, long conversations depend less on window size and more on routine upkeep; if
     they fail, the results will show how much degradation is intrinsic to length [@du2025]. Future work
     includes learned hazard and repair policies [@yi2026], models for information that becomes relevant
     again, per-channel half-lives in multi-agent systems, modality-specific detectors for code and tool
     logs, cache-aware repair scheduling, a dedicated decay benchmark with ground-truth half-lives, and
     comparison with human forgetting curves [@ebbinghaus1885]."""),
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
}
