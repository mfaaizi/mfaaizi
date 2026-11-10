#!/usr/bin/env python3
"""Builds cards/heatmap.svg and cards/activity.svg from your real GitHub contributions.

Env:  GH_TOKEN (token with read access), GH_USER (defaults to profile handle)
Flags: --demo   use fake data (for a local preview only)
       --out    output folder (default: cards/)
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import random
import urllib.request

from build import ACCENT, BORDER, MONO, MUTED, ROOT, SANS, TEXT, svg, text, DATA

RAMP = ["#161b22", "#12335c", "#1f5fa8", "#388bfd", "#79c0ff"]
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload or not payload["data"]["user"]:
        raise SystemExit(f"GitHub API error: {payload.get('errors') or 'user not found'}")
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[(d["date"], d["contributionCount"], LEVELS[d["contributionLevel"]]) for d in w["contributionDays"]] for w in cal]


def demo_weeks():
    random.seed(7)
    today = dt.date.today()
    d = today - dt.timedelta(days=364)
    d -= dt.timedelta(days=(d.weekday() + 1) % 7)
    weeks = []
    while d <= today:
        week = []
        for _ in range(7):
            if d <= today:
                n = 0 if random.random() < 0.35 else random.randint(1, 14)
                lvl = 0 if n == 0 else 1 if n <= 3 else 2 if n <= 6 else 3 if n <= 10 else 4
                week.append((d.isoformat(), n, lvl))
            d += dt.timedelta(days=1)
        weeks.append(week)
    return weeks


def heatmap(weeks):
    total = sum(c for w in weeks for _, c, _ in w)
    b = text(24, 32, "$ ./contributions.sh", 12, MUTED, font=MONO)
    b += text(806, 32, f"{total:,} contributions in the last year", 12, ACCENT, "600", anchor="end")
    x0, y0, step = 24, 66, 15
    prev = None
    for i, w in enumerate(weeks):
        m = dt.date.fromisoformat(w[0][0]).strftime("%b")
        if m != prev:
            b += text(x0 + i * step, 58, m, 10, MUTED)
            prev = m
        for j, (_, _, lvl) in enumerate(w):
            b += f'<rect x="{x0 + i * step}" y="{y0 + j * step}" width="12" height="12" rx="2.5" fill="{RAMP[lvl]}"/>'
    lx = 806 - 5 * 15 - 60
    b += text(lx, 188, "Less", 10, MUTED)
    for k, c in enumerate(RAMP):
        b += f'<rect x="{lx + 30 + k * 15}" y="178" width="12" height="12" rx="2.5" fill="{c}"/>'
    b += text(lx + 30 + 5 * 15 + 4, 188, "More", 10, MUTED)
    return svg(830, 204, b)


def activity(weeks):
    days = sorted((d for w in weeks for d in w), key=lambda t: t[0])
    months = {}
    for date, c, _ in days:
        months[date[:7]] = months.get(date[:7], 0) + c
    keys = list(months)[-12:]
    mx = max([months[k] for k in keys] + [1])
    b = text(24, 32, "$ ./activity.sh", 12, MUTED, font=MONO)
    for i, k in enumerate(keys):
        h = max(3, round(months[k] / mx * 90))
        x = 28 + i * 44
        b += f'<rect x="{x}" y="{150 - h}" width="30" height="{h}" rx="4" fill="{ACCENT}" fill-opacity="{0.35 + 0.65 * months[k] / mx:.2f}"/>'
        b += text(x + 15, 146 - h, str(months[k]), 10, TEXT, anchor="middle")
        b += text(x + 15, 168, dt.date.fromisoformat(k + "-01").strftime("%b"), 10, MUTED, anchor="middle")
    longest = run = 0
    for _, c, _ in days:
        run = run + 1 if c else 0
        longest = max(longest, run)
    cur, seq = 0, days[:]
    if seq and seq[-1][1] == 0:
        seq = seq[:-1]
    for _, c, _ in reversed(seq):
        if not c:
            break
        cur += 1
    best = max(days, key=lambda t: t[1])
    best_label = f"{best[1]} on " + dt.date.fromisoformat(best[0]).strftime("%b %d")
    unit = lambda n: f"{n} day" + ("" if n == 1 else "s")
    stats = [("CURRENT STREAK", unit(cur)), ("LONGEST STREAK", unit(longest)), ("BUSIEST DAY", best_label)]
    for i, (lab, val) in enumerate(stats):
        y = 62 + i * 42
        b += text(610, y, lab, 10, MUTED, "700", MONO, extra='letter-spacing="1.5"')
        b += text(610, y + 22, val, 20, TEXT, "700")
    b += f'<rect x="590" y="50" width="1" height="112" fill="{BORDER}"/>'
    return svg(830, 190, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "cards"))
    a = ap.parse_args()
    if a.demo:
        weeks = demo_weeks()
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("Set GH_TOKEN (or use --demo for a local preview)")
        weeks = fetch(os.environ.get("GH_USER") or DATA["profile"]["handle"], token)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "heatmap.svg").write_text(heatmap(weeks), encoding="utf-8")
    (out / "activity.svg").write_text(activity(weeks), encoding="utf-8")
    print("wrote heatmap.svg and activity.svg to", out)


if __name__ == "__main__":
    main()
