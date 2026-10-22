"""Figures made from measured results. Reads only results/summary/*.csv (never hard-coded numbers).

fig_e1_niah      E1 heat maps (literal vs paraphrased question) and accuracy by context length.
fig_e2_survival  E2 empirical survival, Kaplan-Meier steps and fitted Weibull curves.
fig_e3_detect    E3 detector precision/recall, onset recovery, reader accuracy by turn.
fig_e4_repair    E4 accuracy vs input tokens, per-category accuracy, latency.

Run from the repository root:  python paper/make_result_figures.py
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_figures import AQUA, AXIS, BLUE, INK, INK2, MAGENTA, MUTED, ORANGE, YELLOW, style_axes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SUM = ROOT / "results" / "summary"
OUT = Path(__file__).resolve().parent / "figures"
KIND_COLOR = {"preference": AQUA, "changing": ORANGE, "tool": BLUE}
KIND_NAME = {"preference": "stable preference", "changing": "changing value", "tool": "number in tool output"}


def panel_label(ax, text):
    ax.text(-0.02, 1.08, text, transform=ax.transAxes, fontsize=7.5, fontweight="bold", color=INK)


def fig_e1():
    g = pd.read_csv(SUM / "e1_grid.csv")
    lens = sorted(g.length.unique())
    depths = sorted(g.depth.unique())
    fig = plt.figure(figsize=(6.4, 2.0))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.15, 1.15, 0.06, 0.95], wspace=0.5)
    axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), None, fig.add_subplot(gs[0, 3])]
    cax = fig.add_subplot(gs[0, 2])
    for ax, w, lab in zip(axes[:2], ("literal", "paraphrase"), ("(a) literal question", "(b) paraphrased question")):
        sub = g[g.wording == w].pivot(index="length", columns="depth", values="accuracy").reindex(lens)[depths]
        im = ax.imshow(sub.values, vmin=0, vmax=1, cmap="Blues", aspect="auto", origin="lower")
        ax.set_xticks(range(0, len(depths), 2))
        ax.set_xticklabels([f"{int(d * 100)}" for d in depths[::2]])
        ax.set_yticks(range(len(lens)))
        ax.set_yticklabels([f"{L // 1024}K" for L in lens])
        ax.set_xlabel("Needle depth (%)")
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        for i in range(sub.shape[0]):
            for j in range(sub.shape[1]):
                v = sub.values[i, j]
                ax.text(j, i, f"{100 * v:.0f}", ha="center", va="center", fontsize=4.6,
                        color="white" if v > 0.6 else INK2)
        ax.set_title(lab, fontsize=7, loc="left", color=INK)
    axes[0].set_ylabel("Context length (tokens)")
    cb = fig.colorbar(im, cax=cax)
    cb.ax.tick_params(labelsize=6, length=0)
    cb.outline.set_visible(False)
    bl = pd.read_csv(SUM / "e1_by_length.csv")
    ax = axes[3]
    style_axes(ax)
    for w, c in (("literal", BLUE), ("paraphrase", ORANGE)):
        s = bl[bl.wording == w]
        ax.plot(s.length / 1024, s.correct, "-o", color=c, markersize=3, linewidth=1.5, label=w)
    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 2, 4, 8, 16])
    ax.set_xticklabels(["1K", "2K", "4K", "8K", "16K"])
    ax.set_ylim(0, 1)
    ax.set_xlabel("Context length")
    ax.set_ylabel("Accuracy")
    ax.legend(frameon=False, fontsize=6.3, labelcolor=INK2)
    ax.set_title("(c) accuracy by length", fontsize=7, loc="left", color=INK)
    fig.savefig(OUT / "fig_e1_niah.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)


def fig_e2():
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.25), sharey=True)
    for ax, mode, title in zip(axes, ("ageing", "matched"),
                               ("(a) fact followed by a-turn of filler", "(b) length-matched control (80 turns total)")):
        style_axes(ax)
        surv = pd.read_csv(SUM / f"e2_{mode}_survival.csv")
        km = pd.read_csv(SUM / f"e2_{mode}_km.csv")
        fits = pd.read_csv(SUM / f"e2_{mode}_fits.csv").set_index("kind")
        for kind, c in KIND_COLOR.items():
            s = surv[surv.kind == kind]
            k = km[km.kind == kind]
            ax.step(k.age, k.survival, where="post", color=c, linewidth=1.0, alpha=0.55)
            ax.plot(s.age, s.survival, "o", color=c, markersize=3.6, markeredgecolor="white",
                    markeredgewidth=0.6, label=f"{KIND_NAME[kind]} (n={int(s.n.iloc[0])})")
            f = fits.loc[kind]
            if pd.notna(f.wb_eta):
                a = np.linspace(0, 80, 200)
                ax.plot(a, f.wb_p0 * np.exp(-(a / f.wb_eta) ** f.wb_kappa), "--", color=c, linewidth=1.0)
        ax.axhline(0.5, color=MUTED, linewidth=0.7, linestyle=(0, (3, 2)))
        ax.set_xlim(-2, 82)
        ax.set_ylim(0, 1.05)
        ax.set_xlabel("Age of fact a (turns)")
        ax.set_title(title, fontsize=7, loc="left", color=INK)
    axes[0].set_ylabel("Fraction answered correctly, S(a)")
    axes[0].legend(frameon=False, fontsize=6.0, loc="lower left", labelcolor=INK2, handlelength=1.2)
    fig.tight_layout(w_pad=1.0)
    fig.savefig(OUT / "fig_e2_survival.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)


def fig_e3():
    det = pd.read_csv(SUM / "e3_detectors.csv")
    onset = pd.read_csv(SUM / "e3_onset.csv").dropna()
    acc = pd.read_csv(SUM / "e3_accuracy_by_turn.csv")
    fig, axes = plt.subplots(1, 3, figsize=(6.4, 2.1), gridspec_kw={"width_ratios": [1.1, 0.9, 1]})
    ax = axes[0]
    style_axes(ax)
    x = np.arange(len(det))
    ax.bar(x - 0.19, det.precision, 0.36, color=BLUE, label="precision")
    ax.bar(x + 0.19, det.recall, 0.36, color=ORANGE, label="recall")
    ax.set_xticks(x)
    names = {"contradictory": "contra-\ndictory", "irrelevant": "irrele-\nvant"}
    ax.set_xticklabels([names.get(m, m) for m in det["mode"]], fontsize=5.8)
    ax.set_ylim(0, 1.3)
    ax.set_ylabel("Score (test sessions)")
    ax.legend(frameon=False, fontsize=6.2, ncol=2, loc="upper center", labelcolor=INK2)
    ax.set_title("(a) detectors per decay mode", fontsize=7, loc="left", color=INK)
    ax = axes[1]
    style_axes(ax)
    ax.plot([5, 25], [5, 25], color=MUTED, linewidth=0.8, linestyle=(0, (3, 2)))
    rng = np.random.default_rng(0)
    ax.plot(onset.change_point + rng.normal(0, 0.12, len(onset)), onset.onset_rot, "o", color=BLUE,
            markersize=3.2, alpha=0.7, markeredgewidth=0)
    ax.set_xlabel("Injected change point c (turn)")
    ax.set_ylabel("Estimated onset t* (turn)")
    ax.set_title("(b) onset recovery", fontsize=7, loc="left", color=INK)
    ax = axes[2]
    style_axes(ax)
    ax.plot(acc.turn, acc.correct, "-o", color=ORANGE, markersize=3, linewidth=1.4)
    ax.axvspan(10, 20, color=BLUE, alpha=0.12, linewidth=0)
    ax.text(15, 0.04, "range of c", ha="center", fontsize=6, color=INK2)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Checkpoint turn")
    ax.set_ylabel("Reader accuracy")
    ax.set_title("(c) accuracy through the session", fontsize=7, loc="left", color=INK)
    fig.tight_layout(w_pad=1.0)
    fig.savefig(OUT / "fig_e3_detect.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)


def fig_e4():
    m = pd.read_csv(SUM / "e4_main.csv").set_index("condition")
    cat = pd.read_csv(SUM / "e4_by_category.csv")
    main = ["B0", "B1", "B2", "RND", "OLD", "HL", "ORACLE"]
    colors = {"B0": INK2, "B1": BLUE, "B2": AQUA, "RND": MUTED, "OLD": YELLOW, "HL": ORANGE, "ORACLE": MAGENTA}
    fig, axes = plt.subplots(1, 3, figsize=(6.4, 2.25), gridspec_kw={"width_ratios": [1.15, 1.15, 0.8]})
    ax = axes[0]
    style_axes(ax)
    for c in main:
        r = m.loc[c]
        ax.errorbar(r.input_tokens / 1000, 100 * r.accuracy, yerr=[[100 * (r.accuracy - r.acc_lo)],
                    [100 * (r.acc_hi - r.accuracy)]], fmt="o", color=colors[c], markersize=4, linewidth=0.8,
                    capsize=1.5, markeredgecolor="white", markeredgewidth=0.5)
        if c in ("B1", "RND", "OLD"):
            continue
        off = {"HL": (4, -9), "B2": (4, 3), "B0": (-4, 8), "ORACLE": (3, 4)}[c]
        ax.annotate(c, (r.input_tokens / 1000, 100 * r.accuracy), xytext=off, textcoords="offset points",
                    fontsize=5.8, color=INK2)
    ax.annotate("B1, RND, OLD", (4.69, 45.7), xytext=(10, -24), textcoords="offset points", fontsize=5.8,
                color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    ax.set_xlabel("Mean input tokens (thousands)")
    ax.set_ylabel("Accuracy (%), 95% CI")
    ax.set_title("(a) accuracy vs. cost", fontsize=7, loc="left", color=INK)
    ax = axes[1]
    style_axes(ax)
    cats = ["single-session-user", "multi-session", "temporal-reasoning", "knowledge-update", "abstention"]
    short = {"single-session-user": "single", "multi-session": "multi", "temporal-reasoning": "temporal",
             "knowledge-update": "k-update", "abstention": "abstain"}
    conds = [("B0", INK2), ("B1", BLUE), ("HL", ORANGE)]
    w = 0.26
    for i, (c, col) in enumerate(conds):
        vals = [cat[(cat.category == k) & (cat.condition == c)].accuracy.iloc[0] * 100 for k in cats]
        ax.bar(np.arange(len(cats)) + (i - 1) * w, vals, w, color=col, label=c)
    ns = [int(cat[(cat.category == k) & (cat.condition == "B0")].n.iloc[0]) for k in cats]
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels([f"{short[k]}\nn={n}" for k, n in zip(cats, ns)], fontsize=5.6)
    ax.set_ylim(0, 112)
    ax.set_ylabel("Accuracy (%)")
    ax.legend(frameon=False, fontsize=6, ncol=3, loc="upper center", labelcolor=INK2, handlelength=1.0)
    ax.set_title("(b) accuracy by question type", fontsize=7, loc="left", color=INK)
    ax = axes[2]
    style_axes(ax)
    y = np.arange(len(main))[::-1]
    ax.barh(y + 0.18, m.loc[main].p50_s, 0.34, color=BLUE, label="p50")
    ax.barh(y - 0.18, m.loc[main].p95_s, 0.34, color=ORANGE, label="p95")
    ax.set_yticks(y)
    ax.set_yticklabels(main, fontsize=6)
    ax.set_xlabel("Reader latency (s)")
    ax.legend(frameon=False, fontsize=6, labelcolor=INK2, loc="lower right")
    ax.set_title("(c) latency", fontsize=7, loc="left", color=INK)
    fig.tight_layout(w_pad=0.8)
    fig.savefig(OUT / "fig_e4_repair.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_e1()
    fig_e2()
    fig_e3()
    fig_e4()
    print("result figures written to", OUT)
