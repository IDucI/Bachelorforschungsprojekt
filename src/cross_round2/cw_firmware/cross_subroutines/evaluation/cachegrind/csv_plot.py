"""
Wandelt die Cachegrind-/Memcheck-CSV in Diagramme um.

Beispiele:
  # Ein Diagramm: Metrik fuer einen Benchmark, alle Varianten
  python csv_plot.py cachegrind_results.csv --benchmark CROSS_sign --metric I_refs

  # Mehrere Metriken, logarithmische y-Achse, andere Ausgabedatei
  python csv_plot.py cachegrind_results.csv -b expand_pk -m I_refs D_refs --log -o expand_pk.png

  # Fuer jeden Benchmark ein Diagramm in einen Ordner schreiben
  python csv_plot.py cachegrind_results.csv --all -m I_refs --outdir plots

  # ALLE Benchmarks in einem Bild (empfohlen als Ueberblick)
  python csv_plot.py cachegrind_results.csv --overview -m I_refs
  python csv_plot.py cachegrind_results.csv --heatmap -m I_refs D1_misses

  # Zwei CSV-Dateien (zwei Laeufe) vergleichen
  python csv_plot.py run1.csv --compare run2.csv -b CROSS_sign -m D1_misses

Benoetigt: pandas, matplotlib  (pip install pandas matplotlib)
"""
import argparse
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")  
import matplotlib.pyplot as plt
import pandas as pd

ORDER_OPT = ["fast", "balanced", "small"]


def load(path):
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    if "Variant" in df.columns:
        v = df["Variant"].str.extract(r"^(rsdpg?)_(\d)_(fast|balanced|small)$")
        df["alg"], df["level"], df["opt"] = v[0], v[1], v[2]
    return df


def sort_variants(sub):
    """Sortiert: rsdp vor rsdpg, Level 1/3/5, fast/balanced/small."""
    sub = sub.copy()
    sub["_o"] = sub["opt"].map({o: i for i, o in enumerate(ORDER_OPT)})
    sub["_a"] = sub["alg"].map({"rsdp": 0, "rsdpg": 1})
    return sub.sort_values(["_a", "level", "_o"]).drop(columns=["_a", "_o"])


def plot_benchmark(df, benchmark, metrics, out, log=False, other=None):
    sub = sort_variants(df[df["Benchmark"] == benchmark])
    if sub.empty:
        sys.exit(f"Benchmark '{benchmark}' nicht gefunden.")
    series = []  
    for m in metrics:
        series.append((m, m, sub))
    if other is not None:
        osub = sort_variants(other[other["Benchmark"] == benchmark])
        osub = osub.set_index("Variant").reindex(sub["Variant"]).reset_index()
        for m in metrics:
            series.append((f"{m} (Datei 2)", m, osub))

    n = len(series)
    width = 0.8 / n
    x = range(len(sub))
    fig, ax = plt.subplots(figsize=(max(8, len(sub) * 0.6), 5))
    for i, (label, col, d) in enumerate(series):
        pos = [p + (i - (n - 1) / 2) * width for p in x]
        ax.bar(pos, d[col].values, width=width, label=label)
    ax.set_xticks(list(x))
    ax.set_xticklabels(sub["Variant"], rotation=60, ha="right")
    ax.set_title(benchmark)
    ax.set_ylabel(", ".join(metrics))
    if log:
        ax.set_yscale("log")
    ax.grid(axis="y", alpha=0.3)
    if n > 1:
        ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("geschrieben:", out)


