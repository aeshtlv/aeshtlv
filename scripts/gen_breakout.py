#!/usr/bin/env python3
"""Generate assets/breakout.svg вЂ” a self-playing neon Breakout loop.

A deterministic physics sim plays the game once, then the trajectory and the
per-brick break timings are baked into a seamlessly looping SVG. SMIL only, no
JS: GitHub renders README images through a proxy that strips scripts, but SMIL
survives.

Design notes
------------
* The ball flies straight at the next brick and punches through it, bouncing
  only off the three walls. Re-aiming on every break guarantees the board
  always clears, and the sweep still reads as a ball bouncing around.
* Bricks are targeted in serpentine order, so the wipe sweeps left-to-right,
  right-to-left, ... across the board.
* The paddle is static and every descent is redirected onto the paddle centre,
  so the motion path starts and ends at the same point: the restart is
  invisible.
* SMIL `keyTimes` must start at 0 and END at 1, otherwise the animation is
  silently dropped вЂ” that is why the last keyframe is pinned to 1.

Fully deterministic: the same file is produced on every run.
"""
import math
from pathlib import Path

W, H = 1200, 340
OUT = Path(__file__).resolve().parent.parent / "assets" / "breakout.svg"

CYAN, VIOLET, PINK = "#7cf0ff", "#a78bfa", "#ff79c6"
ROW_COLORS = [PINK, VIOLET, CYAN, VIOLET]

PAD_L, PAD_R = 26.0, W - 26.0
PAD_T = 24.0
BALL_R = 5.0

COLS, ROWS = 12, 4
BRICK_W, BRICK_H = 80.0, 18.0
GAP_X, GAP_Y = 12.0, 10.0
GRID_W = COLS * BRICK_W + (COLS - 1) * GAP_X
GRID_X = (W - GRID_W) / 2
GRID_Y = 62.0

PADDLE_W, PADDLE_H = 168.0, 10.0
PADDLE_Y = H - 46.0
PADDLE_CX = W / 2

SPEED = 320.0
DT = 0.0006
MAX_T = 40.0


def brick_rect(col, row):
    x = GRID_X + col * (BRICK_W + GAP_X)
    y = GRID_Y + row * (BRICK_H + GAP_Y)
    return [x, y, x + BRICK_W, y + BRICK_H]


bricks = {(c, r): brick_rect(c, r) for r in range(ROWS) for c in range(COLS)}
alive = set(bricks)
hits = []

# serpentine order: bottom row first (closest to the paddle), alternating
order = []
for r in range(ROWS - 1, -1, -1):
    cols = range(COLS) if (ROWS - 1 - r) % 2 == 0 else range(COLS - 1, -1, -1)
    for c in cols:
        order.append((c, r))
order_pos = {k: i for i, k in enumerate(order)}


def next_target(px, py):
    """First living brick in serpentine order, preferring reachable ones."""
    cand = [k for k in alive]
    if not cand:
        return None
    cand.sort(key=lambda k: order_pos[k])
    return cand[0]


def centre(key):
    x0, y0, x1, y1 = bricks[key]
    return (x0 + x1) / 2, (y0 + y1) / 2


