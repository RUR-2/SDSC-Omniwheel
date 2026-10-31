#!/usr/bin/env python3
"""
=============================================================
  Sim — BroneX-style Telemetry Analyser
  Source: sdsc_sim_*.csv  (exported from Sim in-browser)
  Plots:  9-panel figure saved to  Matplotlib/graph/
=============================================================
Usage
-----
  python analyse.py                        # auto-picks newest CSV in csv/
  python analyse.py csv/my_log.csv         # explicit file
  python analyse.py --all                  # batch-process every CSV in csv/
"""

import sys
import math
import argparse
from pathlib import Path
from itertools import groupby

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.patches import FancyArrowPatch

# ── Paths ────────────────────────────────────────────────────────────
HERE      = Path(__file__).parent
CSV_DIR   = HERE / "csv"
GRAPH_DIR = HERE / "graph"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

MAX_REC_HUMANS = 6

# ── Zone palette (matches sim colour scheme) ────────────────────────
ZONE_COLORS = {
    "INTIMATE": "#ef4444",
    "PERSONAL": "#f97316",
    "SOCIAL":   "#f59e0b",
    "PUBLIC":   "#22c55e",
}
ZONE_THRESHOLDS = {
    "RI": 0.45,
    "RP": 1.20,
    "RS": 3.60,
}
ZONE_INT = {"PUBLIC": 0, "SOCIAL": 1, "PERSONAL": 2, "INTIMATE": 3}

# Distinct human colours (up to 6)
HUMAN_COLORS = ["#38bdf8", "#fb923c", "#a3e635", "#e879f9", "#facc15", "#34d399"]


# ════════════════════════════════════════════════════════════════════
#  Load & pre-process
# ════════════════════════════════════════════════════════════════════
def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    df["speed"]     = np.hypot(df["robot_vx"], df["robot_vy"])
    df["f_pa_mag"]  = np.hypot(df["fx_pa"],  df["fy_pa"])
    df["f_sr_mag"]  = np.hypot(df["fx_sr"],  df["fy_sr"])
    df["f_sim_mag"] = np.hypot(df["fx_sim"], df["fy_sim"])
    df["zone_int"]  = df["zone"].map(ZONE_INT).fillna(0).astype(int)
    df["heading"]   = ((df["robot_angle_deg"] + 180) % 360) - 180

    return df


def extract_humans(df: pd.DataFrame) -> list[dict]:
    """
    Return a list of per-human dicts with:
      - all_x, all_y  : full position time-series (NaN when absent)
      - mean_x, mean_y, mean_angle_deg  : time-averaged position/heading
      - present       : bool array  (True when this human slot is active)
    Only returns entries where the human was present for at least 1 frame.
    """
    humans = []
    for i in range(1, MAX_REC_HUMANS + 1):
        xc = f"h{i}_x"
        yc = f"h{i}_y"
        ac = f"h{i}_angle_deg"
        if xc not in df.columns:
            break
        xs = pd.to_numeric(df[xc], errors="coerce").values
        ys = pd.to_numeric(df[yc], errors="coerce").values
        as_ = pd.to_numeric(df[ac], errors="coerce").values
        present = ~np.isnan(xs)
        if not present.any():
            continue
        humans.append({
            "idx":       i,
            "all_x":     xs,
            "all_y":     ys,
            "all_angle": as_,
            "present":   present,
            "mean_x":    float(np.nanmean(xs)),
            "mean_y":    float(np.nanmean(ys)),
            "mean_angle":float(np.nanmean(as_)),
            "color":     HUMAN_COLORS[(i - 1) % len(HUMAN_COLORS)],
        })
    return humans


# ════════════════════════════════════════════════════════════════════
#  Plot helpers
# ════════════════════════════════════════════════════════════════════

def _zone_ring(ax, cx, cy, r, color, lw=1.2, ls="--", alpha=0.55, label=None):
    circle = plt.Circle(
        (cx, cy), r, color=color, fill=False,
        linestyle=ls, linewidth=lw, alpha=alpha, label=label
    )
    ax.add_patch(circle)


