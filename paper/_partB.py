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
     when the GPU passes 78 °C. All calls together took roughly 85 minutes."""),
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
        (Section IV-F).""",
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
     absolute error is [$e3.onset_rot.mae|f1] turns (95% CI [$e3.onset_rot.mae_ci.lo|f1]–
     [$e3.onset_rot.mae_ci.hi|f1]), against [$e3.onset_ref.mae_uniform|f1] for a guess drawn uniformly over
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
     HL repair fired on every question (mean R̂ = [$e4.r_hat_mean|f2]) and cut the input from
     [$e4.tokens.B0|i] to [$e4.tokens.HL|i] tokens, but accuracy fell from [$e4.acc.B0|pct0]% to
     [$e4.acc.HL|pct0]% and hallucination rose from [$e4.halluc.B0|pct0]% to [$e4.halluc.HL|pct0]%. None of
     the paired differences against HL is significant after Holm's correction (Table [#tab:e4cmp]); the
     point estimates are a loss of [$e4.cmp.HL_vs_B0.diff|sgn1] points against full context, a tie with the
     sliding window, random removal, and oldest-first removal, and a gain of [$e4.cmp.HL_vs_B2.diff|sgn1]
     points over the rolling summary. In short, HL is as good as other ways of shrinking the context to about
     60% of its size, and none of them matched full context. The oracle, which sees only the evidence
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
     [$e4.cat.multi-session.B0|pct0]% (one question more); on abstention it ties full context at
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
     protection set, without verification, and with a token-budget trigger, the answers are the same as with
     full HL on all but at most one question, because UPDATE and MERGE almost never fired, the protection
     set and verification rarely mattered (verification rolled back
     [$e4.rolled_back.HL|pct1]% of questions, one question in [$e4.n_questions|i]), and the token trigger
     fired whenever R̂ did. Only removing REMOVE changes anything: accuracy rises to
     [$e4.acc.HL_noremove|pct0]% while the input stays at [$e4.tokens.HL_noremove|i] tokens, which confirms
     that REMOVE alone delivers the savings and also the losses."""),
    ("table", "tab:e5", "E5 ablations of HL repair (paired difference against full HL)",
     ["Variant", "Acc. (%)", "Diff. vs HL (points)", "Tokens", "Halluc. (%)"],
     [[name, f"[$e4.acc.{c}|pct0]",
       ("0.0 (0.0 to 0.0)" if c in ("HL_noupdate", "HL_nomerge", "HL_noprotect", "HL_noverify", "HL_tok")
        else f"[$e5.diff.{c}|sgn1] ([$e5.diff.{c}.lo|sgn1] to [$e5.diff.{c}.hi|sgn1])"),
       f"[$e4.tokens.{c}|i]", f"[$e4.halluc.{c}|pct0]"]
      for name, c in [("Full HL", "HL"), ("− UPDATE", "HL_noupdate"), ("− MERGE", "HL_nomerge"),
                      ("− REMOVE", "HL_noremove"), ("− protection", "HL_noprotect"),
                      ("− verification", "HL_noverify"), ("Token trigger", "HL_tok")]],
     [0.75, 0.45, 1.15, 0.45, 0.4], {"size": 7}),

    # ======================================================================== VII. DISCUSSION
    ("h1", "Discussion"),
    ("h2", "Verdict on each hypothesis"),
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
          "HL ties B1, random, and oldest-first; +[$e4.cmp.HL_vs_B2.diff.pct|f0]-point edge over B2 is "
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
