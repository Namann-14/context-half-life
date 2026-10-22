"""Turn raw JSONL logs in results/raw into results/summary/*.csv and results/paper_numbers.json.

Every number quoted in the paper comes from paper_numbers.json (flat keys such as "e4.acc.HL").
Sections whose raw logs are missing are skipped and reported as not run.

    python experiments/analyze.py
"""
import json

import numpy as np
import pandas as pd

from common import SUMMARY, read_jsonl
from context_half_life import halflife as hl
from context_half_life import rot, stats

MODEL = "llama3.2:3b"
MTAG = MODEL.replace(":", "_")
NUMS = {}


def put(key, value):
    if isinstance(value, (np.floating, np.integer)):
        value = value.item()
    NUMS[key] = value


def ci_put(prefix, m, lo, hi):
    put(prefix, m)
    put(prefix + ".lo", lo)
    put(prefix + ".hi", hi)


def save(df, name):
    SUMMARY.mkdir(parents=True, exist_ok=True)
    df.to_csv(SUMMARY / name, index=False)


# ------------------------------------------------------------------------------------------------ E1
def e1():
    rows = read_jsonl(f"e1_niah_{MTAG}")
    if not rows:
        put("e1.run", 0)
        return
    df = pd.DataFrame(rows)
    put("e1.run", 1)
    put("e1.n_calls", len(df))
    put("e1.n_needles", df.needle.nunique())
    grid = df.groupby(["wording", "length", "depth"]).correct.agg(["mean", "count"]).reset_index()
    save(grid.rename(columns={"mean": "accuracy", "count": "n"}), "e1_grid.csv")
    bl = df.groupby(["wording", "length"]).correct.mean().reset_index()
    save(bl, "e1_by_length.csv")
    for w in ("literal", "paraphrase"):
        sub = df[df.wording == w]
        m, lo, hi = stats.bootstrap_ci(sub.correct.values, n_boot=2000)
        ci_put(f"e1.acc.{w}", m, lo, hi)
        for L, g in sub.groupby("length"):
            put(f"e1.acc.{w}.{L}", g.correct.mean())
    piv = df.pivot_table(index=["length", "depth", "needle"], columns="wording", values="correct")
    piv = piv.dropna()
    n01, n10, p = stats.mcnemar_exact(piv["paraphrase"], piv["literal"])
    d, lo, hi = stats.paired_bootstrap_ci(piv["paraphrase"].values, piv["literal"].values, n_boot=5000)
    put("e1.para_minus_lit", d)
    put("e1.para_minus_lit.lo", lo)
    put("e1.para_minus_lit.hi", hi)
    put("e1.mcnemar_p", p)
    lit = df[df.wording == "literal"]
    # position effect: accuracy at middle depths (0.3-0.7) vs ends (0, 0.1, 0.9, 1)
    mid = lit[lit.depth.between(0.3, 0.7)].correct.mean()
    end = lit[(lit.depth <= 0.1) | (lit.depth >= 0.9)].correct.mean()
    put("e1.lit.mid_depth", mid)
    put("e1.lit.end_depth", end)
    put("e1.wall_s_mean", df.wall_s.mean())


