"""Repository categories: one banner per category plus a small badge per repo.

Public, non-fork repositories are sorted into categories by name/description.
Each category gets a banner SVG; each repo gets a badge SVG that the
README wraps in a link. The README block between the category markers is
rewritten so new repositories show up automatically.

usage: python categories.py USER OUT_DIR [--readme README.md] [--base URL]
"""
import argparse
import json
import math
import os
import re
import urllib.request

from contrib import _token

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes { name description url primaryLanguage { name color } }
    }
  }
}
"""

# assignment priority: first match wins
RULES = [
    ("thesis", r"thesis|bachelor"),
    ("42", r"42|libft|ft_printf|printf|push_swap|exam.?rank|codexion|maze|minishell|pipex|philosoph|so_long|minitalk|cub3d|fdf|netpractice|inception|webserv|transcendence"),
    ("robotics", r"robot|\bros\b|turtlebot|kinemat|manipulat|slam|ursina"),
]
# display order and copy
CATEGORIES = {
    "robotics": dict(title="ROBOTICS", sub="MANIPULATORS · KINEMATICS · ROS", mod="MOD-01"),
    "42": dict(title="42 BERLIN", sub="COMMON CORE · C · PYTHON", mod="MOD-02"),
    "thesis": dict(title="BACHELOR'S THESIS", sub="TURTLEBOT3 · PARAMETER ESTIMATION · MPC", mod="MOD-03"),
}
START, END = "<!-- categories:start -->", "<!-- categories:end -->"

W, H = 900, 96
PANEL = (12, 12, 150, 72)
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
BP = dict(bg="#0b2747", ink="#e6f0ff", soft="#9cc2ee", line="#2d4a6e")
PCB = dict(board="#06120d", edge="#1f4d36", copper="#b8862f", pad="#d4a94c", accent="#22d3ee")


def fetch_repos(login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {_token()}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = json.load(r)
    if "errors" in raw:
        raise RuntimeError(raw["errors"])
    return [r for r in raw["data"]["user"]["repositories"]["nodes"] if r["name"].lower() != login.lower()]


def categorise(repos):
    out = {k: [] for k in CATEGORIES}
    for r in repos:
        text = f'{r["name"]} {r["description"] or ""}'.lower().replace("-", "_")
        for key, pattern in RULES:
            if re.search(pattern, text):
                out[key].append(r)
                break
    return {k: v for k, v in out.items() if v}


# ---------------------------------------------------------------- banners

def link(x1, y1, x2, y2, w):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{BP["ink"]}" stroke-width="{w}" stroke-linecap="round"/>'
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{PCB["board"]}" stroke-width="{w - 2.6}" stroke-linecap="round"/>')


def icon_robotics():
    o = []
    for x in (16, 100):
        o.append(f'<rect x="{x}" y="60" width="34" height="5" fill="none" stroke="{BP["soft"]}"/>')
    o.append(f'<path d="M66 64 L70 50 L80 50 L84 64 Z" fill="{PCB["board"]}" stroke="{BP["ink"]}" stroke-width="1.2"/>')
    o.append(link(75, 50, 60, 26, 8) + link(60, 26, 117, 22, 7))
    o.append(f'<line x1="117" y1="22" x2="117" y2="33" stroke="{BP["ink"]}" stroke-width="1.4"/>'
             f'<path d="M110 40 V34 H124 V40" fill="none" stroke="{BP["ink"]}" stroke-width="1.4"/>'
             f'<rect x="112" y="40" width="10" height="10" fill="{PCB["accent"]}" fill-opacity="0.3" stroke="{PCB["accent"]}" stroke-width="1.1"/>')
    for x, y, r in ((75, 50, 4.5), (60, 26, 4), (117, 22, 3.2)):
        o.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{PCB["board"]}" stroke="{BP["ink"]}" stroke-width="1.2"/>')
    return "".join(o)


GLYPH_42 = {"4": [[(30, 60), (30, 0), (0, 30), (40, 30)]],
            "2": [[(0, 10), (10, 0), (30, 0), (40, 10), (40, 22), (0, 60), (40, 60)]]}


def icon_42():
    s = 0.8
    x0, y0 = (PANEL[2] - 98 * s) / 2, (PANEL[3] - 60 * s) / 2
    o = []
    for i, ch in enumerate("42"):
        for st in GLYPH_42[ch]:
            pts = [(x0 + (i * 58 + x) * s, y0 + y * s) for x, y in st]
            d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            o.append(f'<path d="{d}" fill="none" stroke="{PCB["copper"]}" stroke-width="3.4" stroke-linejoin="round" stroke-linecap="round"/>')
            for px, py in (pts[0], pts[-1]):
                o.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.6" fill="{PCB["pad"]}"/><circle cx="{px:.1f}" cy="{py:.1f}" r="1.3" fill="{PCB["board"]}"/>')
    return "".join(o)


def icon_thesis():
    cx, cy = PANEL[2] / 2, PANEL[3] / 2
    f = lambda t: (cx + 56 * math.sin(t), cy + 19 * math.sin(2 * t))
    pts = [f(i * 2 * math.pi / 72) for i in range(73)]
    o = [f'<path d="M' + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'Z" fill="none" stroke="{BP["soft"]}" stroke-dasharray="3 3" stroke-opacity="0.8"/>']
    t0 = 0.55
    for k in range(1, 5):
        x, y = f(t0 + k * 0.22)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{2.6 - k * 0.3:.1f}" fill="#fbbf24" opacity="{0.9 - k * 0.15:.2f}"/>')
    (x, y), (x2, y2) = f(t0), f(t0 + 0.01)
    ang = math.degrees(math.atan2(y2 - y, x2 - x))
    o.append(f'<g transform="translate({x:.1f},{y:.1f}) rotate({ang:.1f})">'
             f'<rect x="-5" y="-9" width="10" height="3" rx="1" fill="#374151"/><rect x="-5" y="6" width="10" height="3" rx="1" fill="#374151"/>'
             f'<circle r="7.5" fill="#1f2937" stroke="{BP["ink"]}" stroke-width="1.2"/>'
             f'<path d="M3 -2.5 L7.5 0 L3 2.5 Z" fill="{PCB["accent"]}"/></g>')
    return "".join(o)


ICONS = {"robotics": icon_robotics, "42": icon_42, "thesis": icon_thesis}


def banner(key, repos):
    c = CATEGORIES[key]
    px, py, pw, ph = PANEL
    label = c["title"].title().replace("'S", "'s")
    n = len(repos)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{label}">'
            f'<defs><pattern id="g" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M10 0H0V10" fill="none" stroke="{BP["soft"]}" stroke-opacity="0.07"/></pattern></defs>'
            f'<rect width="{W}" height="{H}" rx="10" fill="{BP["bg"]}"/><rect width="{W}" height="{H}" rx="10" fill="url(#g)"/>'
            f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="7" fill="{PCB["board"]}" stroke="{PCB["edge"]}" stroke-width="1.5"/>'
            f'<g transform="translate({px},{py})">{ICONS[key]()}</g>'
            f'<text x="190" y="47" font-family="{FONT}" font-size="24" font-weight="700" fill="{BP["ink"]}" letter-spacing="3">{c["title"]}</text>'
            f'<text x="191" y="68" font-family="{FONT}" font-size="10" fill="{BP["soft"]}" letter-spacing="2">{c["sub"]}</text>'
            f'<text x="{W - 24}" y="54" font-family="{FONT}" font-size="26" font-weight="700" fill="{BP["ink"]}" text-anchor="end">{n:02d}</text>'
            f'<text x="{W - 24}" y="70" font-family="{FONT}" font-size="8" fill="{BP["soft"]}" text-anchor="end" letter-spacing="1.5">REPOS</text>'
            f'</svg>')


# ---------------------------------------------------------------- chips

def chip(repo):
    name = repo["name"]
    lang = repo["primaryLanguage"]
    tw = len(name) * 7.2
    tx = 26 if lang else 12
    w = int(tx + tw + 12)
    h = 28
    dot = f'<circle cx="14" cy="14" r="4" fill="{lang["color"] or "#9ca3af"}"/>' if lang else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{name}">'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="6" fill="{BP["bg"]}" stroke="{BP["line"]}"/>'
            f'{dot}<text x="{tx}" y="18.5" font-family="{FONT}" font-size="12" fill="{BP["ink"]}" '
            f'textLength="{tw:.1f}" lengthAdjust="spacingAndGlyphs">{name}</text></svg>')


# ---------------------------------------------------------------- README block

def readme_block(cats, base):
    lines = [START]
    for key in CATEGORIES:
        if key not in cats:
            continue
        title = CATEGORIES[key]["title"].title().replace("'S", "'s")
        lines.append(f'<p align="center"><img src="{base}/cat-{key}.svg" alt="{title}" width="100%"></p>')
        lines.append('<p align="center">')
        for r in cats[key]:
            lines.append(f'  <a href="{r["url"]}"><img src="{base}/chips/{r["name"]}.svg" alt="{r["name"]}"></a>')
        lines.append('</p>')
        lines.append('')
    lines.append(END)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("user")
    ap.add_argument("out_dir")
    ap.add_argument("--readme")
    ap.add_argument("--base", default=".")
    args = ap.parse_args()
    cats = categorise(fetch_repos(args.user))
    os.makedirs(os.path.join(args.out_dir, "chips"), exist_ok=True)
    for key, repos in cats.items():
        with open(os.path.join(args.out_dir, f"cat-{key}.svg"), "w") as f:
            f.write(banner(key, repos))
        for r in repos:
            with open(os.path.join(args.out_dir, "chips", f'{r["name"]}.svg'), "w") as f:
                f.write(chip(r))
    block = readme_block(cats, args.base)
    if args.readme:
        text = open(args.readme).read()
        if START in text and END in text:
            text = text[:text.index(START)] + block + text[text.index(END) + len(END):]
            with open(args.readme, "w") as f:
                f.write(text)
    else:
        print(block)
    for key, repos in cats.items():
        print(f"categories: {key}: {', '.join(r['name'] for r in repos)}")


if __name__ == "__main__":
    main()
