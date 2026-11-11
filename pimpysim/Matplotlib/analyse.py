#!/usr/bin/env python3
"""
=============================================================
  Sim — BroneX-style Telemetry & Scenario Analyser
  Source: sdsc_sim_*.csv / skenario_h1_diam_tengah_ab_*.csv
  Plots:  9-panel figure + summary CSV saved to Matplotlib/graph/
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
from matplotlib.patches import Wedge

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

    # Ensure backward-compatible columns for older CSV files
    if "actual_dist_m" not in df.columns:
        if "h1_x" in df.columns and df["h1_x"].notna().any():
            d_list = []
            for i in range(1, MAX_REC_HUMANS + 1):
                xc, yc = f"h{i}_x", f"h{i}_y"
                if xc in df.columns:
                    hx = pd.to_numeric(df[xc], errors="coerce")
                    hy = pd.to_numeric(df[yc], errors="coerce")
                    d_list.append(np.hypot(df["robot_x"] - hx, df["robot_y"] - hy))
            if d_list:
                df["actual_dist_m"] = np.nanmin(np.vstack(d_list), axis=0)
            else:
                df["actual_dist_m"] = df["closest_dist_m"]
        else:
            df["actual_dist_m"] = df["closest_dist_m"]

    if "lateral_dev_m" not in df.columns:
        df["lateral_dev_m"] = df["robot_y"] - 5.0

    if "fov_enabled" not in df.columns:
        df["fov_enabled"] = 0

    return df


def extract_humans(df: pd.DataFrame) -> list[dict]:
    """
    Return a list of per-human dicts with:
      - all_x, all_y  : full position time-series (NaN when absent)
      - mean_x, mean_y, mean_angle_deg  : time-averaged position/heading
      - present       : bool array  (True when this human slot is active)
      - visible       : bool array  (True when inside robot FOV)
    """
    humans = []
    for i in range(1, MAX_REC_HUMANS + 1):
        xc = f"h{i}_x"
        yc = f"h{i}_y"
        ac = f"h{i}_angle_deg"
        vc = f"h{i}_visible"
        if xc not in df.columns:
            break
        xs = pd.to_numeric(df[xc], errors="coerce").values
        ys = pd.to_numeric(df[yc], errors="coerce").values
        as_ = pd.to_numeric(df[ac], errors="coerce").values
        present = ~np.isnan(xs)
        if not present.any():
            continue
        if vc in df.columns:
            vis = pd.to_numeric(df[vc], errors="coerce").fillna(1).values > 0.5
        else:
            vis = present.copy()
        humans.append({
            "idx":        i,
            "all_x":      xs,
            "all_y":      ys,
            "all_angle":  as_,
            "present":    present,
            "visible":    vis,
            "mean_x":     float(np.nanmean(xs)),
            "mean_y":     float(np.nanmean(ys)),
            "mean_angle": float(np.nanmean(as_)),
            "color":      HUMAN_COLORS[(i - 1) % len(HUMAN_COLORS)],
        })
    return humans


def compute_summary_metrics(df: pd.DataFrame, humans: list[dict]) -> dict:
    """Compute quantitative metrics for the scenario."""
    t = df["time_s"].values
    dur = float(t[-1] - t[0]) if len(t) > 1 else 0.0
    rx, ry = df["robot_x"].values, df["robot_y"].values
    step_dists = np.hypot(np.diff(rx), np.diff(ry)) if len(rx) > 1 else np.array([0.0])
    path_len = float(np.sum(step_dists))

    act_d = pd.to_numeric(df["actual_dist_m"], errors="coerce").values
    act_d = np.where(act_d < 0, np.nan, act_d)
    valid_act = act_d[~np.isnan(act_d)]
    min_clearance = float(np.min(valid_act)) if valid_act.size else float("nan")

    det_d = pd.to_numeric(df["closest_dist_m"], errors="coerce").values
    det_d = np.where(det_d < 0, np.nan, det_d)
    valid_det = det_d[~np.isnan(det_d)]
    min_detected = float(np.min(valid_det)) if valid_det.size else float("nan")

    lat_dev = np.abs(pd.to_numeric(df["lateral_dev_m"], errors="coerce").fillna(0.0).values)
    max_lat_dev = float(np.max(lat_dev)) if lat_dev.size else 0.0

    has_patrol = "patrol_ax" in df.columns and df["patrol_ax"].notna().any()
    if has_patrol:
        ax_pt = float(df["patrol_ax"].dropna().iloc[0])
        ay_pt = float(df["patrol_ay"].dropna().iloc[0])
        bx_pt = float(df["patrol_bx"].dropna().iloc[0])
        by_pt = float(df["patrol_by"].dropna().iloc[0])
        ab_dist = math.hypot(bx_pt - ax_pt, by_pt - ay_pt)
        loops = int(pd.to_numeric(df["patrol_loop"], errors="coerce").fillna(0).max())
        # Count actual legs traversed from patrol_target transitions
        if "patrol_target" in df.columns and df["patrol_target"].notna().any():
            tgts = [k for k, _ in groupby(df["patrol_target"].fillna("").values) if k in ("A", "B")]
            # Last row may have flipped target on arrival; only count a leg if >= 10 samples spent on it
            leg_groups = [(k, sum(1 for _ in g)) for k, g in groupby(df["patrol_target"].fillna("").values) if k in ("A", "B")]
            active_legs = max(1, sum(1 for _, cnt in leg_groups if cnt >= 10))
        else:
            active_legs = max(1, loops * 2)
    else:
        ax_pt, ay_pt, bx_pt, by_pt = 1.5, 5.0, 8.5, 5.0
        ab_dist = math.hypot(rx[-1] - rx[0], ry[-1] - ry[0]) if len(rx) > 1 else 7.0
        loops = 0
        active_legs = 1

    ideal_dist = max(ab_dist * active_legs, 1e-6)
    detour_ratio = path_len / ideal_dist

    fov_on = bool(pd.to_numeric(df["fov_enabled"], errors="coerce").fillna(0).max() > 0)
    if humans:
        vis_pct = float(np.mean(humans[0]["visible"]) * 100.0)
    else:
        vis_pct = 100.0

    zones = df["zone"].values
    n_total = max(len(zones), 1)
    zone_pcts = {
        z: float(np.sum(zones == z) / n_total * 100.0)
        for z in ["PUBLIC", "SOCIAL", "PERSONAL", "INTIMATE"]
    }

    return {
        "duration_s": round(dur, 2),
        "samples": len(df),
        "completed_loops": loops,
        "min_clearance_m": round(min_clearance, 4) if not math.isnan(min_clearance) else -1,
        "min_detected_dist_m": round(min_detected, 4) if not math.isnan(min_detected) else -1,
        "safety_margin_above_RI_m": round(min_clearance - ZONE_THRESHOLDS["RI"], 4) if not math.isnan(min_clearance) else -1,
        "max_lateral_dev_m": round(max_lat_dev, 4),
        "path_length_m": round(path_len, 3),
        "ideal_line_dist_m": round(ideal_dist, 3),
        "detour_ratio": round(detour_ratio, 3),
        "mean_speed_ms": round(float(df["speed"].mean()), 4),
        "max_speed_ms": round(float(df["speed"].max()), 4),
        "fov_87_enabled": int(fov_on),
        "h1_fov_visible_pct": round(vis_pct, 1),
        "pct_public": round(zone_pcts["PUBLIC"], 1),
        "pct_social": round(zone_pcts["SOCIAL"], 1),
        "pct_personal": round(zone_pcts["PERSONAL"], 1),
        "pct_intimate": round(zone_pcts["INTIMATE"], 1),
        "patrol_ax": ax_pt,
        "patrol_ay": ay_pt,
        "patrol_bx": bx_pt,
        "patrol_by": by_pt,
    }


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


def _asymmetric_gaussian_contour(ax, cx, cy, angle_deg, sh=2.4, sr=1.2, sl=1.2):
    """Draw the asymmetric Gaussian boundary Gamma=1 around human (cx,cy)."""
    theta = np.linspace(0, 2 * np.pi, 200)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    s_long = np.where(cos_t >= 0, sh, sr)
    x_local = s_long * cos_t
    y_local = sl * sin_t
    rad = math.radians(angle_deg)
    ca, sa = math.cos(rad), math.sin(rad)
    xw = cx + ca * x_local - sa * y_local
    yw = cy + sa * x_local + ca * y_local
    ax.plot(xw, yw, color="#f59e0b", lw=1.1, ls="-.", alpha=0.65, label="Asym. Gaussian (Γ=1)")


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

# ── 1 · Trajectory + A<->B + Stationary Human + FOV ──────────────────
def plot_trajectory(ax, df: pd.DataFrame, humans: list[dict], summary: dict):
    rx = df["robot_x"].values
    ry = df["robot_y"].values

    # ── Draw A <-> B reference line & markers if present ───────────
    ax_pt, ay_pt = summary["patrol_ax"], summary["patrol_ay"]
    bx_pt, by_pt = summary["patrol_bx"], summary["patrol_by"]
    ax.plot([ax_pt, bx_pt], [ay_pt, by_pt], color="#a855f7", lw=1.5,
            ls="--", alpha=0.45, zorder=2, label="Ref Line A↔B")
    ax.plot(ax_pt, ay_pt, "o", color="#22c55e", ms=12, zorder=8,
            markeredgecolor="white", markeredgewidth=1.2)
    ax.text(ax_pt, ay_pt, "A", color="white", fontsize=7.5, fontweight="bold",
            ha="center", va="center", zorder=9)
    ax.plot(bx_pt, by_pt, "o", color="#3b82f6", ms=12, zorder=8,
            markeredgecolor="white", markeredgewidth=1.2)
    ax.text(bx_pt, by_pt, "B", color="white", fontsize=7.5, fontweight="bold",
            ha="center", va="center", zorder=9)

    # ── Draw 87° / 8m FOV cone from initial robot pose if enabled ──
    if summary["fov_87_enabled"] and len(df) > 0:
        ang0 = float(df["robot_angle_deg"].iloc[0])
        fov_wedge = Wedge(
            (rx[0], ry[0]), 8.0, ang0 - 43.5, ang0 + 43.5,
            facecolor="#06b6d4", alpha=0.07, edgecolor="#06b6d4",
            linestyle="--", linewidth=1.0, zorder=1, label="FOV 87° (8m) @ Start"
        )
        ax.add_patch(fov_wedge)

    # ── Robot trail coloured by speed ──────────────────────────────
    pts  = np.array([rx, ry]).T.reshape(-1, 1, 2)
    segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
    spd  = df["speed"].values
    norm = Normalize(vmin=0, vmax=max(spd.max(), 0.01))
    lc   = LineCollection(segs, cmap="cool", norm=norm, linewidth=2.2, alpha=0.9, zorder=4)
    lc.set_array(spd[:-1])
    ax.add_collection(lc)
    cb = plt.colorbar(lc, ax=ax, label="Robot speed (m/s)", shrink=0.65, pad=0.02)
    cb.ax.yaxis.label.set_color("#8090aa")
    cb.ax.tick_params(colors="#8090aa", labelsize=7)

    # Direction arrows along robot trajectory
    n_pts = len(rx)
    if n_pts > 20:
        for idx_arr in [n_pts // 6, n_pts // 3, (2 * n_pts) // 3, (5 * n_pts) // 6]:
            if idx_arr + 2 < n_pts:
                dx_a = rx[idx_arr + 2] - rx[idx_arr]
                dy_a = ry[idx_arr + 2] - ry[idx_arr]
                if math.hypot(dx_a, dy_a) > 0.02:
                    ang_a = math.degrees(math.atan2(dy_a, dx_a))
                    _heading_arrow(ax, rx[idx_arr], ry[idx_arr], ang_a,
                                   length=0.35, color="#06b6d4", lw=1.4, alpha=0.85)

    # ── Human positions + proxemic zones ───────────────────────────
    ri = ZONE_THRESHOLDS["RI"]
    rp = ZONE_THRESHOLDS["RP"]
    rs = ZONE_THRESHOLDS["RS"]

    for h in humans:
        cx, cy = h["mean_x"], h["mean_y"]
        col    = h["color"]
        idx    = h["idx"]

        _zone_fill(ax, cx, cy, rs, ZONE_COLORS["SOCIAL"],   alpha=0.04)
        _zone_fill(ax, cx, cy, rp, ZONE_COLORS["PERSONAL"], alpha=0.08)
        _zone_fill(ax, cx, cy, ri, ZONE_COLORS["INTIMATE"], alpha=0.14)

        _zone_ring(ax, cx, cy, rs, ZONE_COLORS["SOCIAL"],   lw=0.9, ls=(0, (6, 4)), alpha=0.4)
        _zone_ring(ax, cx, cy, rp, ZONE_COLORS["PERSONAL"], lw=1.2, ls=(0, (4, 3)), alpha=0.6)
        _zone_ring(ax, cx, cy, ri, ZONE_COLORS["INTIMATE"], lw=1.5, ls="-",         alpha=0.8)

        if idx == 1:
            _asymmetric_gaussian_contour(ax, cx, cy, h["mean_angle"])

        # Human mean-position marker
        ax.plot(cx, cy, "o", color=col, ms=11, zorder=6,
                markeredgecolor="white", markeredgewidth=1.2)
        ax.plot(cx, cy, "o", color=col, ms=6, zorder=7, alpha=0.9)
        _heading_arrow(ax, cx, cy, h["mean_angle"], length=0.55,
                       color=col, lw=1.8, alpha=0.9)

        ax.text(cx + 0.12, cy + 0.18, f"H{idx} (diam)",
                fontsize=7.5, color=col, fontweight="bold", zorder=8,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="#111620",
                          edgecolor=col, alpha=0.8, linewidth=0.8))

    # Annotate max lateral deviation point
    lat_vals = np.abs(df["lateral_dev_m"].values)
    if lat_vals.size and lat_vals.max() > 0.1:
        max_i = int(np.argmax(lat_vals))
        ax.annotate(
            f"Max evade: {lat_vals[max_i]:.2f}m",
            xy=(rx[max_i], ry[max_i]),
            xytext=(rx[max_i], ry[max_i] + (0.9 if ry[max_i] >= 5.0 else -0.9)),
            fontsize=6.8, color="#06b6d4", ha="center",
            arrowprops=dict(arrowstyle="->", color="#06b6d4", lw=1),
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#111620",
                      edgecolor="#06b6d4", alpha=0.85),
            zorder=10,
        )

    legend_handles = [
        mpatches.Patch(color="#22c55e", alpha=0.85, label=f"Point A ({ax_pt:.1f},{ay_pt:.1f})"),
        mpatches.Patch(color="#3b82f6", alpha=0.85, label=f"Point B ({bx_pt:.1f},{by_pt:.1f})"),
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
    ax.set_title("(1) Trajectory A↔B + Stationary H1 + FOV 87°")
    ax.legend(handles=legend_handles, fontsize=6.2, loc="upper right",
              framealpha=0.75, edgecolor="#263450")
    ax.grid(alpha=0.2)


# ── 2 · Distance & FOV Detection vs Time ─────────────────────────────
def plot_distance(ax, df: pd.DataFrame, humans: list[dict]):
    t = df["time_s"].values
    d_det = np.where(df["closest_dist_m"].values < 0, np.nan, df["closest_dist_m"].values)
    d_act = np.where(df["actual_dist_m"].values < 0, np.nan, df["actual_dist_m"].values)
    lat_d = np.abs(df["lateral_dev_m"].values)

    # Plot actual physical distance (dashed cyan) and FOV-detected distance (solid white)
    ax.plot(t, d_act, color="#38bdf8", lw=1.3, ls="--", alpha=0.75, label="Actual Dist to H1")
    ax.plot(t, d_det, color="#e8edf5", lw=2.0, label="Detected Dist (in 87° FOV)")
    ax.plot(t, lat_d, color="#a855f7", lw=1.2, ls=":", alpha=0.85, label="|Lateral Dev| from A↔B")

    # Shade blind-spot intervals when FOV is enabled and H1 is not visible
    if humans and df["fov_enabled"].max() > 0:
        vis = humans[0]["visible"]
        blind_labeled = False
        for is_vis, grp in groupby(zip(t, vis), key=lambda x: x[1]):
            if not is_vis:
                pts = list(grp)
                ax.axvspan(
                    pts[0][0], pts[-1][0], color="#475569", alpha=0.22,
                    label="Blind Spot (Outside 87° FOV)" if not blind_labeled else None
                )
                blind_labeled = True

    ax.axhspan(0,                     ZONE_THRESHOLDS["RI"],
               alpha=0.18, color=ZONE_COLORS["INTIMATE"], label=f"Intimate <{ZONE_THRESHOLDS['RI']} m")
    ax.axhspan(ZONE_THRESHOLDS["RI"], ZONE_THRESHOLDS["RP"],
               alpha=0.12, color=ZONE_COLORS["PERSONAL"], label=f"Personal <{ZONE_THRESHOLDS['RP']} m")
    ax.axhspan(ZONE_THRESHOLDS["RP"], ZONE_THRESHOLDS["RS"],
               alpha=0.06, color=ZONE_COLORS["SOCIAL"])

    valid = d_act[~np.isnan(d_act)]
    if valid.size:
        min_d = valid.min()
        min_t = t[np.nanargmin(d_act)]
        ax.annotate(f"min {min_d:.3f} m\nt={min_t:.1f}s",
                    xy=(min_t, min_d), xytext=(min_t + max(t[-1]*0.05, 0.5), min_d + 0.5),
                    fontsize=7, color="#22c55e" if min_d >= ZONE_THRESHOLDS["RI"] else "#ef4444",
                    arrowprops=dict(arrowstyle="->", color="#22c55e", lw=1),
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#111620",
                              edgecolor="#22c55e", alpha=0.85))

    ax.set_xlim(t[0], t[-1]); ax.set_ylim(bottom=0)
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Distance / Offset (m)")
    ax.set_title("(2) Robot-Human Distance & FOV Blind Spots")
    ax.legend(fontsize=6.2, loc="upper right")
    ax.grid(alpha=0.25)


# ── 3 · Robot Velocity ──────────────────────────────────────────────
def plot_velocity(ax, df: pd.DataFrame):
    t = df["time_s"].values
    ax.plot(t, df["robot_vx"],  color="#06b6d4", lw=1.5, label="Vx (along A↔B)")
    ax.plot(t, df["robot_vy"],  color="#a855f7", lw=1.5, label="Vy (lateral evade)")
    ax.plot(t, df["speed"],     color="#e8edf5", lw=2,   label="|V| speed")
    ax.axhline(0, color="#4a5a78", lw=0.8, linestyle="--")
    ax.set_xlim(t[0], t[-1])
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Velocity (m/s)")
    ax.set_title("(3) Robot Velocity Components")
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


# ── 8 · Robot Heading & Patrol Leg Timeline ──────────────────────────
def plot_heading(ax, df: pd.DataFrame):
    t = df["time_s"].values
    ax.plot(t, df["heading"], color="#06b6d4", lw=1.8, label="Camera / Robot Heading (°)")

    if "patrol_target" in df.columns and df["patrol_target"].notna().any():
        targets = df["patrol_target"].fillna("").values
        labeled_b, labeled_a = False, False
        for tgt, grp in groupby(zip(t, targets), key=lambda x: x[1]):
            pts = list(grp)
            if tgt == "B":
                ax.axvspan(pts[0][0], pts[-1][0], color="#3b82f6", alpha=0.08,
                           label="Leg A → B" if not labeled_b else None)
                labeled_b = True
            elif tgt == "A":
                ax.axvspan(pts[0][0], pts[-1][0], color="#22c55e", alpha=0.08,
                           label="Leg B → A" if not labeled_a else None)
                labeled_a = True

    ax.axhline(  0, color="#3b82f6", lw=0.8, ls="--", alpha=0.7, label="East / → B (0°)")
    ax.axhline(180, color="#22c55e", lw=0.8, ls=":",  alpha=0.7, label="West / → A (±180°)")
    ax.axhline(-180, color="#22c55e", lw=0.8, ls=":", alpha=0.7)
    ax.set_xlim(t[0], t[-1]); ax.set_ylim(-190, 190)
    ax.set_yticks([-180, -90, 0, 90, 180])
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Heading (degrees)")
    ax.set_title("(8) Robot & Camera Heading (FOV 87° Direction)")
    ax.legend(fontsize=6.5, loc="lower right"); ax.grid(alpha=0.25)


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
    df      = load_csv(csv_path)
    humans  = extract_humans(df)
    summary = compute_summary_metrics(df, humans)

    # Save quantitative summary CSV alongside graph
    stem = csv_path.stem
    sum_csv = GRAPH_DIR / f"{stem}_summary.csv"
    pd.DataFrame([summary]).to_csv(sum_csv, index=False)

    print(f"  [SUMMARY] Min Clearance : {summary['min_clearance_m']:.3f} m "
          f"(Safety margin above RI={ZONE_THRESHOLDS['RI']}m: +{summary['safety_margin_above_RI_m']:.3f} m)")
    print(f"  [SUMMARY] Max Evasion   : {summary['max_lateral_dev_m']:.3f} m lateral offset from A↔B centerline")
    print(f"  [SUMMARY] Path Length   : {summary['path_length_m']:.2f} m "
          f"(Ideal: {summary['ideal_line_dist_m']:.2f} m | Detour ratio: {summary['detour_ratio']:.3f}x)")
    print(f"  [SUMMARY] FOV 87° Vis   : {summary['h1_fov_visible_pct']:.1f}% visible | "
          f"Zones: PUBLIC {summary['pct_public']}% · SOCIAL {summary['pct_social']}% · "
          f"PERSONAL {summary['pct_personal']}% · INTIMATE {summary['pct_intimate']}%")
    print(f"  [CSV] -> {sum_csv}")

    fig = plt.figure(figsize=(22, 14), facecolor="#0a0d14")
    fig.patch.set_facecolor("#0a0d14")

    human_info = ", ".join(
        f"H{h['idx']}=({h['mean_x']:.1f},{h['mean_y']:.1f})"
        for h in humans
    ) or "none"

    fov_str = f"FOV 87°/8m ({summary['h1_fov_visible_pct']:.0f}% vis)" if summary["fov_87_enabled"] else "FOV 360°"

    fig.suptitle(
        f"Sim — Social-DSC Scenario Analysis (Stationary Human on A↔B Path)\n"
        f"Source: {csv_path.name}  |  Duration: {summary['duration_s']:.1f}s ({summary['samples']:,} pts)  |  "
        f"Loops: {summary['completed_loops']}  |  {fov_str}  |  "
        f"Min Clearance: {summary['min_clearance_m']:.3f} m  |  Max Lateral Evade: {summary['max_lateral_dev_m']:.3f} m  |  "
        f"Detour: {summary['detour_ratio']:.2f}x  |  Humans: {human_info}",
        fontsize=9.8, fontweight="bold", color="#e8edf5", y=0.995
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

    plot_trajectory   (axes[0], df, humans, summary)
    plot_distance     (axes[1], df, humans)
    plot_velocity     (axes[2], df)
    plot_zone_timeline(axes[3], df)
    plot_forces       (axes[4], df)
    plot_force_xy     (axes[5], df)
    plot_packets      (axes[6], df)
    plot_heading      (axes[7], df)
    plot_force_polar  (axes[8], df)

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
        raw = Path(explicit)
        candidates = [
            raw,
            HERE / raw,
            CSV_DIR / raw,
            CSV_DIR / raw.name,
            GRAPH_DIR / raw,
            GRAPH_DIR / raw.name,
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return [c.resolve()]
        sys.exit(f"ERROR: File not found: {explicit}\nChecked in: {CSV_DIR}")
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
        make_figure(csv_path)

    print(f"\nDone! Graphs saved to: {GRAPH_DIR}")


if __name__ == "__main__":
    main()
