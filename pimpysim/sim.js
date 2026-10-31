/* =============================================================
   Sim – Avoidance Simulation Engine  v3.0
   Implements Social-DSC from:
     "Dynamical System based Socially-aware Navigation for Mobile Robot"
     Chen & Liu, IECON 2024
   ============================================================= */

"use strict";

// ──────────────────────────────────────────────
// Parameter defaults — match paper & bluetooth_sdsc.py
// ──────────────────────────────────────────────
const DEFAULTS = {
  // DSC / Proxemic geometry
  RI: 0.45,   // intimate radius (m)
  RP: 1.20,   // personal radius (m)
  RS: 3.60,   // social radius (m)

  // SIM – pedestrian avoidance force (F_pa)  [Eq. 16, paper]
  Ap: 2.0,    // repulsion amplitude (N)
  Bp: 0.8,    // repulsion range (m)
  dp: 0.0,    // offset distance

  // SIM – social rule force (F_sr)  [Eq. 21]
  ksr: 1.0,   // sigmoid gain
  Bsr: 3.0,   // sigmoid steepness
  dsr: 0.2,   // lateral offset (right-hand-side bias)

  // SIM global
  kSIM: 0.35, // velocity output scaling  (paper: 0.3)
  wpa:  1.0,  // weight F_pa
  wpp:  0.5,  // weight F_pp (pedestrian priority – corridor clearing)
  wsr:  0.5,  // weight F_sr (social rule – pass right)

  // Asymmetric Gaussian zone shape (σ units = metres, paper Sec. IV-A)
  sigma_h: 2.4,  // ahead of pedestrian  (= ΔT·||v|| = 2s × 1.2m/s)
  sigma_r: 1.2,  // behind pedestrian    (= σh/2)
  sigma_l: 1.2,  // lateral

  // Robot driving
  SS: 0.50,   // joystick speed scale

  // DSC eigenvalue base
  lambdaV_k: 10.0,   // steepness of sigmoid λv  (paper: 10)
};

let params = { ...DEFAULTS };

// ──────────────────────────────────────────────
// World constants
// ──────────────────────────────────────────────
const WORLD_SIZE  = 10.0;
const MAX_TRAIL   = 100;
const NEUTRAL_PKT = 127;
const ROBOT_R_M   = 0.25;

// ──────────────────────────────────────────────
// Runtime state
// ──────────────────────────────────────────────
let ppm = 60;

let robot  = { x: 5, y: 5, angle: 0, vx: 0, vy: 0, vw: 0 };
let humans = [];  // { id, x, y, angle (heading rad), speed, walkSpeed, edgeBounce }
let nextId = 1;

// ── Human motion defaults ──────────────────────
let humanWalkSpeed  = 0.6;   // m/s default for new humans
let humanEdgeBounce = true;  // true = bounce, false = wrap-around
let trail  = [];

let keys        = {};
let mode        = 'drive';
let paused      = false;
let dragging    = null;
let hoveredId   = null;
let autoGoal    = null;
let prevZone    = 'PUBLIC';

// DSC + SIM diagnostic
let sfm = {
  zone: 'PUBLIC', closestDist: 999,
  fx_pa: 0, fy_pa: 0,   // F_pa contribution
  fx_sr: 0, fy_sr: 0,   // F_sr contribution
  fx_sim: 0, fy_sim: 0, // total SIM output
  numHumans: 0,
  modScale: 1.0,         // effective speed modulation from DSC
};

let lastTime = 0;

// ──────────────────────────────────────────────
// Recording state
// ──────────────────────────────────────────────
let recording     = false;
let recordBuf     = [];   // array of row objects
let recordStartT  = 0;    // performance.now() when started
let recordSimT    = 0;    // simulation time counter (s)
const MAX_REC_ROWS   = 50000; // ~83 min at 10 Hz — hard cap
const MAX_REC_HUMANS = 6;     // human slots recorded per row

// Build header: base columns + h1_x,h1_y,h1_angle_deg … h6_…
const _hCols = Array.from({length: MAX_REC_HUMANS}, (_, i) =>
  `h${i+1}_x,h${i+1}_y,h${i+1}_angle_deg`).join(',');
const REC_CSV_HEADER =
  'time_s,robot_x,robot_y,robot_vx,robot_vy,robot_angle_deg,' +
  'closest_dist_m,zone,' +
  'fx_pa,fy_pa,fx_sr,fy_sr,fx_sim,fy_sim,' +
  `pkt_X,pkt_Y,pkt_W,num_humans,${_hCols}`;

// ──────────────────────────────────────────────
// Math helpers
// ──────────────────────────────────────────────
const hypot   = (a, b) => Math.sqrt(a * a + b * b);
const clamp   = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const dot     = (ax, ay, bx, by) => ax * bx + ay * by;
const cross2d = (ax, ay, bx, by) => ax * by - ay * bx;
const norm    = (x, y) => { const m = hypot(x, y) || 1e-9; return [x / m, y / m]; };

// ──────────────────────────────────────────────
// Coordinate
// ──────────────────────────────────────────────
function w2p(wx, wy, H) { return { px: wx * ppm, py: H - wy * ppm }; }
function p2w(px, py, H) { return { wx: px / ppm, wy: (H - py) / ppm }; }

// ──────────────────────────────────────────────
// Proxemic zone
// ──────────────────────────────────────────────
function getZone(d) {
  if (d < params.RI) return 'INTIMATE';
  if (d < params.RP) return 'PERSONAL';
  if (d < params.RS) return 'SOCIAL';
  return 'PUBLIC';
}

// ──────────────────────────────────────────────
// DSC: Asymmetric Gaussian distance function Γ
//   Models the pedestrian proxemic zone as an
//   asymmetric ellipse oriented along heading.
//   Eq. 3 of paper, zone from Kirby 2010.
// ──────────────────────────────────────────────
function gammaHuman(rx, ry, h) {
  const dx = rx - h.x, dy = ry - h.y;
  const cosA = Math.cos(h.angle), sinA = Math.sin(h.angle);

  // Project into pedestrian frame (heading = +x)
  const dLong = cosA * dx + sinA * dy;   // longitudinal
  const dLat  = -sinA * dx + cosA * dy;  // lateral

  // Asymmetric Gaussian (ahead bigger than behind)
  const sigma_long = dLong >= 0 ? params.sigma_h : params.sigma_r;
  const sigma_lat  = params.sigma_l;

  // Γ = (||xi - xp|| / R(xi))²   — we use the Gaussian form
  const val = (dLong / sigma_long) ** 2 + (dLat / sigma_lat) ** 2;
  return val;  // Γ = 1 is the boundary
}

// Gradient of Γ w.r.t. robot position → normal vector
function gammaGradient(rx, ry, h) {
  const eps = 0.001;
  const g0 = gammaHuman(rx, ry, h);
  const gx = (gammaHuman(rx + eps, ry, h) - g0) / eps;
  const gy = (gammaHuman(rx, ry + eps, h) - g0) / eps;
  return { gx, gy };
}

// ──────────────────────────────────────────────
// DSC: Eigenvalues (Eq. 7-9 of paper)
// ──────────────────────────────────────────────
function computeLambdaV(rx, ry, rvx, rvy, hx, hy, hvx, hvy) {
  // λv = sigmoid of approach velocity dot approach direction
  // → near 0 when approaching, near 1 when receding
  const relVx = rvx - hvx, relVy = rvy - hvy;
  const dirX  = rx - hx,   dirY  = ry - hy;
  const d_dot = dot(relVx, relVy, dirX, dirY);
  return 1.0 / (1.0 + Math.exp(-params.lambdaV_k * d_dot));
}

