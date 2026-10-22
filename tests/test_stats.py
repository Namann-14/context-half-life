import numpy as np

from context_half_life import stats


def test_mcnemar_exact_known_value():
    a = [1] * 9 + [0] * 1 + [1] * 5
    b = [0] * 9 + [1] * 1 + [1] * 5
    n01, n10, p = stats.mcnemar_exact(a, b)
    assert (n01, n10) == (1, 9)
    assert abs(p - 0.021484375) < 1e-9  # 2 * P(X <= 1 | n=10, .5)


def test_mcnemar_no_discordant():
    assert stats.mcnemar_exact([1, 0], [1, 0])[2] == 1.0


def test_holm():
    adj = stats.holm([0.01, 0.04, 0.03])
    assert np.allclose(adj, [0.03, 0.06, 0.06])


def test_paired_bootstrap_ci_brackets_difference():
    rng = np.random.default_rng(0)
    b = (rng.random(300) < 0.5).astype(int)
    a = np.where(rng.random(300) < 0.2, 1, b)
    d, lo, hi = stats.paired_bootstrap_ci(a, b, n_boot=2000, seed=1)
    assert lo <= d <= hi and d > 0