def _zone_fill(ax, cx, cy, r, color, alpha=0.06):
    circle = plt.Circle((cx, cy), r, color=color, alpha=alpha, linewidth=0)
    ax.add_patch(circle)


def _heading_arrow(ax, cx, cy, angle_deg, length, color, lw=1.5, alpha=0.85):
    """Draw a direction arrow from (cx,cy) along angle_deg."""
    rad = math.radians(angle_deg)
    dx  = length * math.cos(rad)
    dy  = length * math.sin(rad)
    ax.annotate(
        "", xy=(cx + dx, cy + dy), xytext=(cx, cy),
        arrowprops=dict(arrowstyle="-|>", color=color,
                        lw=lw, mutation_scale=10),
        alpha=alpha,
    )


# ════════════════════════════════════════════════════════════════════
#  Individual panel renderers
# ════════════════════════════════════════════════════════════════════

# ── 1 · Trajectory + human positions + proxemic zones ───────────────
def plot_trajectory(ax, df: pd.DataFrame, humans: list[dict]):
    rx = df["robot_x"].values
    ry = df["robot_y"].values

    # ── Robot trail coloured by speed ──────────────────────────────
    pts  = np.array([rx, ry]).T.reshape(-1, 1, 2)
    segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
    spd  = df["speed"].values
    norm = Normalize(vmin=0, vmax=max(spd.max(), 0.01))
    lc   = LineCollection(segs, cmap="cool", norm=norm, linewidth=2, alpha=0.85, zorder=3)
    lc.set_array(spd[:-1])
    ax.add_collection(lc)
    cb = plt.colorbar(lc, ax=ax, label="Robot speed (m/s)", shrink=0.65, pad=0.02)
    cb.ax.yaxis.label.set_color("#8090aa")
    cb.ax.tick_params(colors="#8090aa", labelsize=7)

    # ── Human positions + proxemic zones ───────────────────────────
    ri = ZONE_THRESHOLDS["RI"]
    rp = ZONE_THRESHOLDS["RP"]
    rs = ZONE_THRESHOLDS["RS"]

    for h in humans:
        cx, cy   = h["mean_x"], h["mean_y"]
        col      = h["color"]
        idx      = h["idx"]

        # Filled zone areas (faintest = social, darkest fill = intimate)
        _zone_fill(ax, cx, cy, rs, ZONE_COLORS["SOCIAL"],   alpha=0.05)
        _zone_fill(ax, cx, cy, rp, ZONE_COLORS["PERSONAL"], alpha=0.08)
        _zone_fill(ax, cx, cy, ri, ZONE_COLORS["INTIMATE"], alpha=0.13)

        # Zone boundary rings
        _zone_ring(ax, cx, cy, rs, ZONE_COLORS["SOCIAL"],
                   lw=1.0, ls=(0, (6, 4)), alpha=0.45,
                   label=f"H{idx} Social ({rs} m)" if idx == 1 else None)
        _zone_ring(ax, cx, cy, rp, ZONE_COLORS["PERSONAL"],
                   lw=1.2, ls=(0, (4, 3)), alpha=0.60,
                   label=f"H{idx} Personal ({rp} m)" if idx == 1 else None)
        _zone_ring(ax, cx, cy, ri, ZONE_COLORS["INTIMATE"],
                   lw=1.5, ls="-", alpha=0.75,
                   label=f"H{idx} Intimate ({ri} m)" if idx == 1 else None)

        # Human trail (if they moved)
        xs_valid = h["all_x"][h["present"]]
        ys_valid = h["all_y"][h["present"]]
        x_range  = xs_valid.max() - xs_valid.min()
        y_range  = ys_valid.max() - ys_valid.min()
        if x_range > 0.05 or y_range > 0.05:   # only draw if they actually moved
            ax.plot(xs_valid, ys_valid, color=col, lw=0.8,
                    alpha=0.3, zorder=2, linestyle=":")

        # Human mean-position marker — person silhouette style
        ax.plot(cx, cy, "o", color=col, ms=11, zorder=6,
                markeredgecolor="white", markeredgewidth=1.2)
        ax.plot(cx, cy, "o", color=col, ms=6, zorder=7, alpha=0.9)

        # Heading arrow
        _heading_arrow(ax, cx, cy, h["mean_angle"], length=0.55,
                       color=col, lw=1.8, alpha=0.9)

        # Label
        ax.text(cx + 0.12, cy + 0.18, f"H{idx}",
                fontsize=7.5, color=col, fontweight="bold", zorder=8,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="#111620",
                          edgecolor=col, alpha=0.75, linewidth=0.8))

    # ── Robot start / end ──────────────────────────────────────────
    ax.plot(rx[0],  ry[0],  "o", color="#22c55e", ms=9, zorder=9,
            markeredgecolor="white", markeredgewidth=1, label="Robot Start")
    ax.plot(rx[-1], ry[-1], "s", color="#ef4444", ms=9, zorder=9,
            markeredgecolor="white", markeredgewidth=1, label="Robot End")

    # ── Legend ─────────────────────────────────────────────────────
    # Build compact legend entries
    legend_handles = [
        mpatches.Patch(color=ZONE_COLORS["SOCIAL"],   alpha=0.7, label=f"Social  ({rs} m)"),
        mpatches.Patch(color=ZONE_COLORS["PERSONAL"], alpha=0.7, label=f"Personal ({rp} m)"),
        mpatches.Patch(color=ZONE_COLORS["INTIMATE"], alpha=0.7, label=f"Intimate ({ri} m)"),
    ]
    for h in humans:
        legend_handles.append(
            mpatches.Patch(color=h["color"], alpha=0.9, label=f"H{h['idx']} ({h['mean_x']:.1f},{h['mean_y']:.1f})")
        )

    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.set_aspect("equal")
    ax.set_xlabel("X (m)"); ax.set_ylabel("Y (m)")
    ax.set_title("(1) Trajectory + Human Positions + Proxemic Zones")
    ax.legend(handles=legend_handles, fontsize=6.5, loc="upper right",
              framealpha=0.75, edgecolor="#263450")
    ax.grid(alpha=0.2)

    if not humans:
        ax.text(5, 5, "No human data\n(record with Sim v2+)",
                ha="center", va="center", fontsize=9, color="#4a5a78",
                style="italic")