def plot_overview(df, metric, out, opts=("fast", "balanced", "small"), log=True):
    """Ein Bild pro Metrik: x = Benchmark, Balken = Algorithmus+Level, eine Zeile pro Optimierung."""
    import numpy as np
    groups = [(a, l) for a in ("rsdp", "rsdpg") for l in ("1", "3", "5")]
    benches = list(df["Benchmark"].unique())
    # Gesamtoperationen zuerst, dann nach Groesse sortiert
    overall = [b for b in benches if b.startswith("CROSS_")]
    rest = [b for b in benches if b not in overall]
    rest.sort(key=lambda b: df[df["Benchmark"] == b][metric].max(skipna=True), reverse=True)
    benches = overall + rest
    colors = {("rsdp", "1"): "#9ecae1", ("rsdp", "3"): "#4292c6", ("rsdp", "5"): "#08519c",
              ("rsdpg", "1"): "#fdae6b", ("rsdpg", "3"): "#f16913", ("rsdpg", "5"): "#8c2d04"}
    fig, axes = plt.subplots(len(opts), 1, figsize=(16, 4.2 * len(opts)), sharex=True, squeeze=False)
    w = 0.8 / len(groups)
    for ax, opt in zip(axes[:, 0], opts):
        sub = df[df["opt"] == opt]
        for gi, (a, l) in enumerate(groups):
            vals = []
            for b in benches:
                r = sub[(sub["Benchmark"] == b) & (sub["alg"] == a) & (sub["level"] == l)][metric]
                vals.append(r.iloc[0] if len(r) else np.nan)
            pos = np.arange(len(benches)) + (gi - (len(groups) - 1) / 2) * w
            ax.bar(pos, vals, width=w, color=colors[(a, l)], label=f"{a} L{l}")
        if log:
            ax.set_yscale("log")
        ax.set_title(f"{metric} - Variante: {opt}", loc="left", fontsize=10)
        ax.grid(axis="y", alpha=0.3)
        ax.axvline(len(overall) - 0.5, color="gray", ls="--", lw=0.8)  
    axes[0, 0].legend(ncol=6, fontsize=8, loc="upper right")
    axes[-1, 0].set_xticks(range(len(benches)))
    axes[-1, 0].set_xticklabels(benches, rotation=60, ha="right")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("geschrieben:", out)


def plot_heatmap(df, metric, out):
    """Heatmap: Zeilen = Benchmark, Spalten = Variante, Farbe = log10(Wert)."""
    import numpy as np
    pt = df.pivot_table(index="Benchmark", columns="Variant", values=metric, aggfunc="first")
    cols = [f"{a}_{l}_{o}" for a in ("rsdp", "rsdpg") for l in "135" for o in ORDER_OPT]
    pt = pt.reindex(columns=[c for c in cols if c in pt.columns])
    pt = pt.loc[pt.max(axis=1).sort_values(ascending=False).index]
    data = np.log10(pt.values.astype(float))
    fig, ax = plt.subplots(figsize=(14, 0.5 * len(pt) + 3))
    im = ax.imshow(data, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(pt.columns)))
    ax.set_xticklabels(pt.columns, rotation=75, ha="right", fontsize=8)
    ax.set_yticks(range(len(pt.index)))
    ax.set_yticklabels(pt.index, fontsize=9)
    fig.colorbar(im, label=f"log10({metric})")
    ax.set_title(metric)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print("geschrieben:", out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv")
    p.add_argument("-b", "--benchmark", help="Name des Benchmarks (Spalte Benchmark)")
    p.add_argument("-m", "--metric", nargs="+", default=["I_refs"], help="eine oder mehrere Spalten")
    p.add_argument("--all", action="store_true", help="fuer jeden Benchmark ein Diagramm")
    p.add_argument("--compare", help="zweite CSV zum direkten Vergleich")
    p.add_argument("--overview", action="store_true", help="ALLE Benchmarks in einem Bild (pro Metrik, je Optimierungsvariante eine Zeile)")
    p.add_argument("--heatmap", action="store_true", help="Heatmap Benchmark x Variante (pro Metrik)")
    p.add_argument("--opt", nargs="+", choices=ORDER_OPT, default=ORDER_OPT, help="bei --overview: welche Optimierungen zeigen")
    p.add_argument("--log", action="store_true", help="logarithmische y-Achse")
    p.add_argument("-o", "--out", help="Ausgabedatei (PNG/PDF/SVG)")
    p.add_argument("--outdir", default="plots", help="Ordner fuer --all")
    a = p.parse_args()

    df = load(a.csv)
    other = load(a.compare) if a.compare else None
    for m in a.metric:
        if m not in df.columns:
            sys.exit(f"Spalte '{m}' nicht vorhanden. Verfuegbar: {', '.join(df.columns)}")

    if a.overview or a.heatmap:
        for m in a.metric:
            if a.overview:
                plot_overview(df, m, a.out or f"overview_{m}.png", tuple(a.opt), log=True)
            if a.heatmap:
                plot_heatmap(df, m, f"heatmap_{m}.png")
        return

    if a.all:
        os.makedirs(a.outdir, exist_ok=True)
        for b in df["Benchmark"].unique():
            name = re.sub(r"\W+", "_", b)
            plot_benchmark(df, b, a.metric, os.path.join(a.outdir, f"{name}_{'_'.join(a.metric)}.png"), a.log, other)
    else:
        if not a.benchmark:
            sys.exit("Bitte --benchmark angeben oder --all verwenden. Benchmarks: " + ", ".join(df["Benchmark"].unique()))
        out = a.out or f"{a.benchmark}_{'_'.join(a.metric)}.png"
        plot_benchmark(df, a.benchmark, a.metric, out, a.log, other)


if __name__ == "__main__":
    main()