function computeEigenvalues(Gamma, lambdaV) {
  const inv = 1.0 / Math.max(Gamma, 0.01);
  const lam_n = lambdaV + (1 - lambdaV) * (1 - inv);  // Eq. 7 → 0 at boundary
  const lam_e = lambdaV + (1 - lambdaV) * (1 + inv);  // Eq. 8 → large at boundary
  return { lam_n, lam_e };
}

// ──────────────────────────────────────────────
// DSC: Modulation matrix for one obstacle
//   M = E · D · E⁻¹   (Eq. 5-6)
//   E = [n, e]  orthogonal basis
// ──────────────────────────────────────────────
function dscModulation(rx, ry, rvx, rvy, h) {
  const Gamma = gammaHuman(rx, ry, h);

  // Human velocity for λv computation
  const hvx = Math.cos(h.angle) * h.speed;
  const hvy = Math.sin(h.angle) * h.speed;

  const lambdaV = computeLambdaV(rx, ry, rvx, rvy, h.x, h.y, hvx, hvy);
  const { lam_n, lam_e } = computeEigenvalues(Gamma, lambdaV);

  // Normal vector = normalised gradient of Γ
  const { gx, gy } = gammaGradient(rx, ry, h);
  const [nx, ny]   = norm(gx, gy);

  // Tangent vector (90° CCW from normal)
  const ex = -ny, ey = nx;

  // E = [[nx, ex],[ny, ey]]
  // D = [[lam_n, 0],[0, lam_e]]
  // M = E · D · E⁻¹
  // Since E is orthogonal: E⁻¹ = Eᵀ
  // M = E D Eᵀ
  const m00 = lam_n * nx * nx + lam_e * ex * ex;
  const m01 = lam_n * nx * ny + lam_e * ex * ey;
  const m10 = lam_n * ny * nx + lam_e * ey * ex;
  const m11 = lam_n * ny * ny + lam_e * ey * ey;

  return { m00, m01, m10, m11, Gamma, lam_n, lam_e };
}

// ──────────────────────────────────────────────
// DSC: Multi-obstacle weighted modulation (Eq. 11-13)
// ──────────────────────────────────────────────
function combinedModulation(rx, ry, rvx, rvy, humanList) {
  if (humanList.length === 0)
    return { m00: 1, m01: 0, m10: 0, m11: 1, minGamma: 999 };

  const mats   = humanList.map(h => dscModulation(rx, ry, rvx, rvy, h));
  const Gammas = mats.map(m => m.Gamma);
  const minG   = Math.min(...Gammas);

  if (humanList.length === 1) {
    const m = mats[0];
    return { m00: m.m00, m01: m.m01, m10: m.m10, m11: m.m11, minGamma: minG };
  }

  // ω'_i = Π_{j≠i} (Γ_j - 1)  [Eq. 13]
  const omega_prime = Gammas.map((g, i) =>
    Gammas.reduce((acc, gj, j) => j === i ? acc : acc * Math.max(gj - 1, 0), 1)
  );
  const sum_w = omega_prime.reduce((a, b) => a + b, 0) || 1;
  const omega  = omega_prime.map(w => w / sum_w);  // [Eq. 12]

  let cm00 = 0, cm01 = 0, cm10 = 0, cm11 = 0;
  for (let i = 0; i < mats.length; i++) {
    cm00 += omega[i] * mats[i].m00;
    cm01 += omega[i] * mats[i].m01;
    cm10 += omega[i] * mats[i].m10;
    cm11 += omega[i] * mats[i].m11;
  }

  return { m00: cm00, m01: cm01, m10: cm10, m11: cm11, minGamma: minG };
}

// ──────────────────────────────────────────────
// SIM: F_pa – Pedestrian Avoidance force (Eq. 16-18)
// ──────────────────────────────────────────────
function computeFpa(rx, ry) {
  let fxT = 0, fyT = 0;
  for (const h of humans) {
    const dx = rx - h.x, dy = ry - h.y;
    const dist = hypot(dx, dy);
    if (dist < 1e-6) { fxT += 50; continue; }
    // Use asymmetric Γ to weight force direction
    const mag = params.Ap * Math.exp((params.dp - dist) / params.Bp);
    fxT += mag * dx / dist;
    fyT += mag * dy / dist;
  }
  return { fxT, fyT };
}

// ──────────────────────────────────────────────
// SIM: F_pp – Pedestrian Priority (Eq. 19-20)
//   Guides robot around obstacles to clear the
//   pedestrian's straight-ahead path.
//   Simplified: attractive force toward a point
//   lateral to each pedestrian's path.
// ──────────────────────────────────────────────
function computeFpp(rx, ry) {
  let fxT = 0, fyT = 0;
  for (const h of humans) {
    const dx = rx - h.x, dy = ry - h.y;
    const dist = hypot(dx, dy);
    if (dist > params.RS * 1.1 || dist < 1e-6) continue;

    // Unit heading & left-normal of pedestrian
    const hx = Math.cos(h.angle), hy = Math.sin(h.angle);
    const lx = -hy, ly = hx;  // 90° CCW = left-normal

    // Cross product: positive = robot on pedestrian's left
    const side = cross2d(hx, hy, dx / dist, dy / dist);

    // Steer robot toward the right-hand side of the pedestrian
    // (attract robot to a point ~1m to pedestrian's right)
    const targetX = h.x - lx * 1.0;  // right side = -left-normal
    const targetY = h.y - ly * 1.0;
    const tdx = targetX - rx, tdy = targetY - ry;
    const tdist = hypot(tdx, tdy);
    if (tdist < 1e-6) continue;

    const mag = params.Ap * 0.5 * Math.exp((params.dp - dist) / params.Bp);
    fxT += mag * tdx / tdist;
    fyT += mag * tdy / tdist;
  }
  return { fxT, fyT };
}

// ──────────────────────────────────────────────
// SIM: F_sr – Social Rule (Eq. 21-22)
//   Right-hand traffic rule: sigmoid that pushes
//   robot to the right when approaching a
//   pedestrian from the front.
// ──────────────────────────────────────────────
function computeFsr(rx, ry) {
  let fxT = 0, fyT = 0;
  for (const h of humans) {
    const dx = rx - h.x, dy = ry - h.y;
    const dist = hypot(dx, dy);
    if (dist > params.RS || dist < 1e-6) continue;

    // nv_i = unit heading of pedestrian
    const nvx = Math.cos(h.angle), nvy = Math.sin(h.angle);
    // left-normal to pedestrian heading
    const nv_Lx = -nvy, nv_Ly = nvx;

    // λr = cross(nv_i, ξ̃_i) - δ  [Eq. 22]
    const lambda_r = cross2d(nvx, nvy, dx / dist, dy / dist) - params.dsr;

    // sigmoid activation
    const sigmoid = 1.0 / (1.0 + Math.exp(-params.Bsr * lambda_r));

    // Force along pedestrian's left-normal (pushes robot left relative to ped → right-hand rule)
    const mag = params.ksr * sigmoid;
    fxT += mag * nv_Lx;
    fyT += mag * nv_Ly;
  }
  return { fxT, fyT };
}