# ------------------------------------------------------------------------------------------------ E2
def e2_mode(mode):
    rows = read_jsonl(f"e2_{mode}_{MTAG}")
    if not rows:
        put(f"e2.{mode}.run", 0)
        return
    df = pd.DataFrame(rows)
    put(f"e2.{mode}.run", 1)
    put(f"e2.{mode}.n_calls", len(df))
    ages = sorted(df.age.unique())
    fit_rows, km_rows, surv_rows = [], [], []
    km_inputs = {}
    for kind, g in df.groupby("kind"):
        hits = g.pivot_table(index="fact", columns="age", values="correct").dropna()[ages].values.astype(int)
        n = hits.shape[0]
        for a_i, a in enumerate(ages):
            surv_rows.append(dict(mode=mode, kind=kind, age=a, survival=hits[:, a_i].mean(), n=n))
            put(f"e2.{mode}.{kind}.S{a}", hits[:, a_i].mean())
        put(f"e2.{mode}.{kind}.n_facts", n)
        t, e = hl.first_failure(hits, ages)
        km_inputs[kind] = (t, e)
        tm, sm = hl.kaplan_meier(t, e)
        for x, y in zip(tm, sm):
            km_rows.append(dict(mode=mode, kind=kind, age=x, survival=y))
        med = hl.km_median(tm, sm)
        put(f"e2.{mode}.{kind}.km_median", med if np.isfinite(med) else None)
        fw, fe = hl.fit_survival(ages, hits, "weibull"), hl.fit_survival(ages, hits, "exp")
        cw = hl.bootstrap_fit(ages, hits, "weibull", n_boot=500, seed=1)
        ce = hl.bootstrap_fit(ages, hits, "exp", n_boot=500, seed=2)
        stat, p = hl.lrt_weibull_vs_exp(fw, fe)
        flat = fw["p0"] > 0.9 and surv_rows[-1]["survival"] > 0.9
        fit_rows.append(dict(
            mode=mode, kind=kind, n_facts=n, S_last=surv_rows[-1]["survival"],
            exp_lambda=fe["lam"], exp_H=fe["H"], exp_H_lo=ce["H"][0], exp_H_hi=ce["H"][1],
            wb_eta=fw["eta"], wb_kappa=fw["kappa"], wb_kappa_lo=cw["kappa"][0], wb_kappa_hi=cw["kappa"][1],
            wb_p0=fw["p0"], wb_H=fw["H"], wb_H_lo=cw["H"][0], wb_H_hi=cw["H"][1],
            lrt_stat=stat, lrt_p=p, aic_exp=2 * 2 + 2 * fe["nll"], aic_wb=2 * 3 + 2 * fw["nll"],
            right_censored=bool(flat)))
        if flat:  # no decay observed inside the horizon: H is right-censored, fitted values are meaningless
            for k in ("exp_lambda", "exp_H", "exp_H_lo", "exp_H_hi", "wb_eta", "wb_kappa", "wb_kappa_lo",
                      "wb_kappa_hi", "wb_H", "wb_H_lo", "wb_H_hi", "lrt_stat", "lrt_p"):
                fit_rows[-1][k] = None
        for k, v in fit_rows[-1].items():
            if isinstance(v, (int, float, np.floating, bool)) and k not in ("mode",):
                put(f"e2.{mode}.{kind}.{k}", v)
    save(pd.DataFrame(fit_rows), f"e2_{mode}_fits.csv")
    save(pd.DataFrame(km_rows), f"e2_{mode}_km.csv")
    save(pd.DataFrame(surv_rows), f"e2_{mode}_survival.csv")
    # log-rank across types
    from lifelines.statistics import multivariate_logrank_test
    T = np.concatenate([v[0] for v in km_inputs.values()])
    E = np.concatenate([v[1] for v in km_inputs.values()])
    grp = np.concatenate([[k] * len(v[0]) for k, v in km_inputs.items()])
    if E.sum() > 0:
        r = multivariate_logrank_test(T, grp, E)
        put(f"e2.{mode}.logrank_p", float(r.p_value))
        put(f"e2.{mode}.logrank_stat", float(r.test_statistic))
    else:
        put(f"e2.{mode}.logrank_p", None)
    # leave-facts-out discrete-time model: miss ~ kind + age
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold
    d = df.copy()
    d["miss"] = 1 - d.correct
    if d.miss.nunique() == 2:
        X = pd.get_dummies(d[["kind"]]).astype(float)
        X["age"] = d.age.values / 80.0
        groups = d.kind + "_" + d.fact.astype(str)
        pred = np.zeros(len(d))
        for tr, te in GroupKFold(5).split(X, d.miss, groups):
            m = LogisticRegression(C=10.0, max_iter=500).fit(X.iloc[tr], d.miss.iloc[tr])
            pred[te] = m.predict_proba(X.iloc[te])[:, 1]
        put(f"e2.{mode}.hazard_auc", roc_auc_score(d.miss, pred))
    else:
        put(f"e2.{mode}.hazard_auc", None)
    if "stale_hit" in df:
        sh = df[df.kind == "changing"].groupby("age").stale_hit.mean()
        for a, v in sh.items():
            put(f"e2.{mode}.stale_rate.{a}", v)