# ── 2 · Distance vs Time ────────────────────────────────────────────
def plot_distance(ax, df: pd.DataFrame):
    t = df["time_s"].values
    d = np.where(df["closest_dist_m"].values < 0, np.nan, df["closest_dist_m"].values)

    ax.plot(t, d, color="#e8edf5", lw=2, label="Robot-Human Distance")

    ax.axhspan(0,                          ZONE_THRESHOLDS["RI"],
               alpha=0.18, color=ZONE_COLORS["INTIMATE"], label=f"Intimate <{ZONE_THRESHOLDS['RI']} m")
    ax.axhspan(ZONE_THRESHOLDS["RI"],      ZONE_THRESHOLDS["RP"],
               alpha=0.12, color=ZONE_COLORS["PERSONAL"], label=f"Personal <{ZONE_THRESHOLDS['RP']} m")
    ax.axhspan(ZONE_THRESHOLDS["RP"],      ZONE_THRESHOLDS["RS"],
               alpha=0.07, color=ZONE_COLORS["SOCIAL"],   label=f"Social <{ZONE_THRESHOLDS['RS']} m")

    valid = d[~np.isnan(d)]
    if valid.size:
        min_d = valid.min()
        min_t = t[np.nanargmin(d)]
        ax.annotate(f"min {min_d:.3f} m\nt={min_t:.1f}s",
                    xy=(min_t, min_d), xytext=(min_t + max(t[-1]*0.05,0.5), min_d + 0.3),
                    fontsize=7, color="#ef4444",
                    arrowprops=dict(arrowstyle="->", color="#ef4444", lw=1),
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#111620",
                              edgecolor="#ef4444", alpha=0.8))

    ax.set_xlim(t[0], t[-1]); ax.set_ylim(bottom=0)
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Distance (m)")
    ax.set_title("(2) Distance vs Time")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.25)


