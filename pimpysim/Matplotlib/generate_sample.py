#!/usr/bin/env python3
"""
Simulate the exact Social-DSC scenario from sim.js:
  - Robot loops A(1.5, 5.0) -> B(8.5, 5.0) -> A(1.5, 5.0)
  - 1 Stationary Human (H1) in the middle of the path at (5.0, 5.0)
  - Vision Sensor FOV = 87 degrees in front of robot, max distance = 8.0 m
Exports CSV to Matplotlib/csv/skenario_h1_diam_tengah_ab.csv
"""
import csv
import math
import pathlib

OUT = pathlib.Path(__file__).parent / "csv" / "skenario_h1_diam_tengah_ab.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

MAX_REC_HUMANS = 6
_h_cols = ",".join(
    f"h{i}_x,h{i}_y,h{i}_angle_deg,h{i}_visible"
    for i in range(1, MAX_REC_HUMANS + 1)
)
HEADER = (
    "time_s,robot_x,robot_y,robot_vx,robot_vy,robot_angle_deg,"
    "closest_dist_m,actual_dist_m,zone,"
    "fx_pa,fy_pa,fx_sr,fy_sr,fx_sim,fy_sim,"
    "pkt_X,pkt_Y,pkt_W,num_humans,num_visible_humans,fov_enabled,"
    "mode,patrol_target,patrol_loop,patrol_ax,patrol_ay,patrol_bx,patrol_by,goal_dist_m,lateral_dev_m,"
    + _h_cols
)

# Parameters matching sim.js DEFAULTS
RI, RP, RS = 0.45, 1.20, 3.60
AP, BP, DP = 2.0, 0.8, 0.0
KSR, BSR, DSR = 1.0, 3.0, 0.2
KSIM, WPA, WPP, WSR = 0.35, 1.0, 0.5, 0.5
SIGMA_H, SIGMA_R, SIGMA_L = 2.4, 1.2, 1.2
SS = 0.50
LAMBDA_V_K = 10.0
MOVE = 4.0

FOV_DEG = 87.0
FOV_HALF_RAD = math.radians(FOV_DEG * 0.5)
FOV_MAX_DIST = 8.0

# Scenario setup: A(1.5, 5.0) <-> B(8.5, 5.0), H1 stationary at (5.0, 5.0) facing West (pi)
AX, AY = 1.5, 5.0
BX, BY = 8.5, 5.0
HX, HY, H_ANGLE = 5.0, 5.0, math.pi


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def get_zone(d):
    if d < RI:
        return "INTIMATE"
    if d < RP:
        return "PERSONAL"
    if d < RS:
        return "SOCIAL"
    return "PUBLIC"


def is_visible(rx, ry, r_angle, hx, hy):
    dx, dy = hx - rx, hy - ry
    dist = math.hypot(dx, dy)
    if dist > FOV_MAX_DIST:
        return False
    if dist < 1e-6:
        return True
    ang_to_h = math.atan2(dy, dx)
    diff = math.atan2(math.sin(ang_to_h - r_angle), math.cos(ang_to_h - r_angle))
    return abs(diff) <= FOV_HALF_RAD


def gamma_human(rx, ry, hx, hy, h_angle):
    dx, dy = rx - hx, ry - hy
    ca, sa = math.cos(h_angle), math.sin(h_angle)
    d_long = ca * dx + sa * dy
    d_lat = -sa * dx + ca * dy
    s_long = SIGMA_H if d_long >= 0 else SIGMA_R
    return (d_long / s_long) ** 2 + (d_lat / SIGMA_L) ** 2


def gamma_grad(rx, ry, hx, hy, h_angle):
    eps = 0.001
    g0 = gamma_human(rx, ry, hx, hy, h_angle)
    gx = (gamma_human(rx + eps, ry, hx, hy, h_angle) - g0) / eps
    gy = (gamma_human(rx, ry + eps, hx, hy, h_angle) - g0) / eps
    return gx, gy


def to_byte(v):
    return int(clamp(round(127 + v * 127.5), 0, 255))


