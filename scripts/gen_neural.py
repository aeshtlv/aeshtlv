#!/usr/bin/env python3
"""Generate assets/neural.svg — a living neural network that fires in waves.

A small layered graph is laid out once, then a signal wave is baked into the
SVG with SMIL only (GitHub strips scripts from README images, but SMIL
animations inside a plain SVG survive the camo proxy).

How the loop works
------------------
* Every edge carries one pulse per cycle. The pulse travels from the source
  node to the target node during its own keyframe window, then vanishes.
* Pulse windows are staggered by layer, so a wave sweeps left to right through
  the network instead of everything blinking at once.
* A node lights up for exactly the window in which its incoming signals land.
* A few recurrent edges curve back underneath from the last layer to the first,
  so the signal returns just as the next wave starts — the card is never dead.
* Every animated element is back at its t=0 state at t=T, so the loop is
  seamless: no snap, no flicker on restart.

SMIL gotchas baked into the generator
-------------------------------------
* `keyTimes` must start at 0 and END at 1, and be strictly increasing —
  otherwise the animation is silently dropped.
* `animateMotion` ignores `keyPoints`/`keyTimes` unless `calcMode="linear"`.
* `keyPoints` must have exactly as many entries as `keyTimes`.

Deterministic: the same seed always produces the same file.
"""
import random
from pathlib import Path

W, H = 1200, 340
OUT = Path(__file__).resolve().parent.parent / "assets" / "neural.svg"

SEED = 20261029
T = 6.5  # loop length, seconds

CYAN, VIOLET, PINK = "#7cf0ff", "#a78bfa", "#ff79c6"
LAYER_COLORS = [CYAN, CYAN, VIOLET, VIOLET, PINK]
GRAD_FOR = {CYAN: "pC", VIOLET: "pV", PINK: "pP"}
HALO_FOR = {CYAN: "haloC", VIOLET: "haloV", PINK: "haloP"}

rng = random.Random(SEED)

# --- layout ---------------------------------------------------------------
LAYERS = [(80, 5), (340, 8), (600, 10), (860, 7), (1120, 4)]
TOP, BOT = 62.0, 274.0

nodes = []
for li, (x, n) in enumerate(LAYERS):
    span = BOT - TOP
    gap = span / (n - 1) if n > 1 else 0.0
    jit = min(9.0, gap * 0.28)
    col = []
    for i in range(n):
        y = TOP + gap * i if n > 1 else (TOP + BOT) / 2
        col.append(
            (round(x + rng.uniform(-11, 11), 1), round(y + rng.uniform(-jit, jit), 1))
        )
    nodes.append(col)

# --- forward edges --------------------------------------------------------
edges = []
for li in range(len(LAYERS) - 1):
    src, dst = nodes[li], nodes[li + 1]
    k = 3 if li < 2 else 2
    covered = set()
    for i, (x1, y1) in enumerate(src):
        cand = sorted(
            range(len(dst)),
            key=lambda j: abs(dst[j][1] - y1) + rng.uniform(0, 120),
        )
        for j in cand[:k]:
            edges.append((li, i, li + 1, j))
            covered.add(j)
    # every node needs at least one incoming signal
    for j in range(len(dst)):
        if j not in covered:
            i = min(range(len(src)), key=lambda i: abs(src[i][1] - dst[j][1]))
            edges.append((li, i, li + 1, j))

# --- recurrent edges: last layer curves back under to the first -----------
feedback = []
for j in rng.sample(range(len(nodes[-1])), len(nodes[-1])):
    i = rng.randrange(len(nodes[0]))
    x1, y1 = nodes[-1][j]
    x2, y2 = nodes[0][i]
    dip = round(max(y1, y2) + rng.uniform(50, 76), 1)
    d = f"M{x1} {y1}C{x1} {dip} {x2} {dip} {x2} {y2}"
    # staggered so the signal trickles home across the whole gap between waves
    f0 = round(rng.uniform(0.66, 0.86), 4)
    f1 = round(min(0.985, f0 + rng.uniform(0.11, 0.15)), 4)
    feedback.append((d, f0, f1))

# --- timing ---------------------------------------------------------------
layer_start = [0.05 + li * 0.155 for li in range(len(LAYERS))]
# 0.050, 0.205, 0.360, 0.515, 0.670  -> wave clears the board by ~0.80,
# then the recurrent edges carry the signal home during 0.70..0.95

edge_time = {}
for (li, i, lj, j) in edges:
    f0 = layer_start[li] + rng.uniform(0.0, 0.035)
    f1 = f0 + (layer_start[lj] - layer_start[li]) * rng.uniform(0.72, 1.0)
    edge_time[(li, i, lj, j)] = (round(f0, 4), round(f1, 4))

