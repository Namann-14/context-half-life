import numpy as np

from context_half_life import halflife as hl


def simulate(eta, kappa, p0, ages, n, seed):
    rng = np.random.default_rng(seed)
    S = hl.weibull_S(ages, eta, kappa, p0)
    return (rng.random((n, len(ages))) < S).astype(int)


def test_recovers_exponential():
    ages = np.array([0, 5, 10, 20, 40, 80])
    lam = 0.02
    hits = simulate(1 / lam, 1.0, 1.0, ages, 4000, 1)
    f = hl.fit_survival(ages, hits, "exp")
    assert abs(f["lam"] - lam) < 0.003
    assert abs(f["H"] - np.log(2) / lam) < 3


def test_recovers_weibull_shape():
    ages = np.array([0, 5, 10, 20, 40, 80])
    hits = simulate(25.0, 2.0, 0.95, ages, 6000, 2)
    f = hl.fit_survival(ages, hits, "weibull")
    assert abs(f["kappa"] - 2.0) < 0.3
    assert abs(f["eta"] - 25.0) < 3


def test_lrt_detects_non_exponential():
    ages = np.array([0, 5, 10, 20, 40, 80])
    hits = simulate(25.0, 2.0, 1.0, ages, 1000, 3)
    w, e = hl.fit_survival(ages, hits, "weibull"), hl.fit_survival(ages, hits, "exp")
    stat, p = hl.lrt_weibull_vs_exp(w, e)
    assert p < 0.01


def test_kaplan_meier_matches_hand_calculation():
    t = np.array([1, 2, 2, 3, 4])
    e = np.array([1, 1, 0, 1, 0])
    times, s = hl.kaplan_meier(t, e)
    # t=1: 1/5 fail -> .8 ; t=2: 1/4 -> .6 ; t=3: 1/2 -> .3
    assert np.allclose(s, [1.0, 0.8, 0.6, 0.3])
    assert hl.km_median(times, s) == 3.0


def test_first_failure_censoring():
    hits = np.array([[1, 1, 1], [1, 0, 1], [0, 0, 0]])
    t, e = hl.first_failure(hits, [0, 10, 20])
    assert t.tolist() == [20.0, 10.0, 0.0] and e.tolist() == [0, 1, 1]


def test_bootstrap_ci_contains_truth():
    ages = np.array([0, 5, 10, 20, 40, 80])
    hits = simulate(30.0, 1.0, 1.0, ages, 300, 4)
    ci = hl.bootstrap_fit(ages, hits, "exp", n_boot=150, seed=1)
    assert ci["H"][0] < 30 * np.log(2) < ci["H"][1]
