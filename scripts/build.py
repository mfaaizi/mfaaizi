#!/usr/bin/env python3
"""Builds the SVG cards and the project grid in README.md from data/profile.json.

Usage:  python scripts/build.py
Add a project: append an entry to "projects" in data/profile.json and re-run
(or just push; the GitHub Action does it for you).
"""
import html
import json
import pathlib
import re
import textwrap
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
CARDS = ROOT / "cards"
DATA = json.loads((ROOT / "data" / "profile.json").read_text(encoding="utf-8"))

BG1, BG2, BORDER = "#0d1117", "#0f1b2d", "#21314d"
ACCENT, TEXT, MUTED = "#58a6ff", "#e6edf3", "#8b949e"
STATUS = {"shipped": "#3fb950", "building": "#f0883e", "planned": "#a371f7"}
SANS = "'Segoe UI', -apple-system, Helvetica, Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', monospace"


def svg(w, h, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{BG1}"/><stop offset="1" stop-color="{BG2}"/></linearGradient></defs>'
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="url(#bg)" stroke="{BORDER}"/>'
        f"{body}</svg>"
    )


def text(x, y, s, size=14, fill=TEXT, weight="400", font=SANS, anchor="start", extra=""):
    return (
        f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}" {extra}>{escape(s)}</text>'
    )


def chip(x, y, label, color=ACCENT, size=11):
    w = round(len(label) * size * 0.6 + 18)
    s = (
        f'<rect x="{x}" y="{y}" width="{w}" height="22" rx="11" fill="none" stroke="{color}" stroke-opacity="0.55"/>'
        + text(x + w / 2, y + 15, label, size, color, anchor="middle")
    )
    return s, w


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def hero():
    p = DATA["profile"]
    b = "".join(f'<circle cx="{26 + i * 18}" cy="26" r="5.5" fill="{c}"/>' for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")))
    b += text(100, 30, f'{p["handle"]}@github ~ $ whoami', 12, MUTED, font=MONO)
    b += text(36, 100, p["name"], 46, TEXT, "700")
    b += text(36, 134, p["role"], 18, ACCENT, "600")
    b += text(36, 162, p["tagline"], 14, MUTED)
    x = 36
    for label in p["chips"]:
        s, w = chip(x, 184, label)
        b += s
        x += w + 8
    return svg(830, 232, b)


def stat(item):
    b = f'<rect x="0" y="22" width="4" height="76" rx="2" fill="{ACCENT}"/>'
    b += text(24, 38, item["label"], 12, ACCENT, "700", MONO, extra='letter-spacing="2"')
    b += text(24, 72, item["value"], 24, TEXT, "700")
    b += text(24, 96, item["sub"], 12, MUTED)
    return svg(270, 120, b)


def title(label):
    b = text(8, 34, label, 22, TEXT, "700")
    b += f'<rect x="8" y="44" width="48" height="3" rx="1.5" fill="{ACCENT}"/>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="830" height="56" viewBox="0 0 830 56" role="img">{b}</svg>'
    )


def project(p):
    color = STATUS.get(p.get("status", "shipped"), ACCENT)
    b = f'<circle cx="26" cy="29" r="4.5" fill="{color}"/>'
    b += text(38, 33, p.get("status", "shipped").upper(), 10, color, "700", MONO, extra='letter-spacing="1.5"')
    b += text(20, 66, p["name"], 18, TEXT, "700")
    lines = textwrap.wrap(p["desc"], 36)[:4]
    for i, ln in enumerate(lines):
        b += text(20, 92 + i * 18, ln, 12.5, MUTED)
    x = 20
    for t in p.get("tags", []):
        s, w = chip(x, 168, t, ACCENT, 10)
        if x + w > 250:
            break
        b += s
        x += w + 6
    return svg(270, 204, b)


def projects_block():
    imgs = []
    for p in DATA["projects"]:
        img = f'<img src="cards/project-{slug(p["name"])}.svg" width="270" alt="{html.escape(p["name"], quote=True)}">'
        if p.get("repo"):
            img = f'<a href="https://github.com/{DATA["profile"]["handle"]}/{p["repo"]}">{img}</a>'
        imgs.append(img)
    rows = ["<p align=\"center\">\n" + "\n".join(imgs[i:i + 3]) + "\n</p>" for i in range(0, len(imgs), 3)]
    return "\n".join(rows)


def main():
    CARDS.mkdir(exist_ok=True)
    (CARDS / "hero.svg").write_text(hero(), encoding="utf-8")
    for i, item in enumerate(DATA["stats"], 1):
        (CARDS / f"stat-{i}.svg").write_text(stat(item), encoding="utf-8")
    (CARDS / "title-projects.svg").write_text(title(DATA["section_title"]), encoding="utf-8")
    for old in CARDS.glob("project-*.svg"):
        old.unlink()
    for p in DATA["projects"]:
        (CARDS / f"project-{slug(p['name'])}.svg").write_text(project(p), encoding="utf-8")

    readme = ROOT / "README.md"
    src = readme.read_text(encoding="utf-8")
    block = f"<!-- PROJECTS:START -->\n{projects_block()}\n<!-- PROJECTS:END -->"
    new, n = re.subn(r"<!-- PROJECTS:START -->.*?<!-- PROJECTS:END -->", lambda _: block, src, flags=re.S)
    if n != 1:
        raise SystemExit("README.md needs one PROJECTS:START / PROJECTS:END marker pair")
    readme.write_text(new, encoding="utf-8")
    print(f"built {len(DATA['projects'])} project cards")


if __name__ == "__main__":
    main()