def simulate():
    """Fly straight at the next brick, bounce off the three walls, punch through
    bricks on contact. Re-aim on every brick break, so the board always clears."""
    px, py = PADDLE_CX, PADDLE_Y - BALL_R - 1
    pts = [(px, py)]
    t = 0.0
    target = next_target(px, py)
    tx, ty = centre(target)
    ang = math.atan2(ty - py, tx - px)
    guard = 0

    while target is not None and t < MAX_T and guard < 900000:
        guard += 1
        vx, vy = math.cos(ang) * SPEED, math.sin(ang) * SPEED
        nx, ny = px + vx * DT, py + vy * DT
        t += DT

        bounced = False
        if nx - BALL_R < PAD_L:
            nx = PAD_L + BALL_R
            ang = math.pi - ang
            bounced = True
        elif nx + BALL_R > PAD_R:
            nx = PAD_R - BALL_R
            ang = math.pi - ang
            bounced = True
        if ny - BALL_R < PAD_T:
            ny = PAD_T + BALL_R
            ang = -ang
            bounced = True
        if bounced:
            pts.append((px, py))
            nx, ny = px + math.cos(ang) * SPEED * DT, py + math.sin(ang) * SPEED * DT

        # bricks: break on contact, pass straight through
        hit = None
        for key in alive:
            x0, y0, x1, y1 = bricks[key]
            if x0 - BALL_R <= nx <= x1 + BALL_R and y0 - BALL_R <= ny <= y1 + BALL_R:
                hit = key
                break
        if hit is not None:
            alive.discard(hit)
            hits.append((t, hit))
            pts.append((nx, ny))
            target = next_target(nx, ny)
            if target is None:
                px, py = nx, ny
                break
            tx, ty = centre(target)
            ang = math.atan2(ty - ny, tx - nx)

        # descent: aim onto the paddle centre so the loop can close
        if math.sin(ang) > 0 and ny > PADDLE_Y - 150:
            dist = math.hypot(PADDLE_CX - nx, (PADDLE_Y - BALL_R) - ny)
            t += dist / SPEED
            pts.append((nx, ny))
            pts.append((PADDLE_CX, PADDLE_Y - BALL_R))
            px, py = PADDLE_CX, PADDLE_Y - BALL_R
            target = next_target(px, py)
            if target is None:
                break
            tx, ty = centre(target)
            ang = math.atan2(ty - py, tx - px)
            continue

        px, py = nx, ny

    # close the loop: return to the exact start point
    if abs(px - PADDLE_CX) > 0.5 or abs(py - (PADDLE_Y - BALL_R - 1)) > 0.5:
        dist = math.hypot(PADDLE_CX - px, (PADDLE_Y - BALL_R - 1) - py)
        t += dist / SPEED
        pts.append((px, py))
        pts.append((PADDLE_CX, PADDLE_Y - BALL_R - 1))

    return pts, hits, t


pts, hits, T = simulate()
T = round(T, 2)

clean = [pts[0]]
for p in pts[1:]:
    if abs(p[0] - clean[-1][0]) > 0.4 or abs(p[1] - clean[-1][1]) > 0.4:
        clean.append(p)
if abs(clean[-1][0] - clean[0][0]) > 0.4 or abs(clean[-1][1] - clean[0][1]) > 0.4:
    clean.append(clean[0])

path_d = f"M{clean[0][0]:.1f} {clean[0][1]:.1f}"
for x, y in clean[1:]:
    path_d += f" L{x:.1f} {y:.1f}"

hit_map = {}
for t_hit, key in hits:
    hit_map.setdefault(key, min(0.975, max(0.055, t_hit / T)))

# bricks cascade back in at the top of the loop, so the restart reads as the
# board reloading instead of everything snapping to full opacity at once
CASCADE = 0.042          # fraction of the loop spent rebuilding the board
FADE_IN = 0.012
brick_svg = []
for (col, row), (x0, y0, x1, y1) in bricks.items():
    color = ROW_COLORS[row % len(ROW_COLORS)]
    frac = hit_map.get((col, row), 1.0)
    # keyTimes[0] must be 0, so the first cascade slot needs a tiny offset to
    # stay strictly increasing
    f_in = round(max(0.002, order_pos[(col, row)] / len(order) * CASCADE), 4)
    f_on = round(min(f_in + FADE_IN, frac - 0.006), 4)
    f0 = round(max(f_on + 0.002, frac - 0.0025), 4)
    f1 = round(max(f0 + 0.001, frac), 4)
    f2 = round(min(0.998, f1 + 0.008), 4)
    # keyTimes MUST start at 0 and end at 1, otherwise SMIL drops the animation
    anim = (
        f'<animate attributeName="opacity" values="0;0;1;1;0.4;0;0" '
        f'keyTimes="0;{f_in};{f_on};{f0};{f1};{f2};1" dur="{T}s" repeatCount="indefinite"/>'
    )
    brick_svg.append(
        f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{BRICK_W:.0f}" height="{BRICK_H:.0f}" rx="4" '
        f'fill="{color}" fill-opacity="0.22" stroke="{color}" stroke-opacity="0.8" '
        f'stroke-width="1.1">{anim}</rect>'
    )