# node light-up window = span of its incoming signals
node_window = {}
for li in range(len(LAYERS)):
    for i in range(len(nodes[li])):
        incoming = [edge_time[e] for e in edges if e[2] == li and e[3] == i]
        if not incoming:
            outgoing = [edge_time[e] for e in edges if e[0] == li and e[1] == i]
            if outgoing:
                start = min(f for f, _ in outgoing)
                node_window[(li, i)] = (start, start + 0.05)
            else:
                node_window[(li, i)] = (layer_start[li], layer_start[li] + 0.05)
        else:
            node_window[(li, i)] = (
                min(f for f, _ in incoming),
                max(t for _, t in incoming),
            )


def window_keys(f0, f1, pad=0.008):
    """Build a strictly increasing keyTimes list: 0, f0, f0+, f1-, f1, 1."""
    f0 = max(0.002, min(f0, 0.955))
    f1 = max(f0 + 0.03, min(f1, 0.985))
    fa = f0 + pad
    fb = max(fa + 0.012, f1 - pad)
    fb = min(fb, 0.99)
    return f"0;{f0:.4f};{fa:.4f};{fb:.4f};{f1:.4f};1", f0, f1


# --- edges ----------------------------------------------------------------
# Every edge streams data continuously (travelling dashes), and the periodic
# wave brightens the edges it passes through. The stream keeps the card alive
# during the gap between waves instead of leaving it frozen.
DASH, GAP_ = 3, 11
PERIOD = DASH + GAP_
FLOW_DUR = round(T / 8, 4)  # divides T, so the dash stream loops seamlessly

edge_svg = []
for (li, i, lj, j) in edges:
    x1, y1 = nodes[li][i]
    x2, y2 = nodes[lj][j]
    col = LAYER_COLORS[li]
    f0, f1 = edge_time[(li, i, lj, j)]
    kt, _, _ = window_keys(f0, f1)
    edge_svg.append(
        f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{col}" stroke-width="1.15" '
        f'stroke-opacity="0.30" stroke-dasharray="{DASH} {GAP_}" stroke-linecap="round">'
        f'<animate attributeName="stroke-dashoffset" values="0;-{PERIOD}" '
        f'dur="{FLOW_DUR}s" repeatCount="indefinite"/>'
        f'<animate attributeName="stroke-opacity" values="0.30;0.30;1;1;0.30;0.30" '
        f'keyTimes="{kt}" dur="{T}s" repeatCount="indefinite"/>'
        f"</path>"
    )

for (d, f0, f1) in feedback:
    kt, _, _ = window_keys(f0, f1)
    edge_svg.append(
        f'<path d="{d}" stroke="{CYAN}" stroke-width="1.1" stroke-opacity="0.17" '
        f'stroke-dasharray="{DASH} {GAP_}" stroke-linecap="round">'
        f'<animate attributeName="stroke-dashoffset" values="0;-{PERIOD}" '
        f'dur="{FLOW_DUR}s" repeatCount="indefinite"/>'
        f'<animate attributeName="stroke-opacity" values="0.17;0.17;0.78;0.78;0.17;0.17" '
        f'keyTimes="{kt}" dur="{T}s" repeatCount="indefinite"/>'
        f"</path>"
    )

# --- pulses ---------------------------------------------------------------
pulse_svg = []
for (li, i, lj, j) in edges:
    x1, y1 = nodes[li][i]
    x2, y2 = nodes[lj][j]
    grad = GRAD_FOR[LAYER_COLORS[li]]
    f0, f1 = edge_time[(li, i, lj, j)]
    kt, f0, f1 = window_keys(f0, f1)
    pulse_svg.append(
        f'<g><animateMotion dur="{T}s" repeatCount="indefinite" calcMode="linear" '
        f'keyPoints="0;0;1;1" keyTimes="0;{f0:.4f};{f1:.4f};1" '
        f'path="M{x1} {y1}L{x2} {y2}"/>'
        f'<circle r="10" fill="url(#{grad})">'
        f'<animate attributeName="opacity" values="0;0;1;1;0;0" '
        f'keyTimes="{kt}" dur="{T}s" repeatCount="indefinite"/>'
        f"</circle></g>"
    )

for (d, f0, f1) in feedback:
    kt, f0, f1 = window_keys(f0, f1)
    pulse_svg.append(
        f'<g><animateMotion dur="{T}s" repeatCount="indefinite" calcMode="linear" '
        f'keyPoints="0;0;1;1" keyTimes="0;{f0:.4f};{f1:.4f};1" path="{d}"/>'
        f'<circle r="8" fill="url(#pC)">'
        f'<animate attributeName="opacity" values="0;0;1;1;0;0" '
        f'keyTimes="{kt}" dur="{T}s" repeatCount="indefinite"/>'
        f"</circle></g>"
    )

