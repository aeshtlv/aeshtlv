#!/usr/bin/env python3
"""Generate assets/gitlog.svg — a scrolling git log card.

The commit list is real: it was pulled once from the GitHub API for aeshtlv's
repositories and is baked in here so the card stays deterministic and needs no
token at render time. Refresh the list by re-running the fetch and editing
COMMITS.

The scroll is seamless: the list is rendered twice and translated up by exactly
one list height, so the second copy lands where the first started.
"""
from pathlib import Path

W, H = 1200, 240
OUT = Path(__file__).resolve().parent.parent / "assets" / "gitlog.svg"

HEADER_H = 38
LINE_H = 32
PAD_L = 46
FONT = 15

# real commits, newest first (repo: aeshtlv/*)
COMMITS = [
    ("dfee86d", "Serve assets under a content hash, cache them for a year"),
    ("31979de", "Match the preview card's mesh to the page"),
    ("321c1b5", "Draw the hero grid as one even mesh"),
    ("0165659", "Strengthen the hero grid and rework the link preview"),
    ("61c5be6", "Serve the site over HTTP/2"),
    ("c668176", "Version the server config and the deployment check"),
    ("bcf4457", "Add inline buttons to the user handlers"),
    ("120dd9f", "Refine user response messages"),
    ("4a68a70", "Drop the redundant confirmation message"),
    ("5056cc7", "Improve user message responses"),
    ("4aadbbf", "Pin messages directly instead of forwarding"),
    ("271c687", "Limit the ticket query"),
    ("609d131", "Refactor language handling in the i18n middleware"),
    ("1343d41", "Update the referral service and localization"),
    ("76e0a2d", "Refactor JsonI18n to use a private attribute"),
    ("b1d83e5", "Refactor subscription handling and logging"),
]

LIST_H = len(COMMITS) * LINE_H
DUR = round(LIST_H / 20.0, 1)  # ~20 px per second, calm scroll


def line_svg(row, sha, msg):
    y = HEADER_H + row * LINE_H + 21
    return (
        f'<text x="{PAD_L}" y="{y}" fill="#7cf0ff" fill-opacity="0.55" '
        f'font-size="{FONT}">{sha}</text>'
        f'<text x="{PAD_L + 82}" y="{y}" fill="#9aa6b8" font-size="{FONT}">{msg}</text>'
    )


body = []
for pass_no in (0, 1):
    for i, (sha, msg) in enumerate(COMMITS):
        # the second copy must sit exactly one list-height below the first,
        # otherwise the viewport runs out of text at the end of the loop
        body.append(line_svg(pass_no * len(COMMITS) + i, sha, msg))

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" fill="none" role="img" aria-label="recent commits">
  <title>deadera@macbook — git log</title>
  <defs>
    <linearGradient id="winBg" x1="0" y1="0" x2="0" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#0a0f1a"/>
      <stop offset="1" stop-color="#0b0a14"/>
    </linearGradient>
    <linearGradient id="barBg" x1="0" y1="0" x2="0" y2="{HEADER_H}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#121a2b"/>
      <stop offset="1" stop-color="#13111f"/>
    </linearGradient>
    <linearGradient id="fadeTop" x1="0" y1="{HEADER_H}" x2="0" y2="{HEADER_H + 26}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#0a0f1a" stop-opacity="1"/>
      <stop offset="1" stop-color="#0a0f1a" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="fadeBot" x1="0" y1="{H - 34}" x2="0" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#0b0a14" stop-opacity="0"/>
      <stop offset="1" stop-color="#0b0a14" stop-opacity="1"/>
    </linearGradient>
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="20"/></clipPath>
    <clipPath id="viewport"><rect x="0" y="{HEADER_H}" width="{W}" height="{H - HEADER_H}"/></clipPath>
  </defs>

  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="url(#winBg)"/>

    <path d="M0 20a20 20 0 0 1 20-20h1160a20 20 0 0 1 20 20v18H0z" fill="url(#barBg)"/>
    <rect x="0" y="37" width="{W}" height="1" fill="#ffffff" fill-opacity="0.07"/>
    <circle cx="34" cy="19" r="6" fill="#ff5f57"/>
    <circle cx="56" cy="19" r="6" fill="#febc2e"/>
    <circle cx="78" cy="19" r="6" fill="#28c840"/>
    <text x="600" y="24" text-anchor="middle" font-family="ui-monospace,SFMono-Regular,'Segoe UI',monospace" font-size="12.5" fill="#6b7b96">deadera@macbook — git log</text>

    <g clip-path="url(#viewport)" font-family="ui-monospace,SFMono-Regular,Consolas,'Courier New',monospace">
      <g>
        <animateTransform attributeName="transform" type="translate"
          values="0 0;0 -{LIST_H}" dur="{DUR}s" repeatCount="indefinite"/>
        {chr(10).join("        " + b for b in body)}
      </g>
    </g>

    <rect x="0" y="{HEADER_H}" width="{W}" height="26" fill="url(#fadeTop)"/>
    <rect x="0" y="{H - 34}" width="{W}" height="34" fill="url(#fadeBot)"/>
  </g>

  <rect x="0.6" y="0.6" width="{W - 1.2}" height="{H - 1.2}" rx="19.4" stroke="#ffffff" stroke-opacity="0.09" stroke-width="1.2"/>
</svg>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding="utf-8")
print(f"written {OUT} ({OUT.stat().st_size} bytes) | {len(COMMITS)} commits | loop {DUR}s")
