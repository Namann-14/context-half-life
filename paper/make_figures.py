"""Generate the figures embedded in Context_Rot_Research_Final.docx.

fig_evidence         reported degradation numbers from the cited studies.
fig_niah_position    needle-in-a-haystack setup and the lost-in-the-middle shape.
fig_dilution         attention dilution under softmax as the context grows.
fig_survival         schematic survival curves S(a) for three segment types.
fig_session          simulated session: live vs. decayed tokens and the Rot Index.
fig_pipeline         the half-life-guided repair loop (diagram).
fig_before_after     the worked repair example, before and after.

Only fig_evidence shows numbers from the literature (as reported by each study).
Every other curve is computed from the formulas in the paper or is a schematic;
none of it is measured data. Run from the repository root:
    python paper/make_figures.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

# Reference palette (first three categorical slots validate all-pairs) and ink.
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
BLUE_TINT = "#cde2fb"

plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 7.5,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.titlesize": 8,
    "savefig.dpi": 400,
})


def style_axes(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, labelcolor=INK2)


def fig_pipeline():
    steps = [
        ("1  Segment", "split into\nmessages, tool\noutputs, memory"),
        ("2  Detect", "stale · conflict\nduplicate ·\noff-topic"),
        ("3  Estimate", "survival S(a)\nRot Index R(t)\nhalf-life H(C)"),
        ("4  Trigger?", "R(t) > R*\nor t > H(C)\n(or token cap)"),
        ("5  Plan", "update · merge\nremove · keep\n(skip protected)"),
        ("6  Verify", "probe old vs.\nnew context;\nroll back fails"),
        ("7  Commit", "send to LLM;\narchive removed;\nlog metrics"),
    ]
    fig, ax = plt.subplots(figsize=(7.0, 1.45))
    ax.set_xlim(0, 7.0)
    ax.set_ylim(0.1, 1.55)
    ax.axis("off")
    w, h, gap, y0 = 0.9, 0.95, 0.08, 0.5
    x = 0.07
    centers = []
    for i, (title, body) in enumerate(steps):
        face = BLUE_TINT if i in (2, 4) else "#f0efec"
        ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0.0,rounding_size=0.06",
                                    facecolor=face, edgecolor=AXIS, linewidth=0.8))
        ax.text(x + w / 2, y0 + h - 0.16, title, ha="center", va="center",
                fontsize=7.6, fontweight="bold", color=INK)
        ax.text(x + w / 2, y0 + h / 2 - 0.12, body, ha="center", va="center",
                fontsize=6.1, color=INK2, linespacing=1.3)
        centers.append(x + w / 2)
        if i < len(steps) - 1:
            ax.add_patch(FancyArrowPatch((x + w, y0 + h / 2), (x + w + gap, y0 + h / 2),
                                         arrowstyle="-|>", mutation_scale=7, color=INK2, linewidth=0.9,
                                         shrinkA=0, shrinkB=0))
        x += w + gap
    # Loop-back path: the cycle repeats every turn.
    ly = 0.26
    ax.plot([centers[-1], centers[-1], centers[0]], [y0, ly, ly], color=MUTED, linewidth=0.9,
            linestyle=(0, (3, 2)))
    ax.add_patch(FancyArrowPatch((centers[0], ly), (centers[0], y0), arrowstyle="-|>", mutation_scale=7,
                                 color=MUTED, linewidth=0.9, shrinkA=0, shrinkB=0))
    ax.text(3.5, ly, "  next turn: repeat (if nothing triggers, step 7 sends the context unchanged)  ",
            ha="center", va="center", fontsize=6.4, color=INK2, style="italic",
            bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
    fig.savefig(OUT / "fig_repair_loop.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)


def fig_survival():
    a = np.linspace(0, 100, 501)
    curves = [
        ("Tool output (volatile)", np.exp(-(a / 6.0) ** 2.0), 6.0 * np.log(2) ** (1 / 2.0), BLUE),
        ("Chat message (constant rate)", np.exp(-np.log(2) / 20.0 * a), 20.0, ORANGE),
        ("User preference (durable)", np.exp(-(a / 120.0) ** 0.7), 120.0 * np.log(2) ** (1 / 0.7), AQUA),
    ]
    fig, ax = plt.subplots(figsize=(3.3, 2.25))
    style_axes(ax)
    ax.axhline(0.5, color=MUTED, linewidth=0.8, linestyle=(0, (3, 2)))
    ax.text(99, 0.52, "S(a) = 0.5", ha="right", va="bottom", fontsize=6.5, color=INK2)
    for label, s, half, color in curves:
        ax.plot(a, s, color=color, linewidth=1.6, label=label)
        ax.plot([half], [0.5], "o", markersize=4.5, color=color, markeredgecolor="white", markeredgewidth=1)
        ax.annotate(f"H ≈ {half:.0f}", (half, 0.5), xytext=(3, -11), textcoords="offset points",
                    fontsize=6.5, color=INK2)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1.04)
    ax.set_xlabel("Age of segment a (turns since it was written)")
    ax.set_ylabel("Probability still useful, S(a)")
    ax.legend(frameon=False, fontsize=6.4, loc="upper right", bbox_to_anchor=(1.0, 1.0),
              labelcolor=INK2, handlelength=1.6)
    fig.savefig(OUT / "fig_survival.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)


def fig_dilution():
    n = np.logspace(0, 5, 400)
    fig, ax = plt.subplots(figsize=(3.3, 2.2))
    style_axes(ax)
    for s, color in [(0, BLUE), (2, ORANGE), (4, AQUA)]:
        share = np.exp(s) / (np.exp(s) + n - 1)
        ax.plot(n, 100 * share, color=color, linewidth=1.6, label=f"relevance boost s = {s}")
    ax.set_xscale("log")
    ax.set_xlim(1, 1e5)
    ax.set_ylim(0, 102)
    ax.set_xticks([1, 10, 100, 1_000, 10_000, 100_000])
    ax.set_xticklabels(["1", "10", "100", "1K", "10K", "100K"])
    ax.set_xlabel("Number of competing tokens n (log scale)")
    ax.set_ylabel("Attention share on the key token (%)")
    ax.legend(frameon=False, fontsize=6.4, loc="upper right", labelcolor=INK2, handlelength=1.6)
    fig.savefig(OUT / "fig_dilution.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)


def fig_evidence():
    """Degradation numbers exactly as reported by the cited papers (definitions differ)."""
    rows = [
        ("Multi-turn vs. single-turn\n15 LLMs, 6 tasks (Laban et al.)", 39, None, "−39% average"),
        ("Long chat-history recall\nLongMemEval (Wu et al.)", 30, None, "≈ −30%"),
        ("No word overlap, 32K tokens\nGPT-4o on NoLiMa (Modarressi et al.)", 100 * (99.3 - 69.7) / 99.3, None,
         "99.3% → 69.7%"),
        ("Length alone, perfect retrieval\n5 models (Du et al.)", 85, 13.9, "−13.9% to −85%"),
    ]
    fig, ax = plt.subplots(figsize=(3.3, 2.05))
    style_axes(ax)
    ax.grid(axis="y", visible=False)
    ys = np.arange(len(rows))[::-1]
    for y, (label, hi, lo, note) in zip(ys, rows):
        if lo is None:
            ax.barh(y, hi, height=0.5, color=BLUE)
        else:
            ax.barh(y, hi - lo, left=lo, height=0.5, color=BLUE, alpha=0.45)
            ax.plot([lo, lo], [y - 0.25, y + 0.25], color=BLUE, linewidth=1.5)
            ax.plot([hi, hi], [y - 0.25, y + 0.25], color=BLUE, linewidth=1.5)
        ax.text(hi + 2, y, note, va="center", fontsize=6.6, color=INK2)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=6.4)
    ax.set_xlim(0, 112)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Reported performance drop (%)")
    fig.savefig(OUT / "fig_evidence.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)


def fig_niah_position():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.3, 2.75), gridspec_kw={"height_ratios": [1, 1.45]})
    # (a) Needle-in-a-haystack setup.
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 3)
    ax1.axis("off")
    ax1.add_patch(FancyBboxPatch((0.1, 1.0), 7.3, 0.9, boxstyle="round,pad=0,rounding_size=0.1",
                                 facecolor="#f0efec", edgecolor=AXIS, linewidth=0.8))
    ax1.text(1.6, 1.45, "filler text (haystack)", ha="center", va="center", fontsize=6.6, color=INK2)
    ax1.text(5.9, 1.45, "… L tokens", ha="center", va="center", fontsize=6.6, color=INK2)
    ax1.add_patch(FancyBboxPatch((3.55, 1.0), 0.45, 0.9, boxstyle="square,pad=0", facecolor=ORANGE,
                                 edgecolor="none"))
    ax1.text(3.78, 2.35, "needle: “The secret ingredient is cardamom.”", ha="center", va="center",
             fontsize=6.4, color=INK)
    ax1.annotate("", (3.78, 1.95), (3.78, 2.2), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=0.8))
    ax1.annotate("", (0.1, 0.65), (3.78, 0.65), arrowprops=dict(arrowstyle="<->", color=MUTED, lw=0.8))
    ax1.text(1.95, 0.3, "depth d (0% = start)", ha="center", va="center", fontsize=6.3, color=INK2)
    ax1.add_patch(FancyBboxPatch((7.6, 1.0), 2.3, 0.9, boxstyle="round,pad=0,rounding_size=0.1",
                                 facecolor=BLUE_TINT, edgecolor=AXIS, linewidth=0.8))
    ax1.text(8.75, 1.45, "Q: What is the\nsecret ingredient?", ha="center", va="center", fontsize=6.2,
             color=INK)
    ax1.text(0.0, 2.85, "(a)", fontsize=7, fontweight="bold", color=INK, va="top")
    # (b) Schematic lost-in-the-middle shape (no data: shape only).
    x = np.linspace(0, 1, 200)
    y = 0.52 + 0.36 * (2 * x - 1) ** 2 + 0.05 * (1 - x)
    style_axes(ax2)
    ax2.plot(x, y, color=BLUE, linewidth=1.8)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0.4, 1.0)
    ax2.set_xticks([0, 0.5, 1])
    ax2.set_xticklabels(["start", "middle", "end"])
    ax2.set_yticks([])
    ax2.set_xlabel("Position of the relevant information in the context")
    ax2.set_ylabel("Accuracy (schematic)")
    ax2.annotate("primacy", (0.03, 0.9), xytext=(0.12, 0.93), fontsize=6.5, color=INK2)
    ax2.annotate("recency", (0.97, 0.86), xytext=(0.74, 0.9), fontsize=6.5, color=INK2)
    ax2.annotate("lost in the middle", (0.5, 0.545), xytext=(0.5, 0.65), ha="center", fontsize=6.5,
                 color=INK2, arrowprops=dict(arrowstyle="-|>", color=INK2, lw=0.7))
    ax2.text(-0.02, 1.07, "(b)", transform=ax2.transAxes, fontsize=7, fontweight="bold", color=INK)
    fig.tight_layout(h_pad=0.4)
    fig.savefig(OUT / "fig_niah_position.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)


def session_curves(turns=100):
    """Expected live and total tokens for a simulated chat that uses the Fig. survival curves."""
    segs = [(0, 300, "system")]
    for b in range(1, turns + 1):
        segs += [(b, 60, "chat"), (b, 150, "chat")]
        if b % 2 == 0:
            segs.append((b, 600, "tool"))
        if b % 15 == 1:
            segs.append((b, 30, "pref"))

    def surv(kind, a):
        if kind == "system":
            return 1.0
        if kind == "chat":
            return 0.5 ** (a / 20.0)
        if kind == "tool":
            return np.exp(-(a / 6.0) ** 2.0)
        return np.exp(-(a / 120.0) ** 0.7)

    t = np.arange(0, turns + 1)
    total = np.array([sum(l for b, l, _ in segs if b <= tt) for tt in t], dtype=float)
    live = np.array([sum(l * surv(k, tt - b) for b, l, k in segs if b <= tt) for tt in t])
    return t, total, live


def fig_session():
    t, total, live = session_curves()
    rot = 1 - live / total
    half = int(t[np.argmax(rot >= 0.5)])
    trigger = int(t[np.argmax(rot >= 0.4)])
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.3, 2.75), sharex=True,
                                   gridspec_kw={"height_ratios": [1.15, 1]})
    style_axes(ax1)
    ax1.fill_between(t, 0, live / 1000, color=BLUE, linewidth=0, label="live (still useful)")
    ax1.fill_between(t, live / 1000, total / 1000, color=ORANGE, alpha=0.55, linewidth=0,
                     label="decayed (dead weight)")
    ax1.set_ylabel("Tokens (thousands)")
    ax1.set_ylim(0, 55)
    ax1.legend(frameon=False, fontsize=6.3, loc="upper left", labelcolor=INK2)
    style_axes(ax2)
    ax2.plot(t, rot, color=ORANGE, linewidth=1.6)
    ax2.axhline(0.4, color=MUTED, linewidth=0.8, linestyle=(0, (3, 2)))
    ax2.text(99, 0.36, "repair threshold R* = 0.4", ha="right", va="top", fontsize=6.3, color=INK2)
    ax2.plot([half], [0.5], "o", color=ORANGE, markersize=4.5, markeredgecolor="white", markeredgewidth=1)
    ax2.annotate(f"session half-life H(C) ≈ turn {half}", (half, 0.5), xytext=(half + 12, 0.44),
                 fontsize=6.3, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    ax2.annotate(f"trigger fires ≈ turn {trigger}", (trigger, 0.4), xytext=(trigger + 14, 0.2),
                 fontsize=6.3, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    ax2.set_ylim(0, 1)
    ax2.set_xlim(0, 100)
    ax2.set_ylabel("Rot Index R(t)")
    ax2.set_xlabel("Turn t")
    fig.tight_layout(h_pad=0.3)
    fig.savefig(OUT / "fig_session.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)
    return half, trigger


def fig_before_after():
    kinds = {"keep": (BLUE, "protected"), "stale": (ORANGE, "stale"), "dup": (AQUA, "redundant"),
             "conflict": (YELLOW, "contradictory"), "noise": (MAGENTA, "irrelevant")}
    rows = [
        ("System prompt", 300, "keep", "KEEP", "System prompt", 300),
        ("Exam: 12 Mar (t4)", 20, "stale", "UPDATE", "Exam: 19 Mar (+log)", 30),
        ("Allergy: peanuts", 15, "keep", "KEEP", "Allergy: peanuts", 15),
        ("Formulas ×3", 1050, "dup", "MERGE", "Formulas ×1", 350),
        ("“Six units” (t15)", 40, "conflict", "RESOLVE", "Syllabus: 5 units", 50),
        ("Error log (t20)", 3000, "noise", "REMOVE", "archived, recallable", None),
        ("Turns t55–60", 1200, "keep", "KEEP", "Turns t55–60", 1200),
    ]
    fig, ax = plt.subplots(figsize=(3.3, 2.6))
    ax.set_xlim(0, 3.3)
    ax.set_ylim(-0.1, 2.5)
    ax.axis("off")
    bw, bh, gap = 1.3, 0.24, 0.07
    lx, rx = 0.0, 2.0
    top = 2.2
    before = sum(r[1] for r in rows)
    after = sum(r[5] for r in rows if r[5])
    ax.text(lx + bw / 2, 2.43, f"Before: {before:,} tokens", ha="center", fontsize=7, fontweight="bold",
            color=INK)
    ax.text(rx + bw / 2, 2.43, f"After: {after:,} tokens", ha="center", fontsize=7, fontweight="bold",
            color=INK)
    for i, (left, ltok, kind, op, right, rtok) in enumerate(rows):
        y = top - i * (bh + gap) - bh
        color, _ = kinds[kind]
        ax.add_patch(FancyBboxPatch((lx, y), bw, bh, boxstyle="round,pad=0,rounding_size=0.03",
                                    facecolor=color, alpha=0.22, edgecolor=color, linewidth=0.9))
        ax.text(lx + 0.05, y + bh / 2, left, va="center", fontsize=6.0, color=INK)
        ax.text(lx + bw - 0.04, y + bh / 2, f"{ltok:,}", va="center", ha="right", fontsize=5.8, color=INK2)
        ax.annotate("", (rx - 0.03, y + bh / 2), (lx + bw + 0.03, y + bh / 2),
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=0.7, shrinkA=0, shrinkB=0))
        ax.text((lx + bw + rx) / 2, y + bh / 2 + 0.07, op, ha="center", va="bottom", fontsize=5.6,
                fontweight="bold", color=INK2)
        if rtok is None:
            ax.add_patch(FancyBboxPatch((rx, y), bw, bh, boxstyle="round,pad=0,rounding_size=0.03",
                                        facecolor="white", edgecolor=MUTED, linewidth=0.8, linestyle=(0, (2, 2))))
            ax.text(rx + 0.05, y + bh / 2, right, va="center", fontsize=6.0, color=INK2, style="italic")
        else:
            out_color = BLUE if kind == "keep" else color
            ax.add_patch(FancyBboxPatch((rx, y), bw, bh, boxstyle="round,pad=0,rounding_size=0.03",
                                        facecolor=out_color, alpha=0.22, edgecolor=out_color, linewidth=0.9))
            ax.text(rx + 0.05, y + bh / 2, right, va="center", fontsize=6.0, color=INK)
            ax.text(rx + bw - 0.04, y + bh / 2, f"{rtok:,}", va="center", ha="right", fontsize=5.8,
                    color=INK2)
    # Legend: decay-mode colours (identity is also written in the operation labels).
    x = 0.02
    for key in ("keep", "stale", "dup", "conflict", "noise"):
        color, name = kinds[key]
        ax.add_patch(FancyBboxPatch((x, -0.08), 0.09, 0.09, boxstyle="square,pad=0", facecolor=color,
                                    alpha=0.6, edgecolor=color, linewidth=0.6))
        ax.text(x + 0.12, -0.035, name, va="center", fontsize=5.8, color=INK2)
        x += 0.13 + 0.052 * len(name)
    fig.savefig(OUT / "fig_before_after.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)
    return before, after


if __name__ == "__main__":
    fig_evidence()
    fig_niah_position()
    fig_dilution()
    fig_survival()
    print("session half-life and trigger turns:", fig_session())
    fig_pipeline()
    print("worked example tokens before/after:", fig_before_after())
    print("figures written to", OUT)
