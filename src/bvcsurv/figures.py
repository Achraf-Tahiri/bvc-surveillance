"""Figures de l'étude d'événements (PNG pour le README).

Usage : python -m bvcsurv.figures   # results/etude/*.csv et ar.npy -> results/etude/*.png
"""
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .etude import EV, OUT, SEED, boot_ci  # noqa: E402

SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"
DAYS = np.arange(EV[0], EV[1] + 1)


def style(ax, title: str, ylabel: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", color=INK, fontsize=12, pad=12)
    ax.set_ylabel(ylabel, color=INK2, fontsize=9)
    ax.tick_params(colors=MUTED, labelsize=8.5, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)


def label_end(ax, x, y, text, color) -> None:
    ax.annotate(text, (x, y), xytext=(6, 0), textcoords="offset points", va="center",
                fontsize=8.5, color=INK2)
    ax.plot([x], [y], "o", ms=5, color=color, mec=SURFACE, mew=1.5, zorder=4)


def variance_profile(df: pd.DataFrame, ars: np.ndarray) -> None:
    liq = (df.liquid & df.isolated).to_numpy()
    z2 = ars ** 2 / df["sigma"].to_numpy()[:, None] ** 2
    fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=SURFACE)
    series = [("resultats", "Résultats", BLUE, "-"), ("indicateurs_trimestriels", "Indicateurs trimestriels", ORANGE, "-"),
              ("placebo", "Dates sans publication", MUTED, "--")]
    for key, name, color, ls in series:
        m = liq & (df.event_type == key).to_numpy()
        y = z2[m].mean(0)
        ax.plot(DAYS, y, color=color, lw=2, ls=ls, label=f"{name} (n = {m.sum()})")
        label_end(ax, DAYS[-1], y[-1], name.split()[0], color)
    ax.axvspan(-0.5, 1.5, color=GRID, alpha=0.5, lw=0)
    ax.set_xticks(DAYS[::2])
    ax.set_xlim(DAYS[0] - 0.5, DAYS[-1] + 3)
    ax.set_xlabel("Séances autour de la publication (0 = jour de réaction)", color=INK2, fontsize=9)
    style(ax, "Intensité de la réaction : variance anormale moyenne par séance",
          "AR² / σ² (1 = séance ordinaire)")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2, loc="upper left")
    fig.text(0.01, 0.01, "Valeurs liquides, événements isolés (aucune autre publication de la valeur à ±10 séances). "
             "Bande grise : fenêtre [0, +1].", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "profil_variance.png", dpi=150)
    plt.close(fig)


def warning_path(df: pd.DataFrame, ars: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=SURFACE)
    for key, name, color, ls in [("profit_warning", "Profit warnings", BLUE, "-"),
                                 ("placebo", "Dates sans publication", MUTED, "--")]:
        m = (df.liquid & (df.event_type == key)).to_numpy()
        car = np.cumsum(ars[m], axis=1) * 100
        y = car.mean(0)
        if key == "profit_warning":
            cl = df.loc[m, "day0"].astype(str).to_numpy()
            ci = np.array([boot_ci(car[:, j], cl, seed=SEED + j) for j in range(car.shape[1])])
            ax.fill_between(DAYS, ci[:, 0], ci[:, 1], color=color, alpha=0.15, lw=0,
                            label="Intervalle de confiance à 95 % (bootstrap)")
        ax.plot(DAYS, y, color=color, lw=2, ls=ls, label=f"{name} (n = {m.sum()})")
        label_end(ax, DAYS[-1], y[-1], f"{y[-1]:+.1f} %".replace(".", ","), color)
    ax.axhline(0, color=AXIS, lw=0.8)
    ax.axvline(-0.5, color=AXIS, lw=0.8, ls=":")
    ax.set_xticks(DAYS[::2])
    ax.set_xlim(DAYS[0] - 0.5, DAYS[-1] + 3)
    ax.set_xlabel("Séances autour de la publication (0 = jour de réaction)", color=INK2, fontsize=9)
    style(ax, "Rendement anormal cumulé autour des profit warnings", "CAR depuis la séance -10 (%)")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2, loc="lower left")
    fig.text(0.01, 0.01, "Valeurs liquides. Modèle de marché sur le MASI estimé sur [-250, -30].",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "profit_warnings.png", dpi=150)
    plt.close(fig)


NAMES = {"resultats": "Résultats", "profit_warning": "Profit warnings",
         "indicateurs_trimestriels": "Indicateurs trimestriels", "assemblee_generale": "Assemblées générales",
         "operation_financiere": "Opérations financières", "dette": "Dette", "gouvernance": "Gouvernance",
         "autre": "Autres"}


def variance_by_type() -> None:
    t = pd.read_csv(OUT / "par_type_liquides.csv").set_index("event_type")
    base = t.loc["placebo", "vr_ann"]
    t = t.drop("placebo").sort_values("vr_ann")
    fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=SURFACE)
    y = np.arange(len(t))
    ax.barh(y, t["vr_ann"], height=0.6, color=BLUE, edgecolor=SURFACE, linewidth=2)
    ax.errorbar(t["vr_ann"], y, xerr=[t["vr_ann"] - t["vr_ann_ic_bas"], t["vr_ann_ic_haut"] - t["vr_ann"]],
                fmt="none", ecolor=INK2, elinewidth=1, capsize=3)
    for yi, (v, hi) in enumerate(zip(t["vr_ann"], t["vr_ann_ic_haut"])):
        ax.text(hi + 0.12, yi, f"{v:.1f}".replace(".", ","), va="center", fontsize=8.5, color=INK)
    ax.axvline(base, color=INK2, lw=1, ls="--")
    ax.text(base, len(t) - 0.4, f" dates sans publication : {base:.2f}".replace(".", ","), fontsize=8, color=INK2)
    ax.set_yticks(y, [f"{NAMES[i]} ({int(n)})" for i, n in zip(t.index, t["n"])], color=INK2, fontsize=9)
    ax.set_xlabel("Rapport de variance sur [0, +1] (1 = séance ordinaire)", color=INK2, fontsize=9)
    style(ax, "Intensité de la réaction par type de publication", "")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    fig.text(0.01, 0.01, "Valeurs liquides, nombre d'événements entre parenthèses. "
             "Barres d'erreur : intervalle à 95 % (bootstrap en grappes de dates).",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "variance_par_type.png", dpi=150)
    plt.close(fig)


def main() -> int:
    df = pd.read_csv(OUT / "evenements.csv")
    ars = np.load(OUT / "ar.npy")
    assert len(df) == len(ars)
    variance_profile(df, ars)
    warning_path(df, ars)
    variance_by_type()
    print(f"figures écrites dans {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