# --- nodes ----------------------------------------------------------------
node_svg = []
for li in range(len(LAYERS)):
    col = LAYER_COLORS[li]
    for i, (x, y) in enumerate(nodes[li]):
        f0, f1 = node_window[(li, i)]
        kt, _, _ = window_keys(f0, f1, pad=0.010)
        breathe = round(-rng.uniform(0, T), 2)
        node_svg.append(
            f'<g transform="translate({x} {y})">'
            f'<circle r="23" fill="url(#{HALO_FOR[col]})">'
            f'<animate attributeName="opacity" values="0.24;0.24;0.95;0.95;0.24;0.24" '
            f'keyTimes="{kt}" dur="{T}s" repeatCount="indefinite"/>'
            f"</circle>"
            f'<circle r="5.0" fill="{col}">'
            f'<animate attributeName="opacity" values="0.7;0.7;1;1;0.7;0.7" '
            f'keyTimes="{kt}" dur="{T}s" repeatCount="indefinite"/>'
            f"</circle>"
            f'<circle r="2.1" fill="#ffffff">'
            f'<animate attributeName="opacity" values="0.35;0.35;1;1;0.35;0.35" '
            f'keyTimes="{kt}" dur="{T}s" repeatCount="indefinite"/>'
            f"</circle>"
            # slow independent breathing keeps the network alive between waves
            f'<circle r="12" fill="none" stroke="{col}" stroke-width="1">'
            f'<animate attributeName="opacity" values="0;0.34;0" keyTimes="0;0.5;1" '
            f'dur="{T}s" begin="{breathe}s" repeatCount="indefinite"/>'
            f"</circle>"
            f"</g>"
        )

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" fill="none" role="img" aria-label="living neural network">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="{W}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#05070d"/>
      <stop offset="0.5" stop-color="#080d1a"/>
      <stop offset="1" stop-color="#07060f"/>
    </linearGradient>

    <radialGradient id="pC"><stop offset="0" stop-color="#ffffff"/><stop offset="0.28" stop-color="{CYAN}"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
    <radialGradient id="pV"><stop offset="0" stop-color="#ffffff"/><stop offset="0.28" stop-color="{VIOLET}"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
    <radialGradient id="pP"><stop offset="0" stop-color="#ffffff"/><stop offset="0.28" stop-color="{PINK}"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>

    <radialGradient id="haloC"><stop offset="0" stop-color="{CYAN}" stop-opacity="0.85"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
    <radialGradient id="haloV"><stop offset="0" stop-color="{VIOLET}" stop-opacity="0.85"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
    <radialGradient id="haloP"><stop offset="0" stop-color="{PINK}" stop-opacity="0.85"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>

    <radialGradient id="coreGlow"><stop offset="0" stop-color="{VIOLET}" stop-opacity="0.34"/><stop offset="0.55" stop-color="{CYAN}" stop-opacity="0.13"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>

    <radialGradient id="vig" cx="0.5" cy="0.5" r="0.8">
      <stop offset="0.55" stop-color="#000000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0.42"/>
    </radialGradient>

    <pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="1" fill="#ffffff" fill-opacity="0.05"/>
    </pattern>

    <clipPath id="frame"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  </defs>

  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    <rect width="{W}" height="{H}" fill="url(#dots)"/>

    <ellipse cx="600" cy="168" rx="540" ry="165" fill="url(#coreGlow)">
      <animate attributeName="opacity" values="0.75;1;0.75" keyTimes="0;0.5;1" dur="{T}s" repeatCount="indefinite"/>
    </ellipse>

    <g>
      {chr(10).join("      " + e for e in edge_svg)}
    </g>

    <g>
      {chr(10).join("      " + p for p in pulse_svg)}
    </g>

    <g>
      {chr(10).join("      " + n for n in node_svg)}
    </g>

    <rect width="{W}" height="{H}" fill="url(#vig)"/>
  </g>

  <rect x="0.6" y="0.6" width="{W - 1.2}" height="{H - 1.2}" rx="19.4" stroke="#ffffff" stroke-opacity="0.09" stroke-width="1.2"/>
</svg>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")
total_nodes = sum(n for _, n in LAYERS)
print(
    f"written {OUT} ({OUT.stat().st_size} bytes) | loop {T}s | "
    f"{len(edges)} forward + {len(feedback)} recurrent edges | "
    f"{total_nodes} nodes | {len(pulse_svg)} pulses"
)
