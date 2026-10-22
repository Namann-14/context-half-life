"""Half-life estimation: exponential and Weibull survival fits, Kaplan-Meier, bootstrap CIs.

Data layout: arrays of probe outcomes at fixed ages. ``hits[f, j]`` is 1 if fact f was still
answered correctly when probed at ``ages[j]``.
"""
import numpy as np
from scipy.optimize import minimize

LN2 = np.log(2.0)


def weibull_S(a, eta, kappa, p0=1.0):
    return p0 * np.exp(-(np.asarray(a, float) / eta) ** kappa)


def half_life(eta, kappa):
    """Age at which the decay term reaches 1/2: H = eta * (ln 2)^(1/kappa)."""
    return eta * LN2 ** (1.0 / kappa)


def _nll(theta, ages, k, n, form):
    p0 = 1 / (1 + np.exp(-theta[0]))
    eta = np.exp(theta[1])
    kappa = np.exp(theta[2]) if form == "weibull" else 1.0
    p = np.clip(weibull_S(ages, eta, kappa, p0), 1e-9, 1 - 1e-9)
    return -np.sum(k * np.log(p) + (n - k) * np.log(1 - p))


# [listing:fit]
def fit_survival(ages, hits, form="weibull"):
    """Binomial MLE of Weibull survival."""
    ages = np.asarray(ages, float)
    hits = np.asarray(hits)
    k = hits.sum(0)
    n = np.full(len(ages), hits.shape[0])
    best = None
    for e0 in (5, 20, 80, 300):
        x0 = [3.0, np.log(e0), 0.0]
        args = (ages, k, n, form)
        r = minimize(_nll, x0, args=args,
                     method="Nelder-Mead")
        if best is None or r.fun < best.fun:
            best = r
    p0 = 1 / (1 + np.exp(-best.x[0]))
    eta = float(np.exp(best.x[1]))
    kappa = 1.0
    if form == "weibull":
        kappa = float(np.exp(best.x[2]))
    return dict(p0=p0, eta=eta, kappa=kappa,
                lam=1 / eta,
                H=half_life(eta, kappa),
                nll=float(best.fun))
# [/listing]


def survival_at(fit, a):
    return weibull_S(a, fit["eta"], fit["kappa"], fit["p0"])


def absolute_half_life(fit, horizon=1e4):
    """Age at which S(a) = 0.5 (not relative to p0); 0 if S(0) <= 0.5."""
    if fit["p0"] <= 0.5:
        return 0.0
    a = fit["eta"] * np.log(2 * fit["p0"]) ** (1.0 / fit["kappa"])
    return float(min(a, horizon))


def bootstrap_fit(ages, hits, form="weibull", n_boot=2000, seed=0, alpha=0.05):
    """Resample facts with replacement; return percentile CIs for eta/kappa/H/p0."""
    hits = np.asarray(hits)
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_boot):
        idx = rng.integers(0, hits.shape[0], hits.shape[0])
        f = fit_survival(ages, hits[idx], form)
        rows.append((f["eta"], f["kappa"], f["H"], f["p0"]))
    rows = np.array(rows)

    def q(c):
        return tuple(np.quantile(rows[:, c], [alpha / 2, 1 - alpha / 2]).tolist())

    return dict(eta=q(0), kappa=q(1), H=q(2), p0=q(3))


def lrt_weibull_vs_exp(fit_w, fit_e):
    """Likelihood-ratio statistic and p-value (1 d.o.f.) for kappa = 1."""
    from scipy.stats import chi2
    stat = max(0.0, 2 * (fit_e["nll"] - fit_w["nll"]))
    return stat, float(chi2.sf(stat, 1))


def first_failure(hits, ages):
    """Per-fact (time, observed): first probed age with a miss; censored at the last age."""
    ages = np.asarray(ages)
    t, e = [], []
    for row in np.asarray(hits):
        miss = np.where(row == 0)[0]
        if len(miss):
            t.append(float(ages[miss[0]]))
            e.append(1)
        else:
            t.append(float(ages[-1]))
            e.append(0)
    return np.array(t), np.array(e)


def kaplan_meier(t, e):
    """Return (times, survival) step function starting at (0, 1)."""
    t, e = np.asarray(t, float), np.asarray(e, int)
    times, surv = [0.0], [1.0]
    s = 1.0
    for u in np.unique(t[e == 1]):
        at_risk = (t >= u).sum()
        d = ((t == u) & (e == 1)).sum()
        s *= 1 - d / at_risk
        times.append(float(u))
        surv.append(s)
    return np.array(times), np.array(surv)


def km_median(times, surv):
    below = np.where(np.asarray(surv) <= 0.5)[0]
    return float(times[below[0]]) if len(below) else float("inf")
