# Sim — Matplotlib Telemetry & Scenario Analyser

BroneX-style telemetry analysis for **Sim** (SDSC Omniwheel Avoidance Simulator), including support for **Loop A↔B Patrol**, **87° / 8 m Camera FOV**, and the **Stationary Human in Center (`H1 Diam di Tengah Jalan`)** scenario.

## Folder layout

```
Matplotlib/
├── analyse.py          ← main 9-panel analysis + summary metrics script
├── generate_sample.py  ← offline generator for the A↔B + stationary center human + 87° FOV scenario
├── csv/                ← drop exported CSV files here
│   └── skenario_h1_diam_tengah_ab_*.csv
└── graph/              ← generated PNG + PDF figures + *_summary.csv appear here
```

## Workflow (Browser Data Collector)

1. Open `pimpysim/index.html` in your browser.
2. In the right sidebar (**Data Collector → Skenario Uji**):
   - Click **`🧍 Set Skenario: H1 Diam di Tengah (A↔B)`** to place Point **A** at `(1.5, 5.0)`, Point **B** at `(8.5, 5.0)`, stationary **H1** at `(5.0, 5.0)`, and enable **Loop A↔B** + **FOV 87° · 8 m**.
   - Choose **Auto-stop target** (`0.5 Loop (A → B)`, `1 Loop (A → B → A)`, `2 Loops`, or `3 Loops`).
   - Click **`🎬 Setup & Record Skenario`** — the robot starts at **A**, navigates around stationary **H1** to **B**, returns to **A**, and **automatically stops & downloads** `skenario_h1_diam_tengah_ab_<timestamp>.csv`.
3. Move the downloaded CSV into `pimpysim/Matplotlib/csv/` and run:

```bash
# auto-picks the newest CSV in csv/
python Matplotlib/analyse.py

# or generate the scenario CSV directly from Python & analyse it:
python Matplotlib/generate_sample.py
python Matplotlib/analyse.py skenario_h1_diam_tengah_ab.csv

# batch — process all CSVs in csv/
python Matplotlib/analyse.py --all
```

## Outputs

For each input CSV, `analyse.py` saves to `Matplotlib/graph/`:

| File | Description |
|---|---|
| `<stem>.png` | 22×14 inch 9-panel figure @ 150 dpi |
| `<stem>.pdf` | Vector version for reports / papers |
| `<stem>_summary.csv` | Quantitative metrics (`min_clearance_m`, `max_lateral_dev_m`, `detour_ratio`, `h1_fov_visible_pct`, zone percentages, etc.) |

## 9 panels produced

| # | Panel | Data used |
|---|---|---|
| ① | Trajectory A↔B + Stationary H1 + FOV 87° | `robot_x`, `robot_y`, `patrol_ax/ay/bx/by`, asymmetric Gaussian zone, FOV 87° cone, max lateral evasion |
| ② | Robot-Human Distance & FOV Blind Spots | `actual_dist_m`, `closest_dist_m` (in 87° FOV), `lateral_dev_m`, shaded FOV blind spots |
| ③ | Robot Velocity Components | `robot_vx`, `robot_vy`, `\|V\|` |
| ④ | Zone Timeline | `zone` (`PUBLIC`, `SOCIAL`, `PERSONAL`, `INTIMATE`) |
| ⑤ | SFM Force Components | `F_pa`, `F_sr`, `f_SIM` magnitudes |
| ⑥ | Force X/Y Decomposition | `fx_sim`, `fy_sim`, `fx_pa`, `fy_pa` |
| ⑦ | ESP32 Packet Output | `pkt_X`, `pkt_Y`, `pkt_W` (0–255) |
| ⑧ | Robot & Camera Heading (FOV 87° Direction) | `robot_angle_deg` + `Leg A → B` / `Leg B → A` regions |
| ⑨ | Force Polar | `f_SIM` direction scatter coloured by proxemic zone |
