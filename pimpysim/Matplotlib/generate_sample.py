#!/usr/bin/env python3
"""Generate a synthetic sim CSV to test analyse.py without needing the browser."""
import csv, math, random, pathlib

OUT = pathlib.Path(__file__).parent / "csv" / "sample_test.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

HEADER = (
    "time_s,robot_x,robot_y,robot_vx,robot_vy,robot_angle_deg,"
    "closest_dist_m,zone,"
    "fx_pa,fy_pa,fx_sr,fy_sr,fx_sim,fy_sim,"
    "pkt_X,pkt_Y,pkt_W,num_humans,"
    "h1_x,h1_y,h1_angle_deg,"
    "h2_x,h2_y,h2_angle_deg,"
    "h3_x,h3_y,h3_angle_deg,"
    "h4_x,h4_y,h4_angle_deg,"
    "h5_x,h5_y,h5_angle_deg,"
    "h6_x,h6_y,h6_angle_deg"
)

RI, RP, RS = 0.45, 1.20, 3.60
DT = 1/30
rows = []
rx, ry = 5.0, 5.0
vx, vy = 0.0, 0.0
angle = 0.0

# One human at (7, 5) heading left
hx, hy = 7.0, 5.0

random.seed(42)
for i in range(1200):
    t = i * DT

    # Simple drive toward (8,8) then avoid human
    tx, ty = 8.0, 8.0
    dx_g, dy_g = tx - rx, ty - ry
    d_g = math.hypot(dx_g, dy_g)
    vx_nom = (dx_g / d_g) * 0.35 if d_g > 0.1 else 0
    vy_nom = (dy_g / d_g) * 0.35 if d_g > 0.1 else 0

    # Distance to human
    d_h = math.hypot(rx - hx, ry - hy)
    zone = "INTIMATE" if d_h < RI else ("PERSONAL" if d_h < RP else ("SOCIAL" if d_h < RS else "PUBLIC"))

    # Fake forces
    if d_h < RS:
        fx_pa = (rx - hx) / d_h * 2 * math.exp(-d_h / 0.8)
        fy_pa = (ry - hy) / d_h * 2 * math.exp(-d_h / 0.8)
        fx_sr = 0.1 * (1 / (1 + math.exp(-3 * (d_h - 0.5))))
        fy_sr = 0.0
        fx_sim = fx_pa * 0.35 + fx_sr * 0.35
        fy_sim = fy_pa * 0.35 + fy_sr * 0.35
    else:
        fx_pa = fy_pa = fx_sr = fy_sr = fx_sim = fy_sim = 0.0

    vx = vx_nom + fx_sim
    vy = vy_nom + fy_sim
    spd = math.hypot(vx, vy)
    if spd > 0.5:
        vx, vy = vx / spd * 0.5, vy / spd * 0.5

    rx = max(0.3, min(9.7, rx + vx * DT * 4))
    ry = max(0.3, min(9.7, ry + vy * DT * 4))
    angle = math.degrees(math.atan2(vy, vx)) if spd > 0.01 else angle

    def byte(v): return max(0, min(255, round(127 + v * 127.5)))

    rows.append({
        "time_s": round(t, 4),
        "robot_x": round(rx, 4),
        "robot_y": round(ry, 4),
        "robot_vx": round(vx, 4),
        "robot_vy": round(vy, 4),
        "robot_angle_deg": round(angle, 2),
        "closest_dist_m": round(d_h, 4),
        "zone": zone,
        "fx_pa": round(fx_pa, 4),
        "fy_pa": round(fy_pa, 4),
        "fx_sr": round(fx_sr, 4),
        "fy_sr": round(fy_sr, 4),
        "fx_sim": round(fx_sim, 4),
        "fy_sim": round(fy_sim, 4),
        "pkt_X": byte(vx),
        "pkt_Y": byte(vy),
        "pkt_W": 127,
        "num_humans": 2,
        # H1 — static at (7, 5) heading 180 deg (facing left)
        "h1_x": 7.0, "h1_y": 5.0, "h1_angle_deg": 180.0,
        # H2 — static at (3, 7) heading -45 deg (facing down-right)
        "h2_x": 3.0, "h2_y": 7.0, "h2_angle_deg": -45.0,
        # H3-H6 — empty (NaN in pandas)
        "h3_x": "", "h3_y": "", "h3_angle_deg": "",
        "h4_x": "", "h4_y": "", "h4_angle_deg": "",
        "h5_x": "", "h5_y": "", "h5_angle_deg": "",
        "h6_x": "", "h6_y": "", "h6_angle_deg": "",
    })

with open(OUT, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=HEADER.split(","))
    writer.writeheader()
    writer.writerows(rows)

print(f"OK  Generated {len(rows)} rows -> {OUT}")