# ── 3 · Robot Velocity ──────────────────────────────────────────────
def plot_velocity(ax, df: pd.DataFrame):
    t = df["time_s"].values
    ax.plot(t, df["robot_vx"],  color="#06b6d4", lw=1.5, label="Vx")
    ax.plot(t, df["robot_vy"],  color="#a855f7", lw=1.5, label="Vy")
    ax.plot(t, df["speed"],     color="#e8edf5", lw=2,   label="|V|")
    ax.axhline(0, color="#4a5a78", lw=0.8, linestyle="--")
    ax.set_xlim(t[0], t[-1])
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Velocity (m/s)")
    ax.set_title("(3) Robot Velocity")
    ax.legend(fontsize=7); ax.grid(alpha=0.25)


# ── 4 · Zone Timeline ───────────────────────────────────────────────
def plot_zone_timeline(ax, df: pd.DataFrame):
    t     = df["time_s"].values
    zones = df["zone"].values
    z_int = df["zone_int"].values

    for zone_val, group in groupby(zip(t, zones), key=lambda x: x[1]):
        grp = list(group)
        ax.axvspan(grp[0][0], grp[-1][0], alpha=0.35,
                   color=ZONE_COLORS.get(zone_val, "#888"), linewidth=0)

    ax.step(t, z_int, where="post", color="white", lw=1.5, alpha=0.9)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["PUBLIC", "SOCIAL", "PERSONAL", "INTIMATE"], fontsize=7)
    ax.set_xlim(t[0], t[-1]); ax.set_ylim(-0.3, 3.5)
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Proxemic Zone")
    ax.set_title("(4) Zone Timeline"); ax.grid(alpha=0.2)
    patches = [mpatches.Patch(color=c, alpha=0.6, label=z)
               for z, c in ZONE_COLORS.items()]
    ax.legend(handles=patches, fontsize=7, loc="upper right")


# ── 5 · SFM Force Components ────────────────────────────────────────
def plot_forces(ax, df: pd.DataFrame):
    t = df["time_s"].values
    ax.plot(t, df["f_pa_mag"],  color="#ec4899", lw=1.5, label="F_pa (avoid)")
    ax.plot(t, df["f_sr_mag"],  color="#a855f7", lw=1.5, label="F_sr (social)")
    ax.plot(t, df["f_sim_mag"], color="#06b6d4", lw=2,   label="f_SIM (total)")
    ax.set_xlim(t[0], t[-1]); ax.set_ylim(bottom=0)
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Force Magnitude (N)")
    ax.set_title("(5) SFM Force Components")
    ax.legend(fontsize=7); ax.grid(alpha=0.25)


# ── 6 · Force X/Y Decomposition ─────────────────────────────────────
def plot_force_xy(ax, df: pd.DataFrame):
    t = df["time_s"].values
    ax.plot(t, df["fx_sim"], color="#06b6d4", lw=1.5, ls="-",  label="fx_SIM")
    ax.plot(t, df["fy_sim"], color="#3b82f6", lw=1.5, ls="--", label="fy_SIM")
    ax.plot(t, df["fx_pa"],  color="#ec4899", lw=1,   ls="-",  alpha=0.6, label="fx_pa")
    ax.plot(t, df["fy_pa"],  color="#f43f5e", lw=1,   ls="--", alpha=0.6, label="fy_pa")
    ax.axhline(0, color="#4a5a78", lw=0.7, linestyle=":")
    ax.set_xlim(t[0], t[-1])
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Force (N)")
    ax.set_title("(6) Force X/Y Decomposition")
    ax.legend(fontsize=7, ncol=2); ax.grid(alpha=0.25)


