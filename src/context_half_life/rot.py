"""Live fraction L(t), Rot Index R(t), session half-life H(C), and change-point onset t*."""
import numpy as np


def live_fraction(segments, survival, t):
    """segments: dicts with 'birth', 'tokens', 'type'. survival(type, age) -> [0, 1]."""
    tot = sum(s["tokens"] for s in segments if s["birth"] <= t)
    if tot == 0:
        return 1.0
    live = sum(s["tokens"] * survival(s["type"], t - s["birth"])
               for s in segments if s["birth"] <= t)
    return live / tot


def rot_index(segments, survival, t):
    return 1.0 - live_fraction(segments, survival, t)


def session_half_life(segments, survival, turns):
    for t in range(turns + 1):
        if live_fraction(segments, survival, t) <= 0.5:
            return t
    return None


def change_point(y):
    """Single mean-shift change point by least squares; index of the first element of the new regime."""
    y = np.asarray(y, float)
    best, arg = np.inf, None
    for k in range(2, len(y) - 1):
        sse = ((y[:k] - y[:k].mean()) ** 2).sum() + ((y[k:] - y[k:].mean()) ** 2).sum()
        if sse < best:
            best, arg = sse, k
    return arg


def onset_from_series(turns, y):
    k = change_point(y)
    return None if k is None else turns[k]