// ──────────────────────────────────────────────
// SIM: Combine all forces → normalized reference direction
//   [Eq. 14-15]  f_SIM = k_SIM * F_SIM / ||F_SIM||
// ──────────────────────────────────────────────
function computeSIM(rx, ry) {
  const pa = computeFpa(rx, ry);
  const pp = computeFpp(rx, ry);
  const sr = computeFsr(rx, ry);

  const Fx = params.wpa * pa.fxT + params.wpp * pp.fxT + params.wsr * sr.fxT;
  const Fy = params.wpa * pa.fyT + params.wpp * pp.fyT + params.wsr * sr.fyT;
  const mag = hypot(Fx, Fy);

  sfm.fx_pa  = pa.fxT; sfm.fy_pa = pa.fyT;
  sfm.fx_sr  = sr.fxT; sfm.fy_sr = sr.fyT;

  if (mag < 0.01) return { fx: 0, fy: 0 };
  return { fx: params.kSIM * Fx / mag, fy: params.kSIM * Fy / mag };
}

// ──────────────────────────────────────────────
// Social-DSC: Full velocity computation  [Eq. 10]
//   ξ̇r = M_safety(ξr) · (f(ξr) + f_SIM(ξr))
// ──────────────────────────────────────────────
function socialDSC(vxNom, vyNom) {
  if (humans.length === 0) {
    sfm = { zone: 'PUBLIC', closestDist: 999, fx_pa: 0, fy_pa: 0,
            fx_sr: 0, fy_sr: 0, fx_sim: 0, fy_sim: 0, numHumans: 0, modScale: 1.0 };
    return { vx: vxNom, vy: vyNom };
  }

  // Closest distance (for zone display)
  const closestDist = Math.min(...humans.map(h => hypot(h.x - robot.x, h.y - robot.y)));

  // SIM: social inference dynamics
  const fSIM = computeSIM(robot.x, robot.y);
  sfm.fx_sim = fSIM.fx; sfm.fy_sim = fSIM.fy;

  // Combined nominal + SIM
  const fTotalX = vxNom + fSIM.fx;
  const fTotalY = vyNom + fSIM.fy;

  // DSC modulation matrix
  const M = combinedModulation(robot.x, robot.y, robot.vx, robot.vy, humans);

  // Apply modulation: ξ̇ = M · f_total
  const vxMod = M.m00 * fTotalX + M.m01 * fTotalY;
  const vyMod = M.m10 * fTotalX + M.m11 * fTotalY;

  // Speed clamping  (preserve direction, cap magnitude)
  const speed = hypot(vxMod, vyMod);
  const maxSpeed = params.SS;
  let vxOut = vxMod, vyOut = vyMod;
  if (speed > maxSpeed) { vxOut = vxMod / speed * maxSpeed; vyOut = vyMod / speed * maxSpeed; }

  // Update diagnostics
  const nomSpeed = hypot(vxNom, vyNom) || 1e-9;
  sfm.modScale   = clamp(speed / nomSpeed, 0, 1);
  sfm.zone       = getZone(closestDist);
  sfm.closestDist = closestDist;
  sfm.numHumans  = humans.length;

  return { vx: vxOut, vy: vyOut };
}

// ──────────────────────────────────────────────
// Physics tick (20 Hz)
// ──────────────────────────────────────────────
function tick(dt) {
  if (paused) return;

  // ── Move humans ────────────────────────────────
  const MARGIN = 0.2;
  for (const h of humans) {
    if (!h.speed || h.speed < 1e-6) continue;
    let nx = h.x + Math.cos(h.angle) * h.speed * dt;
    let ny = h.y + Math.sin(h.angle) * h.speed * dt;

    if (humanEdgeBounce) {
      // Bounce off walls
      if (nx < MARGIN)              { nx = MARGIN;            h.angle = Math.PI - h.angle; }
      if (nx > WORLD_SIZE - MARGIN) { nx = WORLD_SIZE-MARGIN; h.angle = Math.PI - h.angle; }
      if (ny < MARGIN)              { ny = MARGIN;            h.angle = -h.angle; }
      if (ny > WORLD_SIZE - MARGIN) { ny = WORLD_SIZE-MARGIN; h.angle = -h.angle; }
    } else {
      // Wrap around
      if (nx < MARGIN)              nx = WORLD_SIZE - MARGIN;
      if (nx > WORLD_SIZE - MARGIN) nx = MARGIN;
      if (ny < MARGIN)              ny = WORLD_SIZE - MARGIN;
      if (ny > WORLD_SIZE - MARGIN) ny = MARGIN;
    }
    h.x = nx; h.y = ny;
  }

  // Nominal velocity from driver / planner
  let vxNom = 0, vyNom = 0, vwNom = 0;

  if (mode === 'drive') {
    if (keys['w'] || keys['arrowup'])    vyNom += params.SS;
    if (keys['s'] || keys['arrowdown'])  vyNom -= params.SS;
    if (keys['a'] || keys['arrowleft'])  vxNom -= params.SS;
    if (keys['d'] || keys['arrowright']) vxNom += params.SS;
    if (keys['q']) vwNom += 1;
    if (keys['e']) vwNom -= 1;
  } else if (autoGoal) {
    const dx = autoGoal.x - robot.x, dy = autoGoal.y - robot.y;
    const d  = hypot(dx, dy);
    if (d > 0.15) {
      vxNom = (dx / d) * params.SS;
      vyNom = (dy / d) * params.SS;
    } else {
      autoGoal = null;
      addLog('✅ Goal reached', 'log-success');
    }
  }

  // Social-DSC modulation
  const { vx, vy } = socialDSC(vxNom, vyNom);

  const MOVE = 4.0;
  robot.x += vx * dt * MOVE;
  robot.y += vy * dt * MOVE;
  robot.angle += vwNom * dt * 2.5;

  const mg = 0.3;
  robot.x = clamp(robot.x, mg, WORLD_SIZE - mg);
  robot.y = clamp(robot.y, mg, WORLD_SIZE - mg);
  robot.vx = vx; robot.vy = vy; robot.vw = vwNom;

  trail.push({ x: robot.x, y: robot.y });
  if (trail.length > MAX_TRAIL) trail.shift();

  // ── Data recording ───────────────────────────
  if (recording && recordBuf.length < MAX_REC_ROWS) {
    recordSimT += dt;
    const xB = toByte(robot.vx), yB = toByte(robot.vy), wB = toByte(robot.vw);
    recordBuf.push({
      time_s:          +recordSimT.toFixed(4),
      robot_x:         +robot.x.toFixed(4),
      robot_y:         +robot.y.toFixed(4),
      robot_vx:        +robot.vx.toFixed(4),
      robot_vy:        +robot.vy.toFixed(4),
      robot_angle_deg: +(robot.angle * 180 / Math.PI).toFixed(2),
      closest_dist_m:  +(sfm.closestDist < 900 ? sfm.closestDist : -1).toFixed(4),
      zone:            sfm.zone,
      fx_pa:           +sfm.fx_pa.toFixed(4),
      fy_pa:           +sfm.fy_pa.toFixed(4),
      fx_sr:           +sfm.fx_sr.toFixed(4),
      fy_sr:           +sfm.fy_sr.toFixed(4),
      fx_sim:          +sfm.fx_sim.toFixed(4),
      fy_sim:          +sfm.fy_sim.toFixed(4),
      pkt_X:           xB,
      pkt_Y:           yB,
      pkt_W:           wB,
      num_humans:      humans.length,
      // Human slots h1..h6 — empty string if slot unused (pandas reads as NaN)
      ...Object.fromEntries(
        Array.from({length: MAX_REC_HUMANS}, (_, i) => {
          const h = humans[i];
          return [
            [`h${i+1}_x`,         h ? +h.x.toFixed(4)                     : ''],
            [`h${i+1}_y`,         h ? +h.y.toFixed(4)                     : ''],
            [`h${i+1}_angle_deg`, h ? +(h.angle * 180 / Math.PI).toFixed(2) : ''],
          ];
        }).flat()
      ),
    });
    updateRecUI();
  }
}