# ── 7 · Packet Bytes ────────────────────────────────────────────────
def plot_packets(ax, df: pd.DataFrame):
    t = df["time_s"].values
    ax.plot(t, df["pkt_X"], color="#3b82f6", lw=1.5, label="X (lateral)")
    ax.plot(t, df["pkt_Y"], color="#22c55e", lw=1.5, label="Y (forward)")
    ax.plot(t, df["pkt_W"], color="#a855f7", lw=1.5, label="W (angular)")
    ax.axhline(127, color="#4a5a78", lw=0.8, ls="--", alpha=0.7, label="Neutral (127)")
    ax.set_xlim(t[0], t[-1]); ax.set_ylim(0, 255)
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Byte value (0-255)")
    ax.set_title("(7) ESP32 Packet Output")
    ax.legend(fontsize=7); ax.grid(alpha=0.25)


# ── 8 · Robot Heading ────────────────────────────────────────────────
def plot_heading(ax, df: pd.DataFrame):
    t = df["time_s"].values
    ax.plot(t, df["heading"], color="#06b6d4", lw=1.8, label="Heading (deg)")
    ax.axhline(  0, color="#22c55e", lw=0.8, ls="--", label="East  (0 deg)")
    ax.axhline( 90, color="#a855f7", lw=0.8, ls=":",  label="North (90 deg)")
    ax.axhline(-90, color="#f97316", lw=0.8, ls=":",  label="South (-90 deg)")
    ax.set_xlim(t[0], t[-1]); ax.set_ylim(-185, 185)
    ax.set_yticks([-180, -90, 0, 90, 180])
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Heading (degrees)")
    ax.set_title("(8) Robot Heading")
    ax.legend(fontsize=7); ax.grid(alpha=0.25)


# ── 9 · Force Polar ──────────────────────────────────────────────────
def plot_force_polar(ax, df: pd.DataFrame):
    mag  = df["f_sim_mag"].values
    ang  = np.arctan2(df["fy_sim"].values, df["fx_sim"].values)
    cols = [ZONE_COLORS.get(z, "#888") for z in df["zone"].values]
    valid = mag > 0.01
    if valid.any():
        ax.scatter(ang[valid], mag[valid],
                   c=[cols[i] for i in np.where(valid)[0]],
                   s=8, alpha=0.6, linewidths=0)
    ax.set_xlim(-math.pi, math.pi)
    ax.set_xticks([-math.pi, -math.pi/2, 0, math.pi/2, math.pi])
    ax.set_xticklabels(["-pi\nW", "-pi/2\nS", "0\nE", "pi/2\nN", "pi\nW"], fontsize=7)
    ax.set_xlabel("f_SIM direction (rad)"); ax.set_ylabel("f_SIM magnitude (N)")
    ax.set_title("(9) Force Polar (f_SIM direction)")
    patches = [mpatches.Patch(color=c, alpha=0.7, label=z) for z, c in ZONE_COLORS.items()]
    ax.legend(handles=patches, fontsize=7); ax.grid(alpha=0.25)