# ------------------------------------------------------------------------------------------------ E3
def e3():
    det = read_jsonl("e3_detect")
    if not det:
        put("e3.run", 0)
        return
    put("e3.run", 1)
    put("e3.n_test_sessions", len(det))
    th = json.loads((SUMMARY / "e3_thresholds.json").read_text())
    put("e3.dup", th["dup"])
    put("e3.rel", th["rel"])
    rows = []
    for mode in ("stale", "contradictory", "redundant", "irrelevant"):
        for k in ("precision", "recall"):
            v = np.array([r[mode][k] for r in det])
            m, lo, hi = stats.bootstrap_ci(v, n_boot=2000)
            ci_put(f"e3.{mode}.{k}", m, lo, hi)
        put(f"e3.{mode}.n_true", sum(r[mode]["n_true"] for r in det))
        put(f"e3.{mode}.n_pred", sum(r[mode]["n_pred"] for r in det))
        rows.append(dict(mode=mode, precision=NUMS[f"e3.{mode}.precision"], recall=NUMS[f"e3.{mode}.recall"],
                         n_true=NUMS[f"e3.{mode}.n_true"], n_pred=NUMS[f"e3.{mode}.n_pred"]))
    save(pd.DataFrame(rows), "e3_detectors.csv")
    c = np.array([r["change_point"] for r in det], float)
    on = np.array([np.nan if r["onset_rot"] is None else r["onset_rot"] for r in det], float)
    err = on - c
    ok = ~np.isnan(err)
    put("e3.onset_rot.mae", np.abs(err[ok]).mean())
    put("e3.onset_rot.bias", err[ok].mean())
    put("e3.onset_rot.within5", (np.abs(err[ok]) <= 5).mean())
    m, lo, hi = stats.bootstrap_ci(np.abs(err[ok]), n_boot=2000)
    ci_put("e3.onset_rot.mae_ci", m, lo, hi)
    put("e3.onset_rot.corr", float(np.corrcoef(c[ok], on[ok])[0, 1]) if ok.sum() > 2 else None)
    # random-guess reference: onset drawn uniformly over the session
    put("e3.onset_ref.mae_uniform", float(np.mean([abs(t - c[ok]).mean() for t in range(1, 41)])))
    save(pd.DataFrame(dict(seed=[r["seed"] for r in det], change_point=c, onset_rot=on)), "e3_onset.csv")

    rd = read_jsonl(f"e3_reader_{MTAG}")
    if not rd:
        put("e3.reader.run", 0)
        return
    put("e3.reader.run", 1)
    df = pd.DataFrame(rd)
    put("e3.reader.n_calls", len(df))
    rot_df = df[df.variant == "rot"]
    acc_t = rot_df.groupby("turn").correct.mean().reset_index()
    save(acc_t, "e3_accuracy_by_turn.csv")
    put("e3.reader.acc_rot_overall", rot_df.correct.mean())
    # accuracy-based onset per session
    onsets, cps = [], []
    for seed, g in rot_df.groupby("seed"):
        s = g.groupby("turn").correct.mean().sort_index()
        if len(s) >= 6 and s.nunique() > 1:
            onsets.append(rot.onset_from_series(list(s.index), s.values))
            cps.append(g.change_point.iloc[0])
    put("e3.onset_acc.n", len(onsets))
    if onsets:
        e = np.abs(np.array(onsets, float) - np.array(cps, float))
        put("e3.onset_acc.mae", e.mean())
    # twin (end of session, same turn structure, no rot)
    end_rot = df[(df.variant == "rot") & (df.turn == 40)].set_index(["seed", "attr"]).correct
    twin = df[df.variant == "twin"].set_index(["seed", "attr"]).correct
    idx = end_rot.index.intersection(twin.index)
    if len(idx):
        a, b = twin.loc[idx].values, end_rot.loc[idx].values
        n01, n10, p = stats.mcnemar_exact(a, b)
        dd, lo, hi = stats.paired_bootstrap_ci(a, b, n_boot=5000)
        put("e3.twin.acc_twin", a.mean())
        put("e3.twin.acc_rot", b.mean())
        put("e3.twin.diff", dd)
        put("e3.twin.diff.lo", lo)
        put("e3.twin.diff.hi", hi)
        put("e3.twin.mcnemar_p", p)
        put("e3.twin.n", len(idx))
    # H2: does the Rot Index add to token count? likelihood-ratio test of nested logistic models
    rs = {r["seed"]: r["rot_series"] for r in det}
    d = rot_df.copy()
    d["rhat"] = [rs[s][min(t, len(rs[s])) - 1] for s, t in zip(d.seed, d.turn)]
    d["tok"] = d.prompt_tokens / 1000.0
    from scipy.stats import chi2
    from sklearn.linear_model import LogisticRegression

    def ll(X):
        m = LogisticRegression(C=1e6, max_iter=1000).fit(X, d.correct)
        p = np.clip(m.predict_proba(X)[:, 1], 1e-9, 1 - 1e-9)
        return float(np.sum(d.correct * np.log(p) + (1 - d.correct) * np.log(1 - p)))

    if d.correct.nunique() == 2:
        l0, l1 = ll(d[["tok"]].values), ll(d[["tok", "rhat"]].values)
        stat = max(0.0, 2 * (l1 - l0))
        put("e3.h2.lrt_stat", stat)
        put("e3.h2.lrt_p", float(chi2.sf(stat, 1)))
        put("e3.h2.corr_rhat_acc", float(np.corrcoef(d.rhat, d.correct)[0, 1]))
        put("e3.h2.corr_tok_acc", float(np.corrcoef(d.tok, d.correct)[0, 1]))
    else:
        put("e3.h2.lrt_p", None)