// ──────────────────────────────────────────────
// Rendering constants
// ──────────────────────────────────────────────
const ZONE_COL = {
  INTIMATE: '#ef4444', PERSONAL: '#f97316', SOCIAL: '#f59e0b', PUBLIC: '#22c55e',
};

// ──────────────────────────────────────────────
// Draw utilities
// ──────────────────────────────────────────────
function drawArrowHead(ctx, x1, y1, x2, y2) {
  const angle = Math.atan2(y2 - y1, x2 - x1);
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  const L = 9;
  ctx.beginPath(); ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - L * Math.cos(angle - 0.38), y2 - L * Math.sin(angle - 0.38));
  ctx.lineTo(x2 - L * Math.cos(angle + 0.38), y2 - L * Math.sin(angle + 0.38));
  ctx.closePath(); ctx.fill();
}

// ──────────────────────────────────────────────
// Render arena
// ──────────────────────────────────────────────
function render(canvas, ctx) {
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  const bg = ctx.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, '#0d1220'); bg.addColorStop(1, '#090d18');
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

  drawGrid(ctx, W, H);
  drawProxemicZones(ctx, H);
  drawTrail(ctx, H);
  for (const h of humans) drawHuman(ctx, h, H);
  drawSIMForces(ctx, H);
  drawRobot(ctx, H);

  if (mode === 'auto' && autoGoal) {
    const { px, py } = w2p(autoGoal.x, autoGoal.y, H);
    const rp = w2p(robot.x, robot.y, H);
    ctx.strokeStyle = 'rgba(59,130,246,0.35)';
    ctx.lineWidth = 1; ctx.setLineDash([5, 8]);
    ctx.beginPath(); ctx.moveTo(rp.px, rp.py); ctx.lineTo(px, py); ctx.stroke();
    ctx.setLineDash([]);
    ctx.strokeStyle = '#3b82f6'; ctx.lineWidth = 2; ctx.setLineDash([4, 4]);
    const r = 14;
    ctx.strokeRect(px - r, py - r, r * 2, r * 2);
    ctx.setLineDash([]);
  }
}

function drawGrid(ctx, W, H) {
  ctx.strokeStyle = 'rgba(30,42,64,0.7)'; ctx.lineWidth = 1;
  for (let m = 0; m <= WORLD_SIZE; m++) {
    const a = w2p(m, 0, H), b = w2p(m, WORLD_SIZE, H);
    ctx.beginPath(); ctx.moveTo(a.px, a.py); ctx.lineTo(b.px, b.py); ctx.stroke();
    const c = w2p(0, m, H), d = w2p(WORLD_SIZE, m, H);
    ctx.beginPath(); ctx.moveTo(c.px, c.py); ctx.lineTo(d.px, d.py); ctx.stroke();
  }
  ctx.fillStyle = 'rgba(74,90,120,0.7)';
  ctx.font = '10px JetBrains Mono, monospace'; ctx.textAlign = 'left';
  for (let m = 1; m < WORLD_SIZE; m++) {
    const { px, py } = w2p(m, 0.25, H);
    ctx.fillText(`${m}m`, px - 8, py);
  }
}