# ════════════════════════════════════════════════════════════════════
#  Master figure composer
# ════════════════════════════════════════════════════════════════════
def make_figure(csv_path: Path):
    df     = load_csv(csv_path)
    humans = extract_humans(df)

    n_rows  = len(df)
    dur     = df["time_s"].iloc[-1]
    n_human = int(df["num_humans"].max())
    min_d_raw = df["closest_dist_m"].replace(-1, np.nan).dropna()
    min_d   = float(min_d_raw.min()) if not min_d_raw.empty else float("nan")
    src     = csv_path.name

    fig = plt.figure(figsize=(22, 14), facecolor="#0a0d14")
    fig.patch.set_facecolor("#0a0d14")

    human_info = ", ".join(
        f"H{h['idx']}=({h['mean_x']:.1f},{h['mean_y']:.1f})"
        for h in humans
    ) or "none"

    fig.suptitle(
        f"Sim - Social-DSC Analysis\n"
        f"Source: {src}   |   Duration: {dur:.1f}s   |   {n_rows:,} pts   |   "
        f"max humans: {n_human}   |   min dist: {min_d:.3f} m   |   humans: {human_info}",
        fontsize=10, fontweight="bold", color="#e8edf5", y=0.995
    )

    gs   = gridspec.GridSpec(3, 3, figure=fig, hspace=0.44, wspace=0.36,
                             left=0.06, right=0.97, top=0.93, bottom=0.06)
    axes = [fig.add_subplot(gs[r, c]) for r in range(3) for c in range(3)]

    for ax in axes:
        ax.set_facecolor("#111620")
        ax.tick_params(colors="#8090aa", labelsize=8)
        ax.xaxis.label.set_color("#8090aa")
        ax.yaxis.label.set_color("#8090aa")
        ax.title.set_color("#e8edf5")
        ax.title.set_fontsize(9)
        for spine in ax.spines.values():
            spine.set_edgecolor("#1e2a40")

    plot_trajectory   (axes[0], df, humans)
    plot_distance     (axes[1], df)
    plot_velocity     (axes[2], df)
    plot_zone_timeline(axes[3], df)
    plot_forces       (axes[4], df)
    plot_force_xy     (axes[5], df)
    plot_packets      (axes[6], df)
    plot_heading      (axes[7], df)
    plot_force_polar  (axes[8], df)

    stem    = csv_path.stem
    out_png = GRAPH_DIR / f"{stem}.png"
    out_pdf = GRAPH_DIR / f"{stem}.pdf"

    fig.savefig(out_png, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(out_pdf,           bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"  [PNG] -> {out_png}")
    print(f"  [PDF] -> {out_pdf}")
    plt.close(fig)
    return out_png


# ════════════════════════════════════════════════════════════════════
#  Entry point
# ════════════════════════════════════════════════════════════════════
def pick_csv(explicit):
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = CSV_DIR / p
        if not p.exists():
            sys.exit(f"ERROR: File not found: {p}")
        return [p]
    csvs = sorted(CSV_DIR.glob("*.csv"))
    if not csvs:
        sys.exit(f"ERROR: No CSV files found in {CSV_DIR}\n"
                 "   Export a recording from Sim and place it there.")
    return csvs


def main():
    parser = argparse.ArgumentParser(description="Sim - BroneX-style telemetry analyser")
    parser.add_argument("csv", nargs="?", default=None,
                        help="Path to a specific CSV (default: newest in csv/)")
    parser.add_argument("--all", action="store_true",
                        help="Process every CSV in csv/")
    args = parser.parse_args()

    plt.rcParams.update({
        "figure.facecolor":  "#0a0d14",
        "axes.facecolor":    "#111620",
        "axes.edgecolor":    "#1e2a40",
        "axes.labelcolor":   "#8090aa",
        "xtick.color":       "#8090aa",
        "ytick.color":       "#8090aa",
        "text.color":        "#e8edf5",
        "grid.color":        "#1e2a40",
        "grid.linestyle":    "--",
        "legend.facecolor":  "#161c2a",
        "legend.edgecolor":  "#1e2a40",
        "legend.labelcolor": "#e8edf5",
        "font.family":       "DejaVu Sans",
        "savefig.facecolor": "#0a0d14",
    })

    if args.all:
        csvs = pick_csv(None)
        print(f"Batch processing {len(csvs)} CSV file(s)...")
    else:
        csvs = pick_csv(args.csv)
        if len(csvs) > 1:
            csvs = [max(csvs, key=lambda p: p.stat().st_mtime)]
            print(f"Auto-selected newest: {csvs[0].name}")

    for csv_path in csvs:
        print(f"\nAnalysing: {csv_path.name}")
        df = load_csv(csv_path)
        humans = extract_humans(df)
        print(f"   Rows: {len(df):,}   Duration: {df['time_s'].iloc[-1]:.1f}s   "
              f"Max humans: {int(df['num_humans'].max())}   "
              f"Human slots with data: {len(humans)}")
        make_figure(csv_path)

    print(f"\nDone! Graphs saved to: {GRAPH_DIR}")


if __name__ == "__main__":
    main()