# ball + motion trail: same path, staggered starts, shrinking radius
trail = []
for i, (r, op) in enumerate([(4.2, 0.30), (3.6, 0.20), (3.0, 0.12)]):
    delay = round(-0.035 * (i + 1), 4)
    trail.append(
        f'<g><animateMotion dur="{T}s" begin="{delay}s" repeatCount="indefinite" '
        f'path="{path_d}"/>'
        f'<circle r="{r}" fill="{CYAN}" opacity="{op}"/></g>'
    )

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" fill="none" role="img" aria-label="self-playing neon breakout">
  <defs>
    <linearGradient id="gBg" x1="0" y1="0" x2="{W}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#05070d"/>
      <stop offset="0.5" stop-color="#080d1a"/>
      <stop offset="1" stop-color="#07060f"/>
    </linearGradient>
    <linearGradient id="gPaddle" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{CYAN}"/>
      <stop offset="0.5" stop-color="{VIOLET}"/>
      <stop offset="1" stop-color="{PINK}"/>
    </linearGradient>
    <radialGradient id="gBall"><stop offset="0" stop-color="#ffffff"/><stop offset="0.4" stop-color="{CYAN}"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
    <radialGradient id="gHalo"><stop offset="0" stop-color="{CYAN}" stop-opacity="0.9"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
    <radialGradient id="gVig" cx="0.5" cy="0.5" r="0.78">
      <stop offset="0.55" stop-color="#000000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0.55"/>
    </radialGradient>
    <pattern id="gGrid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M40 0H0v40" stroke="#ffffff" stroke-opacity="0.028" stroke-width="1"/>
    </pattern>
    <clipPath id="gFrame"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  </defs>

  <g clip-path="url(#gFrame)">
    <rect width="{W}" height="{H}" fill="url(#gBg)"/>
    <rect width="{W}" height="{H}" fill="url(#gGrid)"/>

    <g>
      {chr(10).join("      " + b for b in brick_svg)}
    </g>

    <line x1="{PAD_L + 40}" y1="{PADDLE_Y + 24}" x2="{PAD_R - 40}" y2="{PADDLE_Y + 24}" stroke="#ffffff" stroke-opacity="0.05"/>

    <rect x="{PADDLE_CX - PADDLE_W / 2:.1f}" y="{PADDLE_Y}" width="{PADDLE_W}" height="{PADDLE_H}" rx="5" fill="url(#gPaddle)" opacity="0.85"/>
    <rect x="{PADDLE_CX - PADDLE_W / 2:.1f}" y="{PADDLE_Y}" width="{PADDLE_W}" height="{PADDLE_H}" rx="5" fill="none" stroke="{CYAN}" stroke-opacity="0.55"/>

    <g>
      {chr(10).join("      " + tr for tr in trail)}
      <g>
        <animateMotion dur="{T}s" repeatCount="indefinite" path="{path_d}"/>
        <circle r="30" fill="url(#gHalo)" opacity="0.28"/>
        <circle r="12" fill="url(#gBall)" opacity="0.5"/>
        <circle r="{BALL_R}" fill="#ffffff"/>
      </g>
    </g>

    <rect width="{W}" height="{H}" fill="url(#gVig)"/>
  </g>

  <rect x="0.6" y="0.6" width="{W - 1.2}" height="{H - 1.2}" rx="19.4" stroke="#ffffff" stroke-opacity="0.09" stroke-width="1.2"/>
</svg>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")
print(
    f"written {OUT} ({OUT.stat().st_size} bytes) | loop {T}s | "
    f"cleared {len(hits)}/{COLS * ROWS} | path points {len(clean)}"
)