def run_simulation(target_loops=1):
    dt = 1.0 / 30.0
    rx, ry = AX, AY
    rvx, rvy = 0.0, 0.0
    r_angle = 0.0  # facing East toward B
    patrol_target = "B"
    patrol_loops = 0
    half_legs = 0
    rows = []

    for step in range(4000):
        t = step * dt
        gx, gy = (AX, AY) if patrol_target == "A" else (BX, BY)
        dx_g, dy_g = gx - rx, gy - ry
        d_goal = math.hypot(dx_g, dy_g)

        if d_goal > 0.18:
            vx_nom = (dx_g / d_goal) * SS
            vy_nom = (dy_g / d_goal) * SS
        else:
            if patrol_target == "B":
                patrol_target = "A"
                half_legs += 1
            else:
                patrol_target = "B"
                patrol_loops += 1
                half_legs += 1
            gx, gy = (AX, AY) if patrol_target == "A" else (BX, BY)
            dx_g, dy_g = gx - rx, gy - ry
            d_goal = math.hypot(dx_g, dy_g)
            vx_nom = (dx_g / d_goal) * SS
            vy_nom = (dy_g / d_goal) * SS

        # Auto-face movement direction
        if math.hypot(vx_nom, vy_nom) > 0.02:
            des_ang = math.atan2(vy_nom, vx_nom)
            ang_diff = math.atan2(math.sin(des_ang - r_angle), math.cos(des_ang - r_angle))
            r_angle += clamp(ang_diff, -6.0 * dt, 6.0 * dt)
            r_angle = math.atan2(math.sin(r_angle), math.cos(r_angle))

        actual_dist = math.hypot(rx - HX, ry - HY)
        vis = is_visible(rx, ry, r_angle, HX, HY)

        if not vis:
            closest_dist = -1.0
            zone = "PUBLIC"
            fx_pa = fy_pa = fx_sr = fy_sr = fx_sim = fy_sim = 0.0
            vx_out, vy_out = vx_nom, vy_nom
        else:
            closest_dist = actual_dist
            zone = get_zone(closest_dist)
            dx, dy = rx - HX, ry - HY
            dist = max(actual_dist, 1e-6)

            # F_pa
            mag_pa = AP * math.exp((DP - dist) / BP)
            fx_pa, fy_pa = mag_pa * dx / dist, mag_pa * dy / dist

            # F_pp
            fx_pp = fy_pp = 0.0
            if dist <= RS * 1.1:
                hx_u, hy_u = math.cos(H_ANGLE), math.sin(H_ANGLE)
                lx_u, ly_u = -hy_u, hx_u
                d_long = hx_u * dx + hy_u * dy
                d_lat = lx_u * dx + ly_u * dy
                if d_long > -0.2:
                    lat_sign = 1.0 if d_lat >= 0.15 else -1.0
                    mag_pp = AP * 0.35 * math.exp((DP - dist) / BP)
                    fx_pp = mag_pp * (lat_sign * lx_u + 0.25 * dx / dist)
                    fy_pp = mag_pp * (lat_sign * ly_u + 0.25 * dy / dist)

            # F_sr
            fx_sr = fy_sr = 0.0
            if dist <= RS:
                nvx, nvy = math.cos(H_ANGLE), math.sin(H_ANGLE)
                nv_lx, nv_ly = -nvy, nvx
                lam_r = (nvx * (dy / dist) - nvy * (dx / dist)) - DSR
                sig = 1.0 / (1.0 + math.exp(-BSR * lam_r))
                fx_sr, fy_sr = KSR * sig * nv_lx, KSR * sig * nv_ly

            Fx = WPA * fx_pa + WPP * fx_pp + WSR * fx_sr
            Fy = WPA * fy_pa + WPP * fy_pp + WSR * fy_sr
            f_mag = math.hypot(Fx, Fy)
            if f_mag < 0.01:
                fx_sim = fy_sim = 0.0
            else:
                if closest_dist < RP:
                    urgency = max(KSIM, SS * clamp((RP - closest_dist) / max(RP - RI, 0.2), 0.3, 1.0))
                else:
                    urgency = KSIM * min(1.0, f_mag / 0.5)
                fx_sim = urgency * Fx / f_mag
                fy_sim = urgency * Fy / f_mag

            f_tot_x = vx_nom + fx_sim
            f_tot_y = vy_nom + fy_sim

            # DSC modulation
            Gam = gamma_human(rx, ry, HX, HY, H_ANGLE)
            d_dot = rvx * dx + rvy * dy
            lam_v = 1.0 / (1.0 + math.exp(-LAMBDA_V_K * d_dot))
            gam_eff = max(Gam, 1.0)
            inv = 1.0 / gam_eff
            lam_n = max(0.0, lam_v + (1.0 - lam_v) * (1.0 - inv))
            lam_e = min(2.5, lam_v + (1.0 - lam_v) * (1.0 + inv))

            ggx, ggy = gamma_grad(rx, ry, HX, HY, H_ANGLE)
            gm = math.hypot(ggx, ggy) or 1e-9
            nx, ny = ggx / gm, ggy / gm
            if (f_tot_x * nx + f_tot_y * ny) > 0:
                lam_n = 1.0
            ex, ey = -ny, nx

            m00 = lam_n * nx * nx + lam_e * ex * ex
            m01 = lam_n * nx * ny + lam_e * ex * ey
            m10 = lam_n * ny * nx + lam_e * ey * ex
            m11 = lam_n * ny * ny + lam_e * ey * ey

            vx_mod = m00 * f_tot_x + m01 * f_tot_y
            vy_mod = m10 * f_tot_x + m11 * f_tot_y

            # Head-on colinear anti-stall (matching sim.js)
            nom_mag = math.hypot(vx_nom, vy_nom)
            if nom_mag > 0.05 and closest_dist < RS * 0.9:
                to_hx, to_hy = HX - rx, HY - ry
                app_cos = (vx_nom * to_hx + vy_nom * to_hy) / (nom_mag * dist)
                if app_cos > 0.25:
                    rx_u, ry_u = -to_hx / dist, -to_hy / dist
                    cross_off = (vx_nom / nom_mag) * to_hy - (vy_nom / nom_mag) * to_hx
                    pass_right = True if abs(cross_off) < 0.18 else (cross_off > 0)
                    tx = -ry_u if pass_right else ry_u
                    ty = rx_u if pass_right else -rx_u
                    tang_proj = vx_mod * tx + vy_mod * ty
                    min_tang = nom_mag * 0.72 * clamp((RS * 0.9 - dist) / (RP * 1.1), 0.25, 1.0)
                    if tang_proj < min_tang:
                        boost = min_tang - tang_proj
                        vx_mod += tx * boost
                        vy_mod += ty * boost

            spd = math.hypot(vx_mod, vy_mod)
            if spd > SS:
                vx_out, vy_out = vx_mod / spd * SS, vy_mod / spd * SS
            else:
                vx_out, vy_out = vx_mod, vy_mod

        rx = clamp(rx + vx_out * dt * MOVE, 0.3, 9.7)
        ry = clamp(ry + vy_out * dt * MOVE, 0.3, 9.7)
        rvx, rvy = vx_out, vy_out

        ab_dx, ab_dy = BX - AX, BY - AY
        ab_len = math.hypot(ab_dx, ab_dy) or 1e-6
        lat_dev = ((rx - AX) * (-ab_dy) + (ry - AY) * ab_dx) / ab_len

        row = {
            "time_s": round(t, 4),
            "robot_x": round(rx, 4),
            "robot_y": round(ry, 4),
            "robot_vx": round(rvx, 4),
            "robot_vy": round(rvy, 4),
            "robot_angle_deg": round(math.degrees(r_angle), 2),
            "closest_dist_m": round(closest_dist, 4),
            "actual_dist_m": round(actual_dist, 4),
            "zone": zone,
            "fx_pa": round(fx_pa, 4),
            "fy_pa": round(fy_pa, 4),
            "fx_sr": round(fx_sr, 4),
            "fy_sr": round(fy_sr, 4),
            "fx_sim": round(fx_sim, 4),
            "fy_sim": round(fy_sim, 4),
            "pkt_X": to_byte(rvx),
            "pkt_Y": to_byte(rvy),
            "pkt_W": 127,
            "num_humans": 1,
            "num_visible_humans": 1 if vis else 0,
            "fov_enabled": 1,
            "mode": "patrol",
            "patrol_target": patrol_target,
            "patrol_loop": patrol_loops,
            "patrol_ax": AX,
            "patrol_ay": AY,
            "patrol_bx": BX,
            "patrol_by": BY,
            "goal_dist_m": round(d_goal, 4),
            "lateral_dev_m": round(lat_dev, 4),
            "h1_x": HX,
            "h1_y": HY,
            "h1_angle_deg": round(math.degrees(H_ANGLE), 2),
            "h1_visible": 1 if vis else 0,
        }
        for i in range(2, MAX_REC_HUMANS + 1):
            row[f"h{i}_x"] = ""
            row[f"h{i}_y"] = ""
            row[f"h{i}_angle_deg"] = ""
            row[f"h{i}_visible"] = ""
        rows.append(row)

        if half_legs >= target_loops * 2:
            break

    return rows


if __name__ == "__main__":
    rows = run_simulation(target_loops=1)
    with open(OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER.split(","))
        writer.writeheader()
        writer.writerows(rows)
    print(f"OK  Generated scenario CSV ({len(rows)} rows) -> {OUT}")