# ------------------------------------------------------------------------------------------------ E4/E5
MAIN = ["B0", "B1", "B2", "RND", "OLD", "HL", "ORACLE"]
ABL = ["HL", "HL_noupdate", "HL_nomerge", "HL_noremove", "HL_noprotect", "HL_noverify", "HL_tok"]


def e4():
    ans = read_jsonl(f"e4_answers_{MTAG}")
    jud = read_jsonl("e4_judge_qwen2.5_3b")
    if not ans or not jud:
        put("e4.run", 0)
        return
    put("e4.run", 1)
    a = pd.DataFrame(ans)
    j = pd.DataFrame(jud)[["answer_key", "correct"]].rename(columns={"answer_key": "key"})
    df = a.merge(j, on="key")
    meta = pd.DataFrame(read_jsonl("e4_meta")).drop_duplicates("qid")
    put("e4.n_questions", df.qid.nunique())
    for cat, n in df[df.condition == "B0"].groupby("category").size().items():
        put(f"e4.n.{cat}", n)
    put("e4.triggered_frac", meta.triggered.mean())
    put("e4.r_hat_mean", meta.r_hat.mean())
    put("e4.repair_s_mean", meta.repair_s.mean())
    put("e4.n_stale_mean", meta.n_stale.mean())
    put("e4.n_redundant_mean", meta.n_redundant.mean())
    put("e4.n_irrelevant_mean", meta.n_irrelevant.mean())
    df["halluc"] = ((df.correct == 0) & (df.abstained == 0)).astype(int)
    qs = sorted(df.qid.unique())
    rows = []
    for cond in MAIN + ABL[1:]:
        g = df[df.condition == cond].set_index("qid").reindex(qs)
        if g.correct.isna().any():
            continue
        acc = g.correct.values
        m, lo, hi = stats.bootstrap_ci(acc, n_boot=5000)
        tok = g.prompt_tokens.mean()
        rows.append(dict(condition=cond, accuracy=m, acc_lo=lo, acc_hi=hi, halluc=g.halluc.mean(),
                         input_tokens=tok, acc_per_1k=m / (tok / 1000), p50_s=g.wall_s.quantile(.5),
                         p95_s=g.wall_s.quantile(.95), rolled_back=g.get("rolled_back", pd.Series([0])).mean()))
        put(f"e4.acc.{cond}", m)
        put(f"e4.acc.{cond}.lo", lo)
        put(f"e4.acc.{cond}.hi", hi)
        put(f"e4.halluc.{cond}", g.halluc.mean())
        put(f"e4.tokens.{cond}", tok)
        put(f"e4.acc_per_1k.{cond}", m / (tok / 1000))
        put(f"e4.p50.{cond}", g.wall_s.quantile(.5))
        put(f"e4.p95.{cond}", g.wall_s.quantile(.95))
        put(f"e4.rolled_back.{cond}", float(g["rolled_back"].mean()))
    save(pd.DataFrame(rows), "e4_main.csv")
    # per-category accuracy (H3)
    cat_rows = []
    for cat, g0 in df.groupby("category"):
        for cond in ("B0", "HL", "B1", "B2"):
            g = g0[g0.condition == cond]
            if len(g):
                m, lo, hi = stats.bootstrap_ci(g.correct.values, n_boot=2000)
                cat_rows.append(dict(category=cat, condition=cond, accuracy=m, lo=lo, hi=hi, n=len(g)))
                put(f"e4.cat.{cat}.{cond}", m)
    save(pd.DataFrame(cat_rows), "e4_by_category.csv")
    # paired tests against HL (Holm over the four comparisons in the main family)
    wide = df.pivot(index="qid", columns="condition", values="correct")
    cmp_rows = []
    fam = ["B0", "B1", "B2", "RND", "OLD"]
    pv = []
    for c in fam:
        n01, n10, p = stats.mcnemar_exact(wide["HL"], wide[c])
        d, lo, hi = stats.paired_bootstrap_ci(wide["HL"].values, wide[c].values, n_boot=10000)
        pv.append(p)
        cmp_rows.append(dict(comparison=f"HL - {c}", diff=d, lo=lo, hi=hi, hl_only=n10, other_only=n01, p=p))
    adj = stats.holm(pv)
    for r, ap in zip(cmp_rows, adj):
        r["p_holm"] = ap
        c = r["comparison"].split(" - ")[1]
        for k in ("diff", "lo", "hi", "p", "p_holm", "hl_only", "other_only"):
            put(f"e4.cmp.HL_vs_{c}.{k}", r[k])
    save(pd.DataFrame(cmp_rows), "e4_paired.csv")
    # H5/E5 ablation: differences against HL
    ab_rows = []
    for c in ABL[1:]:
        if c not in wide:
            continue
        d, lo, hi = stats.paired_bootstrap_ci(wide[c].values, wide["HL"].values, n_boot=5000)
        n01, n10, p = stats.mcnemar_exact(wide[c], wide["HL"])
        ab_rows.append(dict(condition=c, diff_vs_HL=d, lo=lo, hi=hi, p=p,
                            tokens=NUMS.get(f"e4.tokens.{c}"), acc=NUMS.get(f"e4.acc.{c}"),
                            halluc=NUMS.get(f"e4.halluc.{c}")))
        put(f"e5.diff.{c}", d)
        put(f"e5.diff.{c}.lo", lo)
        put(f"e5.diff.{c}.hi", hi)
        put(f"e5.p.{c}", p)
    save(pd.DataFrame(ab_rows), "e5_ablation.csv")
    # H7: latency break-even (HL reader time + repair overhead vs full-context reader time)
    t_b0 = df[df.condition == "B0"].set_index("qid").wall_s.reindex(qs)
    t_hl = df[df.condition == "HL"].set_index("qid").wall_s.reindex(qs)
    ov = meta.set_index("qid").repair_s.reindex(qs)
    put("e4.latency.b0_mean", t_b0.mean())
    put("e4.latency.hl_reader_mean", t_hl.mean())
    put("e4.latency.hl_total_mean", (t_hl + ov).mean())
    put("e4.latency.saved_reader_s", (t_b0 - t_hl).mean())


def main():
    SUMMARY.mkdir(parents=True, exist_ok=True)
    e1()
    e2_mode("ageing")
    e2_mode("matched")
    e3()
    e4()
    (SUMMARY.parent / "paper_numbers.json").write_text(json.dumps(NUMS, indent=1, sort_keys=True))
    print(f"wrote {len(NUMS)} numbers to results/paper_numbers.json")


if __name__ == "__main__":
    main()
