#!/usr/bin/env python3
"""Generate an animated stats card (assets/stats.svg) for the profile README.

Only the Python standard library is used, so it runs on a bare ubuntu-latest
runner inside GitHub Actions.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER = os.environ.get("PROFILE_USER", "aeshtlv")
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "stats.svg"


def api(path: str, timeout: int = 25):
    req = urllib.request.Request(f"{API}{path}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", f"{USER}-profile-stats")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def safe(path: str, default):
    try:
        return api(path)
    except Exception as exc:  # noqa: BLE001 - stats are best effort
        print(f"warn: {path} -> {exc}", file=sys.stderr)
        return default


def collect() -> dict:
    user = safe(f"/users/{USER}", {}) or {}
    repos: list[dict] = []
    page = 1
    while page <= 5:
        chunk = safe(
            f"/users/{USER}/repos?per_page=100&page={page}&sort=pushed&type=owner", []
        )
        if not isinstance(chunk, list) or not chunk:
            break
        repos.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1

    owned = [r for r in repos if not r.get("fork")]
    stars = sum(int(r.get("stargazers_count") or 0) for r in repos)
    forks = sum(int(r.get("forks_count") or 0) for r in repos)

    langs: dict[str, int] = {}
    for repo in owned:
        name = repo.get("name")
        if not name:
            continue
        data = safe(f"/repos/{USER}/{name}/languages", {}) or {}
        if isinstance(data, dict):
            for lang, size in data.items():
                langs[lang] = langs.get(lang, 0) + int(size or 0)

    commits = safe(f"/search/commits?q=author:{USER}&per_page=1", {}) or {}
    commit_count = int(commits.get("total_count") or 0)

    top_langs = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:5]
    total_bytes = sum(size for _, size in top_langs) or 1

    return {
        "followers": int(user.get("followers") or 0),
        "repos": int(user.get("public_repos") or 0),
        "stars": stars,
        "forks": forks,
        "commits": commit_count,
        "langs": [
            {"name": name, "share": size / total_bytes}
            for name, size in top_langs
        ],
        "generated": datetime.now(timezone.utc).strftime("%d.%m.%Y"),
    }


LANG_COLORS = {
    "Python": ("#7cf0ff", "#3b82f6"),
    "TypeScript": ("#7cf0ff", "#a78bfa"),
    "JavaScript": ("#fde68a", "#f59e0b"),
    "HTML": ("#ffb4a2", "#ef4444"),
    "CSS": ("#a5b4fc", "#6366f1"),
    "Shell": ("#86efac", "#22c55e"),
    "C++": ("#93c5fd", "#2563eb"),
    "C": ("#cbd5e1", "#64748b"),
    "Batchfile": ("#e2e8f0", "#94a3b8"),
    "Dockerfile": ("#93c5fd", "#1d4ed8"),
}


def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_svg(data: dict) -> str:
    tiles = [
        ("подписчики", data["followers"], "👥"),
        ("репозитории", data["repos"], "📦"),
        ("звёзды", data["stars"], "⭐"),
        ("коммиты", data["commits"], "💾"),
    ]

    parts: list[str] = []
    parts.append(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 340" width="1200" height="340" fill="none" role="img" aria-label="статистика профиля">
  <defs>
    <linearGradient id="sbg" x1="0" y1="0" x2="1200" y2="340" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#070a12"/>
      <stop offset="1" stop-color="#0b0814"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#7cf0ff"/>
      <stop offset="1" stop-color="#a78bfa"/>
    </linearGradient>
    <linearGradient id="shine" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0"/>
      <stop offset="0.5" stop-color="#ffffff" stop-opacity="0.22"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
    <pattern id="sgrid" width="48" height="48" patternUnits="userSpaceOnUse">
      <path d="M48 0H0v48" stroke="#ffffff" stroke-opacity="0.04" stroke-width="1"/>
    </pattern>
    <clipPath id="sframe"><rect width="1200" height="340" rx="20"/></clipPath>
  </defs>

  <style>
    @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulseDot { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
    @keyframes drift { 0%, 100% { transform: translateX(0); } 50% { transform: translateX(26px); } }
    .tile { animation: fadeUp .9s ease-out both; }
    .dot { animation: pulseDot 2.6s ease-in-out infinite; }
    #sheen { animation: drift 9s ease-in-out infinite; }
  </style>

  <g clip-path="url(#sframe)">
    <rect width="1200" height="340" fill="url(#sbg)"/>
    <rect width="1200" height="340" fill="url(#sgrid)"/>
"""
    )

    # tiles 2x2 on the left
    for i, (label, value, icon) in enumerate(tiles):
        col, row = i % 2, i // 2
        x = 40 + col * 300
        y = 62 + row * 128
        delay = 0.08 * i
        parts.append(
            f"""    <g class="tile" style="animation-delay:{delay}s">
      <rect x="{x}" y="{y}" width="280" height="112" rx="16" fill="#0f1526" fill-opacity="0.92" stroke="#ffffff" stroke-opacity="0.08"/>
      <rect x="{x}" y="{y}" width="280" height="112" rx="16" fill="none" stroke="url(#accent)" stroke-opacity="0.28"/>
      <text x="{x + 22}" y="{y + 34}" font-family="'Segoe UI',system-ui,-apple-system,sans-serif" font-size="13" fill="#7d8ba6" letter-spacing="1.1">{esc(label).upper()}</text>
      <text x="{x + 22}" y="{y + 86}" font-family="'Segoe UI',system-ui,-apple-system,sans-serif" font-size="42" font-weight="700" fill="#e8eefb">{esc(value)}</text>
      <text x="{x + 258}" y="{y + 86}" text-anchor="end" font-size="26">{esc(icon)}</text>
    </g>
"""
        )

    # languages panel
    parts.append(
        """    <g class="tile" style="animation-delay:.34s">
      <rect x="660" y="62" width="500" height="240" rx="16" fill="#0f1526" fill-opacity="0.92" stroke="#ffffff" stroke-opacity="0.08"/>
      <rect x="660" y="62" width="500" height="240" rx="16" fill="none" stroke="url(#accent)" stroke-opacity="0.28"/>
      <text x="684" y="96" font-family="'Segoe UI',system-ui,-apple-system,sans-serif" font-size="13" fill="#7d8ba6" letter-spacing="1.1">ТОП ЯЗЫКОВ</text>
"""
    )

    for i, lang in enumerate(data["langs"]):
        y = 126 + i * 36
        width = max(8.0, round(lang["share"] * 452, 1))
        c1, c2 = LANG_COLORS.get(lang["name"], ("#7cf0ff", "#a78bfa"))
        parts.append(
            f"""      <text x="684" y="{y}" font-family="'Segoe UI',system-ui,-apple-system,sans-serif" font-size="14" fill="#c9d4e6">{esc(lang["name"])}</text>
      <text x="1136" y="{y}" text-anchor="end" font-family="ui-monospace,Consolas,monospace" font-size="13" fill="#7d8ba6">{lang["share"] * 100:.0f}%</text>
      <rect x="684" y="{y + 7}" width="452" height="7" rx="3.5" fill="#ffffff" fill-opacity="0.06"/>
      <rect x="684" y="{y + 7}" width="0" height="7" rx="3.5" fill="{c1}">
        <animate attributeName="width" from="0" to="{width}" dur="1.4s" begin="{0.5 + i * 0.12:.2f}s" fill="freeze" calcMode="spline" keySplines="0.22 1 0.36 1" keyTimes="0;1"/>
      </rect>
      <rect x="684" y="{y + 7}" width="0" height="7" rx="3.5" fill="{c2}" fill-opacity="0.55">
        <animate attributeName="width" from="0" to="{width}" dur="1.4s" begin="{0.5 + i * 0.12:.2f}s" fill="freeze" calcMode="spline" keySplines="0.22 1 0.36 1" keyTimes="0;1"/>
      </rect>
"""
        )

    parts.append(
        f"""      <rect id="sheen" x="684" y="118" width="120" height="150" fill="url(#shine)" opacity="0.16"/>
    </g>

    <circle class="dot" cx="40" cy="30" r="3.5" fill="#7cf0ff"/>
    <text x="54" y="35" font-family="'Segoe UI',system-ui,-apple-system,sans-serif" font-size="12.5" fill="#6f7d96" letter-spacing="0.6">обновлено {esc(data["generated"])} · github actions</text>

    <rect x="380" y="316" width="440" height="1.4" rx="1" fill="url(#accent)" fill-opacity="0.45"/>
  </g>

  <rect x="0.6" y="0.6" width="1198.8" height="338.8" rx="19.4" stroke="#ffffff" stroke-opacity="0.09" stroke-width="1.2"/>
</svg>
"""
    )

    return "".join(parts)


def main() -> int:
    data = collect()
    svg = build_svg(data)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(
        "stats: followers=%s repos=%s stars=%s commits=%s langs=%s"
        % (
            data["followers"],
            data["repos"],
            data["stars"],
            data["commits"],
            ", ".join(f"{l['name']}:{l['share'] * 100:.0f}%" for l in data["langs"]),
        )
    )
    print(f"written -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