// Draw asymmetric Gaussian proxemic zone for each human
function drawProxemicZones(ctx, H) {
  for (const h of humans) {
    const { px: hx, py: hy } = w2p(h.x, h.y, H);
    const sh = params.sigma_h * ppm;  // pixels
    const sr = params.sigma_r * ppm;
    const sl = params.sigma_l * ppm;

    ctx.save();
    ctx.translate(hx, hy);
    ctx.rotate(-h.angle);  // align with heading (screen Y is flipped)

    // Draw asymmetric ellipse: front half with σ_h, rear half with σ_r
    // Approximate with two half-ellipses
    for (const [col, fillA, strokeA, isFront] of [
      ['245,158,11', 0.06, 0.2, true],
      ['249,115,22', 0.10, 0.3, false],
    ]) {
      const rx_ = isFront ? sh : sr;
      const ry_ = sl;
      ctx.beginPath();
      // front semi-ellipse
      if (isFront) {
        ctx.ellipse(-sh * 0.5, 0, sh, sl, 0, -Math.PI / 2, Math.PI / 2);
        ctx.fillStyle = `rgba(${col},${fillA})`; ctx.fill();
        ctx.strokeStyle = `rgba(${col},${strokeA})`; ctx.lineWidth = 1.2;
        ctx.setLineDash([5, 4]); ctx.stroke(); ctx.setLineDash([]);
      } else {
        ctx.ellipse(sr * 0.5, 0, sr, sl, 0, Math.PI / 2, Math.PI * 1.5);
        ctx.fillStyle = `rgba(${col},${fillA})`; ctx.fill();
        ctx.strokeStyle = `rgba(${col},${strokeA})`; ctx.lineWidth = 1.2;
        ctx.setLineDash([4, 3]); ctx.stroke(); ctx.setLineDash([]);
      }
    }

    ctx.restore();

    // Intimate zone (always circular)
    const riPx = params.RI * ppm;
    ctx.beginPath(); ctx.arc(hx, hy, riPx, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(239,68,68,0.12)'; ctx.fill();
    ctx.strokeStyle = 'rgba(239,68,68,0.5)'; ctx.lineWidth = 1.5; ctx.stroke();
  }

  // Also draw DSC robot-centric zone circles for reference
  const { px: rx, py: ry } = w2p(robot.x, robot.y, H);
  const distLines = [
    { r: params.RS, c: 'rgba(245,158,11,0.07)', s: 'rgba(245,158,11,0.12)', d: [8, 6] },
    { r: params.RP, c: 'rgba(249,115,22,0.05)', s: 'rgba(249,115,22,0.18)', d: [5, 4] },
    { r: params.RI, c: 'rgba(239,68,68,0.05)',  s: 'rgba(239,68,68,0.30)',  d: [] },
  ];
  for (const z of distLines) {
    ctx.beginPath(); ctx.arc(rx, ry, z.r * ppm, 0, Math.PI * 2);
    ctx.fillStyle = z.c; ctx.fill();
    ctx.strokeStyle = z.s; ctx.lineWidth = 1; ctx.setLineDash(z.d); ctx.stroke();
    ctx.setLineDash([]);
  }
}

function drawTrail(ctx, H) {
  for (let i = 1; i < trail.length; i++) {
    const alpha = (i / trail.length) * 0.4;
    const a = w2p(trail[i - 1].x, trail[i - 1].y, H);
    const b = w2p(trail[i].x, trail[i].y, H);
    ctx.strokeStyle = `rgba(6,182,212,${alpha})`; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(a.px, a.py); ctx.lineTo(b.px, b.py); ctx.stroke();
  }
}

function drawHuman(ctx, h, H) {
  const { px, py } = w2p(h.x, h.y, H);
  const dist = hypot(h.x - robot.x, h.y - robot.y);
  const col  = ZONE_COL[getZone(dist)];
  const r    = (dragging && dragging.id === h.id) ? 22 : (hoveredId === h.id ? 20 : 16);

  // Glow
  const g = ctx.createRadialGradient(px, py, 0, px, py, r * 2.5);
  g.addColorStop(0, col + '44'); g.addColorStop(1, 'transparent');
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(px, py, r * 2.5, 0, Math.PI * 2); ctx.fill();

  // Body
  ctx.fillStyle = '#fff'; ctx.strokeStyle = col; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();

  // Heading arrow
  ctx.strokeStyle = col; ctx.lineWidth = 2.5;
  const hx2 = px + Math.cos(h.angle) * r * 1.5;
  const hy2 = py - Math.sin(h.angle) * r * 1.5;   // screen Y flipped
  ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(hx2, hy2); ctx.stroke();

  // Silhouette
  ctx.fillStyle = '#8090aa';
  ctx.beginPath(); ctx.arc(px, py - r * 0.35, r * 0.3, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#8090aa'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(px, py - r * 0.05); ctx.lineTo(px, py + r * 0.4); ctx.stroke();

  // Labels
  ctx.textAlign = 'center';
  ctx.fillStyle = '#e8edf5'; ctx.font = 'bold 10px Inter, sans-serif';
  ctx.fillText(`H${h.id}`, px, py + r + 14);
  ctx.fillStyle = col; ctx.font = '9px JetBrains Mono, monospace';
  ctx.fillText(`${dist.toFixed(2)}m`, px, py + r + 24);
  ctx.textAlign = 'left';
}

function drawSIMForces(ctx, H) {
  const { px: cx, py: cy } = w2p(robot.x, robot.y, H);

  // F_pa (repulsion) — magenta
  const paMag = hypot(sfm.fx_pa, sfm.fy_pa);
  if (paMag > 0.05) {
    const sc = Math.min(paMag * 30, 70);
    const ex = cx + (sfm.fx_pa / paMag) * sc;
    const ey = cy - (sfm.fy_pa / paMag) * sc;
    ctx.strokeStyle = '#ec4899'; ctx.fillStyle = '#ec4899'; ctx.lineWidth = 2.5;
    ctx.globalAlpha = 0.8; drawArrowHead(ctx, cx, cy, ex, ey); ctx.globalAlpha = 1;
    ctx.fillStyle = '#ec4899'; ctx.font = '10px JetBrains Mono, monospace';
    ctx.fillText('F_pa', ex + 4, ey - 4);
  }

  // F_sr (social rule) — purple
  const srMag = hypot(sfm.fx_sr, sfm.fy_sr);
  if (srMag > 0.02) {
    const sc = Math.min(srMag * 35, 55);
    const ex = cx + (sfm.fx_sr / srMag) * sc;
    const ey = cy - (sfm.fy_sr / srMag) * sc;
    ctx.strokeStyle = '#a855f7'; ctx.fillStyle = '#a855f7'; ctx.lineWidth = 2;
    ctx.globalAlpha = 0.7; drawArrowHead(ctx, cx, cy, ex, ey); ctx.globalAlpha = 1;
    ctx.fillStyle = '#a855f7'; ctx.font = '10px JetBrains Mono, monospace';
    ctx.fillText('F_sr', ex + 4, ey);
  }

  // f_SIM total — cyan bold
  const simMag = hypot(sfm.fx_sim, sfm.fy_sim);
  if (simMag > 0.01) {
    const sc = 65;
    const ex = cx + (sfm.fx_sim / simMag) * sc;
    const ey = cy - (sfm.fy_sim / simMag) * sc;
    ctx.strokeStyle = '#06b6d4'; ctx.fillStyle = '#06b6d4'; ctx.lineWidth = 3;
    ctx.globalAlpha = 0.9; drawArrowHead(ctx, cx, cy, ex, ey); ctx.globalAlpha = 1;
    ctx.fillStyle = '#06b6d4'; ctx.font = 'bold 10px JetBrains Mono, monospace';
    ctx.fillText('f_SIM', ex + 4, ey + 4);
  }
}

function drawRobot(ctx, H) {
  const { px, py } = w2p(robot.x, robot.y, H);
  const r = ROBOT_R_M * ppm;
  const glowCol = sfm.zone === 'INTIMATE' ? '#ef4444'
                : sfm.zone === 'PERSONAL' ? '#f97316' : '#06b6d4';

  const g = ctx.createRadialGradient(px, py, 0, px, py, r * 2.8);
  g.addColorStop(0, glowCol + '30'); g.addColorStop(1, 'transparent');
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(px, py, r * 2.8, 0, Math.PI * 2); ctx.fill();

  ctx.save();
  ctx.translate(px, py); ctx.rotate(-robot.angle);

  const bg = ctx.createRadialGradient(0, -r * 0.3, 0, 0, 0, r);
  bg.addColorStop(0, '#1e3a5f'); bg.addColorStop(1, '#0f1e35');
  ctx.fillStyle = bg; ctx.strokeStyle = glowCol; ctx.lineWidth = 2.5;
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2 - Math.PI / 6;
    i === 0 ? ctx.moveTo(Math.cos(a)*r, Math.sin(a)*r)
            : ctx.lineTo(Math.cos(a)*r, Math.sin(a)*r);
  }
  ctx.closePath(); ctx.fill(); ctx.stroke();

  ctx.fillStyle = glowCol;
  for (const wa of [0, Math.PI/2, Math.PI, Math.PI*1.5]) {
    ctx.beginPath(); ctx.arc(Math.cos(wa)*r, Math.sin(wa)*r, 4, 0, Math.PI*2); ctx.fill();
  }
  ctx.strokeStyle = glowCol; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(r * 0.7, 0); ctx.stroke();
  ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(0, 0, 4, 0, Math.PI*2); ctx.fill();
  ctx.restore();

  ctx.textAlign = 'center';
  ctx.fillStyle = '#e8edf5'; ctx.font = 'bold 11px Inter, sans-serif';
  ctx.fillText('SDSC', px, py + r + 14);
  ctx.textAlign = 'left';

  const vMag = hypot(robot.vx, robot.vy);
  if (vMag > 0.05) {
    const sc = 40;
    ctx.strokeStyle = 'rgba(6,182,212,0.6)'; ctx.fillStyle = 'rgba(6,182,212,0.6)';
    ctx.lineWidth = 2;
    drawArrowHead(ctx, px, py, px + robot.vx/vMag*vMag*sc, py - robot.vy/vMag*vMag*sc);
  }
}

// ──────────────────────────────────────────────
// Force polar canvas (right sidebar)
// ──────────────────────────────────────────────
function drawForceCanvas(fc, fctx) {
  const W = fc.width, H = fc.height;
  const cx = W/2, cy = H/2, R = W/2 - 8;
  fctx.clearRect(0, 0, W, H);

  fctx.strokeStyle = '#1e2a40'; fctx.lineWidth = 1;
  for (let r = R/3; r <= R+0.5; r += R/3) {
    fctx.beginPath(); fctx.arc(cx, cy, r, 0, Math.PI*2); fctx.stroke();
  }
  fctx.beginPath();
  fctx.moveTo(cx-R, cy); fctx.lineTo(cx+R, cy);
  fctx.moveTo(cx, cy-R); fctx.lineTo(cx, cy+R); fctx.stroke();

  // Robot dot
  fctx.fillStyle = '#06b6d4'; fctx.beginPath(); fctx.arc(cx, cy, 5, 0, Math.PI*2); fctx.fill();

  const maxD = params.RS * 1.2;
  for (const h of humans) {
    const dx = h.x - robot.x, dy = h.y - robot.y;
    const dist = hypot(dx, dy);
    const hpx = cx + (dx / maxD) * R, hpy = cy - (dy / maxD) * R;
    fctx.fillStyle = ZONE_COL[getZone(dist)];
    fctx.globalAlpha = 0.85;
    fctx.beginPath(); fctx.arc(hpx, hpy, 5, 0, Math.PI*2); fctx.fill();
    fctx.globalAlpha = 1;

    // Heading arrow on polar plot
    fctx.strokeStyle = '#8090aa'; fctx.lineWidth = 1;
    fctx.beginPath(); fctx.moveTo(hpx, hpy);
    fctx.lineTo(hpx + Math.cos(h.angle) * 10, hpy - Math.sin(h.angle) * 10);
    fctx.stroke();
  }

  // F_pa
  const paMag = hypot(sfm.fx_pa, sfm.fy_pa);
  if (paMag > 0.05) {
    const sc = Math.min(paMag/8, 1) * R * 0.8;
    fctx.strokeStyle = '#ec4899'; fctx.fillStyle = '#ec4899'; fctx.lineWidth = 2.5;
    drawArrowHead(fctx, cx, cy, cx + sfm.fx_pa/paMag*sc, cy - sfm.fy_pa/paMag*sc);
  }
  // F_sr
  const srMag = hypot(sfm.fx_sr, sfm.fy_sr);
  if (srMag > 0.02) {
    const sc = Math.min(srMag/5, 1) * R * 0.7;
    fctx.strokeStyle = '#a855f7'; fctx.fillStyle = '#a855f7'; fctx.lineWidth = 1.5;
    fctx.globalAlpha = 0.7;
    drawArrowHead(fctx, cx, cy, cx + sfm.fx_sr/srMag*sc, cy - sfm.fy_sr/srMag*sc);
    fctx.globalAlpha = 1;
  }
  // f_SIM total
  const simMag = hypot(sfm.fx_sim, sfm.fy_sim);
  if (simMag > 0.01) {
    const sc = R * 0.9;
    fctx.strokeStyle = '#06b6d4'; fctx.fillStyle = '#06b6d4'; fctx.lineWidth = 3;
    drawArrowHead(fctx, cx, cy, cx + sfm.fx_sim/simMag*sc, cy - sfm.fy_sim/simMag*sc);
  }
}

// ──────────────────────────────────────────────
// UI helpers
// ──────────────────────────────────────────────
const ZONE_LOG = { INTIMATE:'log-danger', PERSONAL:'log-warn', SOCIAL:'log-warn', PUBLIC:'log-success' };
const ZONE_MSG = {
  INTIMATE: '🔴 INTIMATE — HARD STOP (DSC boundary)',
  PERSONAL: '🟠 PERSONAL — STRONG evasion',
  SOCIAL:   '🟡 SOCIAL — SIM force active',
  PUBLIC:   '🟢 PUBLIC — Free motion',
};

function toByte(v) { return clamp(Math.round(NEUTRAL_PKT + v * 127.5), 0, 255); }

function updateUI() {
  const col = ZONE_COL[sfm.zone];
  document.getElementById('zoneIndicator').className = 'status-pill ' + sfm.zone.toLowerCase();
  document.getElementById('zoneText').textContent = sfm.zone;
  const dot = document.getElementById('zoneDot');
  dot.style.background = col; dot.style.boxShadow = `0 0 6px ${col}`;

  document.getElementById('humanCount').textContent = sfm.numHumans;
  document.getElementById('closestDist').textContent =
    sfm.closestDist < 900 ? sfm.closestDist.toFixed(2) + 'm' : '—';
  document.getElementById('forceVal').textContent =
    hypot(sfm.fx_sim, sfm.fy_sim).toFixed(3);
  const spd = Math.round(hypot(robot.vx, robot.vy) / (params.SS || 1) * 100);
  document.getElementById('speedVal').textContent = clamp(spd, 0, 100) + '%';

  const xB = toByte(robot.vx), yB = toByte(robot.vy), wB = toByte(robot.vw);
  document.getElementById('packetCode').textContent = `<${xB},${yB},${wB}>`;
  ['X','Y','W'].forEach((ch, i) => {
    const b = [xB, yB, wB][i];
    document.getElementById('pkt' + ch).textContent = b;
    document.getElementById('bar' + ch).style.width = (b/255*100) + '%';
  });

  if (sfm.zone !== prevZone) { addLog(ZONE_MSG[sfm.zone], ZONE_LOG[sfm.zone]); prevZone = sfm.zone; }

  // Force table — now shows F_pa, F_sr per human
  const table = document.getElementById('forceTable');
  if (!humans.length) {
    table.innerHTML = '<p class="no-data">No detections</p>';
  } else {
    table.innerHTML = '<div style="display:flex;justify-content:space-between;font-size:9px;color:#4a5a78;padding:2px 0">' +
      '<span>ID</span><span>Zone</span><span>Dist</span><span>Γ</span><span>f_SIM</span></div>' +
      humans.map(h => {
        const d    = hypot(h.x - robot.x, h.y - robot.y);
        const z    = getZone(d);
        const Gam  = gammaHuman(robot.x, robot.y, h).toFixed(2);
        const fpa  = computeFpa(robot.x, robot.y);
        const fMag = hypot(sfm.fx_sim, sfm.fy_sim).toFixed(2);
        return `<div style="border-bottom:1px solid #1e2a40;padding:3px 0;display:flex;justify-content:space-between;gap:4px">
          <span style="color:#8090aa">H${h.id}</span>
          <span style="color:${ZONE_COL[z]}">${z.slice(0,4)}</span>
          <span style="font-family:monospace;color:#e8edf5">${d.toFixed(2)}m</span>
          <span style="font-family:monospace;color:${ZONE_COL[z]}">${Gam}</span>
          <span style="font-family:monospace;color:#ec4899">${fMag}</span>
        </div>`;
      }).join('')
  }
}

// ──────────────────────────────────────────────
// Log
// ──────────────────────────────────────────────
const MAX_LOG = 80;
function addLog(msg, cls = 'log-info') {
  const c = document.getElementById('logContainer'); if (!c) return;
  const p = document.createElement('p');
  p.className = `log-entry ${cls}`;
  p.textContent = `[${new Date().toLocaleTimeString('en-GB',{hour12:false})}] ${msg}`;
  c.appendChild(p); c.scrollTop = c.scrollHeight;
  while (c.children.length > MAX_LOG) c.removeChild(c.firstChild);
}
function clearLog() { const c = document.getElementById('logContainer'); if (c) c.innerHTML = ''; }

// ──────────────────────────────────────────────
// Recording controls
// ──────────────────────────────────────────────
function startRecording() {
  if (recording) return;
  recordBuf     = [];
  recordSimT    = 0;
  recordStartT  = performance.now();
  recording     = true;
  document.getElementById('recBtn').classList.add('recording');
  document.getElementById('recBtn').textContent = '⏹ Stop & Export';
  document.getElementById('recStatus').style.display = 'flex';
  addLog('⏺ Recording started — collecting telemetry', 'log-danger');
}

function stopRecording() {
  if (!recording) return;
  recording = false;
  document.getElementById('recBtn').classList.remove('recording');
  document.getElementById('recBtn').textContent = '⏺ Record';
  document.getElementById('recStatus').style.display = 'none';
  const n = recordBuf.length;
  addLog(`⏹ Recording stopped — ${n} rows collected`, 'log-success');
  if (n > 0) exportCSV();
  else addLog('⚠️ No data to export', 'log-warn');
}

function toggleRecording() {
  if (recording) stopRecording();
  else startRecording();
}

function exportCSV() {
  const cols = REC_CSV_HEADER.split(',');
  const rows = [REC_CSV_HEADER];
  for (const row of recordBuf) {
    rows.push(cols.map(k => row[k] !== undefined ? row[k] : '').join(','));
  }
  const csv  = rows.join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  const ts   = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const fname = `sdsc_sim_${ts}.csv`;
  a.href = url;
  a.download = fname;
  a.click();
  URL.revokeObjectURL(url);
  addLog(`💾 Downloaded: ${fname}  (${recordBuf.length} rows)`, 'log-success');
  addLog('📁 Move CSV → pimpysim/Matplotlib/csv/', 'log-info');
  addLog('📊 Then run: python Matplotlib/analyse.py', 'log-info');
}

function updateRecUI() {
  const el = document.getElementById('recCounter');
  const et = document.getElementById('recElapsed');
  if (!el || !et) return;
  el.textContent = recordBuf.length.toLocaleString() + ' rows';
  const s = ((performance.now() - recordStartT) / 1000).toFixed(1);
  et.textContent = s + 's';
}

// ──────────────────────────────────────────────
// Actions (called from HTML buttons & keyboard)
// ──────────────────────────────────────────────
function clearHumans() {
  humans = []; nextId = 1;
  sfm = { zone:'PUBLIC', closestDist:999, fx_pa:0, fy_pa:0, fx_sr:0, fy_sr:0,
          fx_sim:0, fy_sim:0, numHumans:0, modScale:1 };
  addLog('🗑️ All humans cleared', 'log-warn');
  const hint = document.getElementById('canvasHint'); if (hint) hint.style.opacity = '0.7';
}

// ──────────────────────────────────────────────
// Human motion controls
// ──────────────────────────────────────────────

/** Set all humans walking in a cardinal direction (or stop). */
function setHumanDir(dir) {
  const DIRS = {
    up:    Math.PI / 2,
    down: -Math.PI / 2,
    right:  0,
    left:   Math.PI,
  };
  if (dir === 'stop') {
    humans.forEach(h => { h.speed = 0; });
    addLog('🚶 All humans stopped', 'log-info');
    highlightDirBtn(null);
    return;
  }
  const angle = DIRS[dir];
  if (angle === undefined) return;
  humans.forEach(h => { h.angle = angle; h.speed = humanWalkSpeed; });
  const emoji = { up:'↑', down:'↓', left:'←', right:'→' }[dir];
  addLog(`🚶 All humans walking ${emoji} (${humanWalkSpeed.toFixed(1)} m/s)`, 'log-info');
  highlightDirBtn(dir);
}

/** Update the walk speed for all existing + future humans. */
function setHumanWalkSpeed(v) {
  humanWalkSpeed = parseFloat(v);
  // Update any already-moving humans
  humans.forEach(h => { if (h.speed > 0) h.speed = humanWalkSpeed; });
  const el = document.getElementById('valHumanSpeed');
  if (el) el.textContent = humanWalkSpeed.toFixed(1) + ' m/s';
}

/** Toggle bounce vs wrap edge behaviour. */
function setEdgeBounce(val) {
  humanEdgeBounce = val;
  document.getElementById('btnBounce').classList.toggle('active', val);
  document.getElementById('btnWrap').classList.toggle('active', !val);
  addLog(`🔁 Edge mode: ${val ? 'Bounce' : 'Wrap-around'}`, 'log-info');
}

/** Visual feedback: highlight the active direction button. */
function highlightDirBtn(dir) {
  ['up','down','left','right','stop'].forEach(d => {
    const el = document.getElementById('dirBtn_' + d);
    if (el) el.classList.toggle('active', d === dir);
  });
}

function resetRobot() {
  robot = { x: 5, y: 5, angle: 0, vx: 0, vy: 0, vw: 0 };
  trail = []; autoGoal = null;
  addLog('⟳ Robot reset to center', 'log-info');
}

function setMode(m) {
  mode = m; autoGoal = null;
  document.getElementById('btnDrive').classList.toggle('active', m === 'drive');
  document.getElementById('btnAuto').classList.toggle('active', m === 'auto');
  document.getElementById('modeDesc').textContent = m === 'drive'
    ? 'Keyboard drives the robot. Social-DSC modulates velocity.'
    : 'Click arena to set a goal. Social-DSC navigates autonomously.';
  addLog(`🔄 Mode: ${m.toUpperCase()}`, 'log-info');
}

function togglePause() {
  paused = !paused;
  document.getElementById('pauseBtn').textContent = paused ? '▶ Resume' : '⏸ Pause';
  addLog(paused ? '⏸ Paused' : '▶ Resumed', 'log-info');
}

function updateParam(key, val) {
  params[key] = parseFloat(val);
  const FMT = {
    RI:'valRI', RP:'valRP', RS:'valRS',
    Ap:'valAp', Bp:'valBp',
    kSIM:'valKSIM', ksr:'valKsr',
    sigma_h:'valSH', sigma_l:'valSL',
    SS:'valSS',
    wpa:'valWpa', wpp:'valWpp', wsr:'valWsr',
  };
  const FMTFN = {
    RI: v => `${parseFloat(v).toFixed(2)} m`,
    RP: v => `${parseFloat(v).toFixed(2)} m`,
    RS: v => `${parseFloat(v).toFixed(2)} m`,
    Ap: v => `${parseFloat(v).toFixed(1)} N`,
    Bp: v => `${parseFloat(v).toFixed(2)} m`,
    kSIM: v => parseFloat(v).toFixed(2),
    ksr: v => parseFloat(v).toFixed(2),
    sigma_h: v => `${parseFloat(v).toFixed(2)} m`,
    sigma_l: v => `${parseFloat(v).toFixed(2)} m`,
    SS: v => parseFloat(v).toFixed(2),
    wpa: v => parseFloat(v).toFixed(2),
    wpp: v => parseFloat(v).toFixed(2),
    wsr: v => parseFloat(v).toFixed(2),
  };
  if (FMT[key]) document.getElementById(FMT[key]).textContent = FMTFN[key](val);
}

function resetParams() {
  params = { ...DEFAULTS };
  const MAP = {
    RI:'slRI', RP:'slRP', RS:'slRS', Ap:'slAp', Bp:'slBp',
    kSIM:'slKSIM', ksr:'slKsr', sigma_h:'slSH', sigma_l:'slSL',
    SS:'slSS', wpa:'slWpa', wpp:'slWpp', wsr:'slWsr',
  };
  for (const [k, id] of Object.entries(MAP)) {
    const el = document.getElementById(id);
    if (el) { el.value = DEFAULTS[k]; updateParam(k, DEFAULTS[k]); }
  }
  addLog('↺ Params reset to Social-DSC defaults', 'log-info');
}

// ──────────────────────────────────────────────
// Bootstrap
// ──────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  const canvas    = document.getElementById('arena');
  const ctx       = canvas.getContext('2d');
  const fCanvas   = document.getElementById('forceCanvas');
  const fCtx      = fCanvas.getContext('2d');
  const container = document.getElementById('canvasContainer');

  function resizeCanvas() {
    let size = Math.min(container.clientWidth, container.clientHeight) - 20;
    if (size <= 50) size = 600;
    canvas.width = size; canvas.height = size;
    ppm = size / WORLD_SIZE;
  }
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  // ── Game loop ─────────────────────────────
  function loop(ts) {
    const dt = Math.min((ts - lastTime) / 1000, 0.1);
    lastTime = ts;
    tick(dt);
    render(canvas, ctx);
    drawForceCanvas(fCanvas, fCtx);
    updateUI();
    requestAnimationFrame(loop);
  }
  lastTime = performance.now();
  requestAnimationFrame(loop);

  // ── Keyboard ──────────────────────────────
  document.addEventListener('keydown', e => {
    const k = e.key.toLowerCase(); keys[k] = true;
    if (k === ' ') { e.preventDefault(); ['w','a','s','d'].forEach(x => keys[x] = false); }
    if (k === 'c') clearHumans();
    if (k === 'r') resetRobot();
    // rotate selected human heading with [ and ]
    if (k === '[') { const h = humans.find(h => h.id === hoveredId); if (h) h.angle += 0.2; }
    if (k === ']') { const h = humans.find(h => h.id === hoveredId); if (h) h.angle -= 0.2; }
  });
  document.addEventListener('keyup', e => { keys[e.key.toLowerCase()] = false; });

  // ── Canvas helpers ─────────────────────────
  function canvasXY(e) {
    const rect = canvas.getBoundingClientRect();
    return {
      px: (e.clientX - rect.left) * (canvas.width  / rect.width),
      py: (e.clientY - rect.top)  * (canvas.height / rect.height),
    };
  }

  function humanAt(px, py) {
    return humans.find(h => {
      const p = w2p(h.x, h.y, canvas.height);
      return hypot(px - p.px, py - p.py) < 22;
    }) || null;
  }

  function placeHuman(px, py) {
    const { wx, wy } = p2w(px, py, canvas.height);
    const id = nextId++;
    // Inherit current global direction if any human is already walking
    const walkingH = humans.find(h => h.speed > 0);
    const angle = walkingH ? walkingH.angle : Math.atan2(robot.y - wy, robot.x - wx);
    const speed = walkingH ? humanWalkSpeed : 0;
    humans.push({ id, x: clamp(wx, 0.2, WORLD_SIZE-0.2), y: clamp(wy, 0.2, WORLD_SIZE-0.2),
                  angle, speed });
    const moving = speed > 0 ? ` · walking ${speed.toFixed(1)}m/s` : ' · stationary';
    addLog(`👤 H${id} placed at (${wx.toFixed(2)}, ${wy.toFixed(2)})${moving}`, 'log-info');
    const hint = document.getElementById('canvasHint'); if (hint) hint.style.opacity = '0';
  }

  function removeHuman(id) {
    humans = humans.filter(h => h.id !== id);
    addLog(`❌ H${id} removed`, 'log-warn');
    if (!humans.length) { const hint = document.getElementById('canvasHint'); if (hint) hint.style.opacity = '0.7'; }
  }

  // ── Mouse events ──────────────────────────
  canvas.addEventListener('mousedown', e => {
    e.preventDefault();
    const { px, py } = canvasXY(e);
    const h = humanAt(px, py);
    if (e.button === 2) { if (h) removeHuman(h.id); return; }
    if (h) {
      const p = w2p(h.x, h.y, canvas.height);
      dragging = { id: h.id, ox: px - p.px, oy: py - p.py };
    } else if (mode === 'auto') {
      const { wx, wy } = p2w(px, py, canvas.height);
      autoGoal = { x: clamp(wx, 0.2, WORLD_SIZE-0.2), y: clamp(wy, 0.2, WORLD_SIZE-0.2) };
      addLog(`📍 Goal → (${autoGoal.x.toFixed(2)}, ${autoGoal.y.toFixed(2)})`, 'log-info');
    } else {
      placeHuman(px, py);
    }
  });

  canvas.addEventListener('mousemove', e => {
    const { px, py } = canvasXY(e);
    if (dragging) {
      const { wx, wy } = p2w(px - dragging.ox, py - dragging.oy, canvas.height);
      const h = humans.find(h => h.id === dragging.id);
      if (h) { h.x = clamp(wx, 0.2, WORLD_SIZE-0.2); h.y = clamp(wy, 0.2, WORLD_SIZE-0.2); }
    } else {
      const h = humanAt(px, py);
      hoveredId = h ? h.id : null;
      canvas.style.cursor = h ? 'grab' : 'crosshair';
    }
  });

  canvas.addEventListener('mouseup',    () => { dragging = null; });
  canvas.addEventListener('mouseleave', () => { dragging = null; hoveredId = null; });
  canvas.addEventListener('contextmenu', e => e.preventDefault());

  canvas.addEventListener('touchstart', e => {
    e.preventDefault();
    const t = e.touches[0], rect = canvas.getBoundingClientRect();
    const px = (t.clientX - rect.left) * (canvas.width / rect.width);
    const py = (t.clientY - rect.top)  * (canvas.height / rect.height);
    const h  = humanAt(px, py);
    if (h) { const p = w2p(h.x, h.y, canvas.height); dragging = { id: h.id, ox: px-p.px, oy: py-p.py }; }
    else placeHuman(px, py);
  }, { passive: false });

  canvas.addEventListener('touchmove', e => {
    e.preventDefault(); if (!dragging) return;
    const t = e.touches[0], rect = canvas.getBoundingClientRect();
    const px = (t.clientX - rect.left) * (canvas.width / rect.width);
    const py = (t.clientY - rect.top)  * (canvas.height / rect.height);
    const { wx, wy } = p2w(px-dragging.ox, py-dragging.oy, canvas.height);
    const h = humans.find(h => h.id === dragging.id);
    if (h) { h.x = clamp(wx, 0.2, WORLD_SIZE-0.2); h.y = clamp(wy, 0.2, WORLD_SIZE-0.2); }
  }, { passive: false });

  canvas.addEventListener('touchend', () => { dragging = null; });

  addLog('🟢 Social-DSC engine ready (Chen & Liu, IECON 2024)', 'log-success');
  addLog('💡 WASD=drive · Click=place human · Drag=move · [/]=rotate heading', 'log-info');
  addLog('📐 DSC modulation matrix active — asymmetric Gaussian zones enabled', 'log-info');
  addLog('🚶 Use Human Motion panel to make humans walk in a direction', 'log-info');
  addLog('⏺ Click Record to start collecting CSV log data', 'log-info');
});
