"""Repository categories: one animated banner per category plus a chip per repo.

Public, non-fork repositories are sorted into categories by name/description.
Each category gets a banner SVG; each repo gets a small IC-chip SVG that the
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

from arm import gripper_arm
from contrib import _token
from smil import finalize

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

W, H = 900, 128
PANEL = (14, 14, 230, 100)
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
BP = dict(bg="#0b2747", ink="#e6f0ff", soft="#9cc2ee")
PCB = dict(board="#06120d", edge="#1f4d36", grid="#0c2219", copper="#b8862f", pad="#d4a94c", energy="#22d3ee", silk="#9fb8ac")


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

def defs():
    return f'''<defs>
<style>.t{{font-family:{FONT}}}</style>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2" result="b"/>
  <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="bpgrid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M10 0H0V10" fill="none" stroke="{BP["soft"]}" stroke-opacity="0.08"/></pattern>
<pattern id="bpmajor" width="50" height="50" patternUnits="userSpaceOnUse"><path d="M50 0H0V50" fill="none" stroke="{BP["soft"]}" stroke-opacity="0.17"/></pattern>
<pattern id="pcbgrid" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M8 0H0V8" fill="none" stroke="{PCB["grid"]}" stroke-width="0.6"/></pattern>
<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="{BP["soft"]}"/></pattern>
<clipPath id="panel"><rect x="{PANEL[0]}" y="{PANEL[1]}" width="{PANEL[2]}" height="{PANEL[3]}" rx="8"/></clipPath>
</defs>'''


def anim_robotics():
    dur, sc = 6.0, 0.6
    base, a, b, gy = (192, 112), 92, 292, 140     # shoulder, station A/B x, cube centre y
    keys = [(0.0, (192, 62), False), (0.7, (a, 98), False), (1.1, (a, gy), False), (1.35, (a, gy), True),
            (1.8, (a, 94), True), (2.6, (192, 56), True), (3.4, (b, 98), True), (3.8, (b, gy), True),
            (4.05, (b, gy), False), (4.5, (b, 94), False), (5.3, (192, 62), False), (dur, (192, 62), False)]
    cube = '<rect x="-8" y="-8" width="16" height="16" fill="#22d3ee" fill-opacity="0.3" stroke="#7dd3fc" stroke-width="1.4"/>'
    o = [f'<g transform="translate({PANEL[0]},{PANEL[1]}) scale({sc})">']
    for cx in (a, b):
        o.append(f'<rect x="{cx - 30}" y="{gy + 8}" width="60" height="9" fill="url(#hatch)" stroke="{BP["ink"]}" stroke-width="1.4"/>')
    o.append(f'<g transform="translate({a},{gy})">{cube}<animate attributeName="opacity" values="1;0;1" keyTimes="0;{1.35 / dur:.4f};{5.6 / dur:.4f}" calcMode="discrete" dur="{dur}s" repeatCount="indefinite"/></g>')
    o.append(f'<g transform="translate({b},{gy})" opacity="0">{cube}<animate attributeName="opacity" values="0;1;0" keyTimes="0;{4.05 / dur:.4f};{5.6 / dur:.4f}" calcMode="discrete" dur="{dur}s" repeatCount="indefinite"/></g>')
    o.append(f'<path d="M{base[0] - 22} {gy + 17} L{base[0] - 14} {base[1] + 8} L{base[0] + 14} {base[1] + 8} L{base[0] + 22} {gy + 17} Z" fill="{PCB["board"]}" stroke="{BP["ink"]}" stroke-width="1.4"/>')
    o.append(gripper_arm(base, 74, 64, 24, keys, dur, carried=cube, carry=(1.35, 4.05), fill=PCB["board"]))
    o.append('</g>')
    return "".join(o)


GLYPH_42 = {"4": [[(30, 60), (30, 0), (0, 30), (40, 30)]],
            "2": [[(0, 10), (10, 0), (30, 0), (40, 10), (40, 22), (0, 60), (40, 60)]]}


def anim_42():
    s = 1.2
    width = (58 + 40) * s
    x0 = PANEL[0] + (PANEL[2] - width) / 2
    y0 = PANEL[1] + (PANEL[3] - 60 * s) / 2
    o = []
    for i, ch in enumerate("42"):
        for k, st in enumerate(GLYPH_42[ch]):
            pts = [(x0 + (i * 58 + x) * s, y0 + y * s) for x, y in st]
            d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            ln = sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
            o.append(f'<path d="{d}" fill="none" stroke="#3b2a0c" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"/>'
                     f'<path d="{d}" fill="none" stroke="{PCB["copper"]}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>')
            o.append(f'<path d="{d}" fill="none" stroke="{PCB["energy"]}" stroke-width="2.2" stroke-linecap="round" filter="url(#glow)" '
                     f'stroke-dasharray="16 {ln:.0f}"><animate attributeName="stroke-dashoffset" values="16;{-ln:.0f}" '
                     f'dur="{ln / 70:.2f}s" begin="{i * 0.6:.1f}s" repeatCount="indefinite"/></path>')
            for px, py in (pts[0], pts[-1]):
                o.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="{PCB["pad"]}" stroke="#3b2a0c"/>'
                         f'<circle cx="{px:.1f}" cy="{py:.1f}" r="1.8" fill="{PCB["board"]}"/>')
    return "".join(o)


def anim_thesis():
    cx, cy = PANEL[0] + PANEL[2] / 2, PANEL[1] + PANEL[3] / 2 + 2
    pts = [(cx + 88 * math.sin(t), cy + 30 * math.sin(2 * t)) for t in [i * 2 * math.pi / 96 for i in range(97)]]
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"
    dur = 8
    o = [f'<path d="{d}" fill="none" stroke="{BP["soft"]}" stroke-width="1" stroke-dasharray="3 4" stroke-opacity="0.7"/>']
    for k in range(5, 0, -1):     # prediction horizon: ghosts running ahead of the robot
        o.append(f'<circle r="{3.4 - k * 0.35:.2f}" fill="#fbbf24" opacity="{0.85 - k * 0.13:.2f}">'
                 f'<animateMotion path="{d}" dur="{dur}s" begin="{-k * 0.22:.2f}s" repeatCount="indefinite"/></circle>')
    robot = (f'<rect x="-6" y="-11.5" width="12" height="3.5" rx="1.2" fill="#374151"/>'
             f'<rect x="-6" y="8" width="12" height="3.5" rx="1.2" fill="#374151"/>'
             f'<circle r="9.5" fill="#1f2937" stroke="#e5e7eb" stroke-width="1.4"/>'
             f'<circle r="4" fill="#111827" stroke="{PCB["energy"]}" stroke-width="1"/>'
             f'<path d="M5 -3 L10 0 L5 3 Z" fill="{PCB["energy"]}"/>')
    o.append(f'<g>{robot}<animateMotion path="{d}" dur="{dur}s" rotate="auto" repeatCount="indefinite"/></g>')
    o.append(f'<text x="{PANEL[0] + PANEL[2] - 10}" y="{PANEL[1] + PANEL[3] - 8}" class="t" font-size="7" fill="#fbbf24" text-anchor="end">N = 5</text>')
    return "".join(o)


ANIMS = {"robotics": anim_robotics, "42": anim_42, "thesis": anim_thesis}


def banner(key, repos):
    c = CATEGORIES[key]
    px, py, pw, ph = PANEL
    n = len(repos)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{c["title"].title().replace("'S", "'s")}">',
         defs(),
         f'<rect width="{W}" height="{H}" rx="12" fill="{BP["bg"]}"/><rect width="{W}" height="{H}" rx="12" fill="url(#bpgrid)"/>'
         f'<rect width="{W}" height="{H}" rx="12" fill="url(#bpmajor)"/>',
         f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="8" fill="{PCB["board"]}" stroke="{PCB["edge"]}" stroke-width="2"/>'
         f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="8" fill="url(#pcbgrid)" opacity="0.7"/>',
         f'<g clip-path="url(#panel)">{ANIMS[key]()}</g>',
         f'<text x="{px + 8}" y="{py + 12}" class="t" font-size="7" fill="{PCB["silk"]}">{c["mod"]}</text>']
    # title + copper trace into the repo counter
    o.append(f'<text x="272" y="56" class="t" font-size="27" font-weight="700" fill="{BP["ink"]}" letter-spacing="4">{c["title"]}</text>')
    o.append(f'<text x="274" y="80" class="t" font-size="10" fill="{BP["soft"]}" letter-spacing="2">{c["sub"]}</text>')
    trace = f"M{px + pw} {py + ph - 18} H 262 L 270 100 H 690 L 698 92 H 716"
    o.append(f'<path d="{trace}" fill="none" stroke="{PCB["copper"]}" stroke-width="2"/>'
             f'<path d="{trace}" fill="none" stroke="{PCB["energy"]}" stroke-width="2" stroke-dasharray="10 60" filter="url(#glow)">'
             f'<animate attributeName="stroke-dashoffset" values="70;0" dur="1.1s" repeatCount="indefinite"/></path>')
    bx, bw = 716, 170
    o.append(f'<rect x="{bx}" y="20" width="{bw}" height="88" fill="{BP["bg"]}" stroke="{BP["ink"]}" stroke-width="1.4"/>'
             f'<line x1="{bx}" y1="44" x2="{bx + bw}" y2="44" stroke="{BP["ink"]}"/>'
             f'<text x="{bx + 10}" y="36" class="t" font-size="8" fill="{BP["soft"]}" letter-spacing="1.5">REPOSITORIES</text>'
             f'<text x="{bx + 10}" y="80" class="t" font-size="30" font-weight="700" fill="{BP["ink"]}">{n:02d}</text>')
    step = min(14, (bw - 70) / max(n, 1))
    cyc = n * 0.35 + 1.2
    for k in range(n):
        lx = bx + 66 + k * step
        o.append(f'<circle cx="{lx:.1f}" cy="70" r="4" fill="#0f2a22" stroke="{PCB["copper"]}"/>'
                 f'<circle cx="{lx:.1f}" cy="70" r="3" fill="{PCB["energy"]}" opacity="0.2" filter="url(#glow)">'
                 f'<animate attributeName="opacity" values="0.2;0.2;1;0.2;0.2" keyTimes="0;{k * 0.35 / cyc:.3f};{(k * 0.35 + 0.1) / cyc:.3f};{(k * 0.35 + 0.6) / cyc:.3f};1" '
                 f'dur="{cyc:.2f}s" repeatCount="indefinite"/></circle>')
    o.append('</svg>')
    return finalize("\n".join(o))


# ---------------------------------------------------------------- chips

def chip(repo, k):
    name = repo["name"]
    lang = repo["primaryLanguage"]
    tw = len(name) * 7.2
    w = int(tw + (62 if lang else 46))
    h = 36
    pins = "".join(f'<rect x="{x}" y="2" width="4" height="6" rx="1" fill="#c9a227"/><rect x="{x}" y="28" width="4" height="6" rx="1" fill="#c9a227"/>'
                   for x in range(16, w - 14, 11))
    dot = (f'<circle cx="{w - 22}" cy="18" r="4.5" fill="{lang["color"] or "#9ca3af"}"/>' if lang else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{name}">'
            f'<defs><filter id="g" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="1.6"/></filter></defs>'
            f'{pins}<rect x="5" y="7" width="{w - 10}" height="22" rx="3" fill="#10161c" stroke="#2d3a44"/>'
            f'<path d="M5 14 A4 4 0 0 1 5 22" fill="#1f2937"/>'
            f'<circle cx="17" cy="18" r="3.2" fill="#22d3ee" filter="url(#g)"><animate attributeName="opacity" values="1;0.25;1" '
            f'dur="2.4s" begin="{k * 0.3:.1f}s" repeatCount="indefinite"/></circle><circle cx="17" cy="18" r="2" fill="#a5f3fc"/>'
            f'<text x="27" y="22.5" font-family="{FONT}" font-size="12" fill="#e6f0ff" textLength="{tw:.1f}" lengthAdjust="spacingAndGlyphs">{name}</text>'
            f'{dot}</svg>')


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
    k = 0
    for key, repos in cats.items():
        with open(os.path.join(args.out_dir, f"cat-{key}.svg"), "w") as f:
            f.write(banner(key, repos))
        for r in repos:
            with open(os.path.join(args.out_dir, "chips", f'{r["name"]}.svg'), "w") as f:
                f.write(chip(r, k))
            k += 1
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
