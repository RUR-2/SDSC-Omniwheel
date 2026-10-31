# Sim — Matplotlib Analyser

BroneX-style telemetry analysis for **Sim** (SDSC Omniwheel Avoidance Simulator).

## Folder layout

```
Matplotlib/
├── analyse.py        ← main analysis script
├── csv/              ← drop exported sim_log CSV files here
│   └── sdsc_sim_2026-10-27T....csv
└── graph/            ← generated PNG + PDF figures appear here
    └── sdsc_sim_2026-10-27T....png
```

## Workflow

1. **Record** a session in Sim (click **⏺ Record**, drive around, click **⏹ Stop & Export**)
2. The browser downloads `sdsc_sim_<timestamp>.csv` — move it to `Matplotlib/csv/`
3. Run the analyser:

```bash
# auto-picks the newest CSV in csv/
python Matplotlib/analyse.py

# explicit file
python Matplotlib/analyse.py csv/sdsc_sim_2026-10-27T17-15-00.csv

# batch — all CSVs in csv/
python Matplotlib/analyse.py --all
```

## Outputs

For each input CSV, the script saves to `graph/`:

| File | Description |
|---|---|
| `<stem>.png` | 22×14 inch figure @ 150 dpi |
| `<stem>.pdf` | vector version for printing / paper |

## 9 panels produced

| # | Panel | Data used |
|---|---|---|
| ① | Trajectory + Proxemic Zones | robot_x, robot_y — colour = speed |
| ② | Distance vs Time | closest_dist_m with zone bands |
| ③ | Robot Velocity | robot_vx, robot_vy, \|V\| |
| ④ | Zone Timeline | zone column as colour bands |
| ⑤ | SFM Force Components | F_pa, F_sr, f_SIM magnitudes |
| ⑥ | Force X/Y Decomposition | fx_sim, fy_sim, fx_pa, fy_pa |
| ⑦ | ESP32 Packet Output | pkt_X, pkt_Y, pkt_W (0–255) |
| ⑧ | Robot Heading | robot_angle_deg |
| ⑨ | Force Polar | f_SIM direction scatter by zone |

## Requirements

```bash
pip install matplotlib numpy pandas
```
