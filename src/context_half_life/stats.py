"""Paired comparisons: exact McNemar, paired bootstrap CIs, Holm correction."""
import numpy as np
from scipy.stats import binomtest


def mcnemar_exact(a, b):
    """Exact two-sided McNemar test on paired 0/1 outcomes. Returns (n01, n10, p)."""
    a, b = np.asarray(a, int), np.asarray(b, int)
    n10 = int(((a == 1) & (b == 0)).sum())
    n01 = int(((a == 0) & (b == 1)).sum())
    n = n10 + n01
    p = 1.0 if n == 0 else float(binomtest(min(n10, n01), n, 0.5).pvalue)
    return n01, n10, p


def paired_bootstrap_ci(a, b, stat=np.mean, n_boot=10_000, alpha=0.05, seed=0):
    """CI of stat(a) - stat(b), resampling question indices jointly."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(n_boot, len(a)))
    diffs = np.array([stat(a[i]) - stat(b[i]) for i in idx]) if stat is not np.mean else \
        a[idx].mean(1) - b[idx].mean(1)
    lo, hi = np.quantile(diffs, [alpha / 2, 1 - alpha / 2])
    return float(stat(a) - stat(b)), float(lo), float(hi)


def bootstrap_ci(x, n_boot=10_000, alpha=0.05, seed=0):
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), size=(n_boot, len(x)))].mean(1)
    lo, hi = np.quantile(m, [alpha / 2, 1 - alpha / 2])
    return float(x.mean()), float(lo), float(hi)


def holm(pvalues):
    """Holm-Bonferroni adjusted p-values, returned in the input order."""
    p = np.asarray(pvalues, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    m = len(p)
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj.tolist()
