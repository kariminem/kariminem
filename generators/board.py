"""README circuit board: stackable section SVGs that power on after the deploy.

Every section shares the same power buses along both edges, so the stacked
images read as one continuous board. Sections start dark; at the moment the
assembly line's packet hits the name (plus a small cascade delay) they boot,
and from then on pulses keep running through the wiring.

usage: python board.py USER OUT_DIR --theme NAME [--cache file.json] [--base URL]
"""
import argparse
import base64
import math
import os
import random

import assembly
from categories import CATEGORIES, GLYPH_42, ICONS, categorise, fetch_repos
from contrib import fetch
from smil import finalize

W = 900
BUS = (10, 22, 878, 890)
X0, X1 = 70, 830                     # content column
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

DESC = {
    "Bachelors-thesis-codes": "Modeling, parameter estimation and MPC control of a Turtlebot3",
    "python_rob": "Robotics logic and 3D visualization on Windows without ROS",
    "ROS": "ROS material from the GUC IEEE robotics club",
    "codexion": "Codexion project at 42 Berlin",
    "Python_Modules_42": "Python modules 00 to 10",
    "A-maze-ing": "Maze generator and visualizer",
    "Exam-Rank-02": "Exam Rank 02 practice and solutions",
    "push_swap": "Stack sorting with the fewest possible operations",
    "ft_printf": "printf rebuilt from scratch in C",
}
ABOUT = [("name", "Karim Taher"), ("role", "Robotics Engineer"), ("school", "42 Berlin"),
         ("thesis", "Turtlebot3 modeling, parameter estimation and MPC control"),
         ("building", "python_rob, a 3D robotics sandbox that runs without ROS"),
         ("interests", "VLA models, speech assistants, embedded C")]
CAT_COLOR = {"robotics": "#38bdf8", "42": "#4ade80", "thesis": "#c084fc"}

THEMES = {
    "mainboard": dict(label="Mainboard", tagline="Green PCB, silkscreen labels, cyan current",
                      bg="#0b3d25", grid="#14532f", trace="#2f8f5b", pad="#c0c6cc", energy="#7df9ff", energy2="#7df9ff",
                      ink="#effff5", soft="#9fd8b4", card="none", edge="#effff5", header="silk", boot="deploy"),
    "blueprint": dict(label="Blueprint Board", tagline="The whole README as one engineering drawing",
                      bg="#0b2747", grid="#16365e", trace="#4b77a8", pad="#e6f0ff", energy="#22d3ee", energy2="#22d3ee",
                      ink="#e6f0ff", soft="#9cc2ee", card="none", edge="#9cc2ee", header="titleblock", boot="deploy"),
    "chrome": dict(label="Chrome & Lightning", tagline="Black board, chrome wires, electric arcs",
                   bg="#07080b", grid="#11141a", trace="url(#chrome)", pad="#d1d5db", energy="#60a5fa", energy2="#c7d2fe",
                   ink="#f3f4f6", soft="#9ca3af", card="#0d1016", edge="url(#chrome)", header="plate", boot="deploy", bolts=True),
    "neon": dict(label="Neon Circuit", tagline="Synthwave board, magenta and cyan alternating",
                 bg="#0d0221", grid="#1b0b3a", trace="#3b1d6e", pad="#a78bfa", energy="#ff2bd6", energy2="#22d3ee",
                 ink="#fdf4ff", soft="#c4b5fd", card="#14062e", edge="#ff2bd6", header="neon", boot="deploy"),
    "minimal": dict(label="Quiet Wiring", tagline="No board fill, thin wiring in the margins, boots right away",
                    bg=None, grid=None, trace="#3d444d", pad="#6e7681", energy="#58a6ff", energy2="#3fb950",
                    ink="#e6edf3", soft="#8b949e", card="#161b22", edge="#30363d", header="card", boot="fast"),
}


def kt(times, dur):
    out, last = [], 0.0
    for t in times:
        v = min(1.0, max(last, t / dur))
        out.append(v)
        last = v
    return ";".join(f"{v:.4f}" for v in out)


# ------------------------------------------------------------------ frame

class Section:
    def __init__(self, T, h, t_on, seed, last=False):
        self.T, self.h, self.t_on, self.last = T, h, t_on, last
        self.rng = random.Random(seed)
        self.decor, self.content, self.energy = [], [], []

    def defs(self):
        T = self.T
        out = [f'<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2" result="b"/>'
               f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
               f'<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>',
               '<linearGradient id="chrome" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6b7280"/>'
               '<stop offset="0.45" stop-color="#f3f4f6"/><stop offset="0.55" stop-color="#9ca3af"/><stop offset="1" stop-color="#4b5563"/></linearGradient>',
               '<linearGradient id="plate" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3f47"/>'
               '<stop offset="0.5" stop-color="#1c1f25"/><stop offset="1" stop-color="#2b2f36"/></linearGradient>',
               '<linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
               '<stop offset="0.5" stop-color="#fff" stop-opacity="0.35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>']
        if T["grid"]:
            out.append(f'<pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">'
                       f'<path d="M10 0H0V10" fill="none" stroke="{T["grid"]}" stroke-width="0.7"/></pattern>')
        return "<defs>" + "".join(out) + f"<style>.m{{font-family:{FONT}}} .s{{font-family:{SANS}}}</style></defs>"

    def background(self):
        T, h = self.T, self.h
        if not T["bg"]:
            return ""
        r = 12 if self.last else 0
        shape = (f'<path d="M0 0H{W}V{h - r}' + (f'A{r} {r} 0 0 1 {W - r} {h}H{r}A{r} {r} 0 0 1 0 {h - r}' if r else f'H0') + 'Z" fill="{fill}"/>')
        return shape.replace("{fill}", T["bg"]) + (shape.replace("{fill}", "url(#grid)") if T["grid"] else "")

    # --- wiring ---------------------------------------------------------
    def buses(self):
        T, h = self.T, self.h
        out = []
        for i, x in enumerate(BUS):
            out.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{T["trace"]}" stroke-width="2"/>')
            col = T["energy"] if i % 2 == 0 else T["energy2"]
            speed = 0.9 if i % 2 == 0 else 1.4
            self.energy.append(
                f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{col}" stroke-width="2" stroke-dasharray="7 41" filter="url(#glow)" opacity="0">'
                f'<animate attributeName="stroke-dashoffset" values="0;-48" dur="{speed}s" repeatCount="indefinite"/>'
                f'<set attributeName="opacity" to="1" begin="{self.t_on + 0.2:.2f}s"/></line>')
        return "".join(out)

    def components(self):
        """Resistors, caps, vias and small ICs in the margins, each wired to a bus."""
        T, h, rng = self.T, self.h, self.rng
        out = []
        for side, (bus, xa, xb) in enumerate([(BUS[1], 30, 60), (BUS[2], 840, 870)]):
            y = rng.uniform(8, 20)
            while y < h - 10:
                kind = rng.choice(["res", "cap", "via", "ic", "via", "res"])
                cx = rng.uniform(xa + 6, xb - 6)
                if kind == "ic" and y + 18 > h - 4:
                    kind = "via"
                stub_y = y + (6 if kind == "ic" else 0)
                x_from, x_to = (bus, cx) if side == 0 else (cx, bus)
                out.append(f'<line x1="{x_from:.1f}" y1="{stub_y:.1f}" x2="{x_to:.1f}" y2="{stub_y:.1f}" stroke="{T["trace"]}" stroke-width="1.4"/>')
                out.append(f'<circle cx="{bus}" cy="{stub_y:.1f}" r="2.4" fill="{T["pad"]}"/>')
                if kind == "res":
                    out.append(f'<rect x="{cx - 8:.1f}" y="{y - 3:.1f}" width="16" height="6" rx="2" fill="#2b2f36" stroke="{T["pad"]}" stroke-width="0.8"/>'
                               f'<rect x="{cx - 3:.1f}" y="{y - 3:.1f}" width="2" height="6" fill="{T["energy"]}" opacity="0.7"/>')
                elif kind == "cap":
                    out.append(f'<line x1="{cx - 2:.1f}" y1="{y - 6:.1f}" x2="{cx - 2:.1f}" y2="{y + 6:.1f}" stroke="{T["pad"]}" stroke-width="1.6"/>'
                               f'<line x1="{cx + 2:.1f}" y1="{y - 6:.1f}" x2="{cx + 2:.1f}" y2="{y + 6:.1f}" stroke="{T["pad"]}" stroke-width="1.6"/>')
                elif kind == "ic":
                    out.append(f'<rect x="{cx - 7:.1f}" y="{y:.1f}" width="14" height="12" rx="1.5" fill="#15171c" stroke="{T["pad"]}" stroke-width="0.8"/>')
                else:
                    out.append(f'<circle cx="{cx:.1f}" cy="{y:.1f}" r="3" fill="none" stroke="{T["pad"]}" stroke-width="1.2"/>')
                # some stubs carry their own pulse once powered
                if rng.random() < 0.55:
                    ln = abs(x_to - x_from)
                    d0 = rng.uniform(0, 2.5)
                    self.energy.append(
                        f'<line x1="{x_from:.1f}" y1="{stub_y:.1f}" x2="{x_to:.1f}" y2="{stub_y:.1f}" stroke="{T["energy2"] if rng.random() < 0.5 else T["energy"]}" '
                        f'stroke-width="1.6" stroke-dasharray="5 {ln + 20:.0f}" filter="url(#glow)" opacity="0">'
                        f'<animate attributeName="stroke-dashoffset" values="5;{-ln - 15:.0f}" dur="{rng.uniform(0.9, 1.8):.2f}s" '
                        f'begin="{self.t_on + 0.3 + d0:.2f}s" repeatCount="indefinite"/>'
                        f'<set attributeName="opacity" to="1" begin="{self.t_on + 0.3 + d0:.2f}s"/></line>')
                y += rng.uniform(20, 34) + (12 if kind == "ic" else 0)
        if self.T.get("bolts"):
            for side in (0, 1):
                if rng.random() < 0.8:
                    self.energy.append(self.bolt(side))
        return "".join(out)

    def bolt(self, side):
        """Electric arc between the two buses on one side, flickering through a few shapes."""
        rng, h = self.rng, self.h
        xa, xb = (BUS[0], BUS[1] + 40) if side == 0 else (BUS[2] - 40, BUS[3])
        y = rng.uniform(10, h - 10)
        shapes = []
        for _ in range(4):
            pts = [(xa, y)]
            for k in range(1, 6):
                pts.append((xa + (xb - xa) * k / 6, y + rng.uniform(-7, 7)))
            pts.append((xb, y + rng.uniform(-3, 3)))
            shapes.append("M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts))
        period = rng.uniform(2.5, 4.5)
        t0 = self.t_on + rng.uniform(0.5, 3)
        return (f'<path d="{shapes[0]}" fill="none" stroke="#e0e7ff" stroke-width="1.3" filter="url(#glow)" opacity="0">'
                f'<animate attributeName="d" values="{";".join(shapes)}" dur="0.24s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values="0;1;0.3;1;0;0" keyTimes="0;0.04;0.08;0.12;0.18;1" dur="{period:.2f}s" '
                f'begin="{t0:.2f}s" repeatCount="indefinite"/></path>')

    def render(self, aria):
        T, h = self.T, self.h
        decor = self.buses() + self.components()
        boot = self.t_on
        flick = f'values="0.12;0.8;0.3;1" keyTimes="0;0.3;0.55;1" dur="0.7s" begin="{boot:.2f}s" fill="freeze"'
        flick_c = f'values="0.45;0.9;0.6;1" keyTimes="0;0.3;0.55;1" dur="0.7s" begin="{boot:.2f}s" fill="freeze"'
        sweep = (f'<rect x="0" y="-6" width="{W}" height="6" fill="{T["energy"]}" opacity="0" filter="url(#soft)">'
                 f'<animate attributeName="y" values="-6;{h}" dur="0.45s" begin="{boot:.2f}s" fill="freeze"/>'
                 f'<animate attributeName="opacity" values="0.9;0.9;0" keyTimes="0;0.8;1" dur="0.45s" begin="{boot:.2f}s"/></rect>')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" role="img" aria-label="{aria}">'
               f'{self.defs()}{self.background()}'
               f'<g opacity="0.12">{decor}<animate attributeName="opacity" {flick}/></g>'
               f'<g opacity="0.45">{"".join(self.content)}<animate attributeName="opacity" {flick_c}/></g>'
               f'{"".join(self.energy)}{sweep}</svg>')
        return finalize(svg)


# ------------------------------------------------------------------ neon icons (150 x 72 window)

def neon_robot(t_on):
    """Smiling robot face: blinking eyes, alternating antenna lights, a happy squint now and then."""
    cyan, pink = "#22d3ee", "#ff2bd6"
    blink = 'values="1;1;0.1;1;1" keyTimes="0;0.9;0.94;0.98;1" dur="3.7s" repeatCount="indefinite"'
    happy = f'begin="{t_on + 4:.2f}s" dur="7s" repeatCount="indefinite"'
    eyes = "".join(f'<rect x="{x}" y="29" width="9" height="11" rx="3.5" fill="{cyan}" filter="url(#glow)" '
                   f'transform-origin="{x + 4.5} 34.5"><animateTransform attributeName="transform" type="scale" '
                   f'values="1 1;1 1;1 0.12;1 1;1 1" keyTimes="0;0.9;0.94;0.98;1" dur="3.7s" repeatCount="indefinite"/></rect>'
                   for x in (59, 82))
    arcs = "".join(f'<path d="M{x} 37 Q{x + 4.5} 29 {x + 9} 37" fill="none" stroke="{cyan}" stroke-width="2.4" '
                   f'stroke-linecap="round" filter="url(#glow)"/>' for x in (59, 82))
    return (f'<line x1="62" y1="16" x2="58" y2="7" stroke="{cyan}" stroke-width="1.6"/>'
            f'<line x1="88" y1="16" x2="92" y2="7" stroke="{cyan}" stroke-width="1.6"/>'
            f'<circle cx="58" cy="6" r="3" fill="{pink}" filter="url(#glow)"><animate attributeName="opacity" values="1;0.2;1" dur="1.2s" repeatCount="indefinite"/></circle>'
            f'<circle cx="92" cy="6" r="3" fill="{pink}" filter="url(#glow)"><animate attributeName="opacity" values="0.2;1;0.2" dur="1.2s" repeatCount="indefinite"/></circle>'
            f'<rect x="45" y="15" width="60" height="47" rx="13" fill="#1a0b3a" stroke="{cyan}" stroke-width="1.8" filter="url(#glow)"/>'
            f'<rect x="40" y="31" width="5" height="14" rx="2" fill="{pink}" opacity="0.8"/><rect x="105" y="31" width="5" height="14" rx="2" fill="{pink}" opacity="0.8"/>'
            f'<rect x="52" y="23" width="46" height="22" rx="8" fill="#07010f"/>'
            f'<g>{eyes}<animate attributeName="opacity" values="1;0;1" keyTimes="0;0.7;0.86" calcMode="discrete" {happy}/></g>'
            f'<g opacity="0">{arcs}<animate attributeName="opacity" values="0;1;0" keyTimes="0;0.7;0.86" calcMode="discrete" {happy}/></g>'
            f'<path d="M64 51 Q75 58 86 51" fill="none" stroke="{pink}" stroke-width="2.2" stroke-linecap="round" filter="url(#glow)"/>'
            f'<circle cx="56" cy="50" r="2.6" fill="{pink}" opacity="0.45"/><circle cx="94" cy="50" r="2.6" fill="{pink}" opacity="0.45"/>')


def neon_42(t_on):
    """Neon-tube 42 that flickers on and off like a real sign, each digit on its own rhythm."""
    s = 0.8
    x0, y0 = (150 - 98 * s) / 2, (72 - 60 * s) / 2
    o = []
    rhythms = [("1;1;0.15;1;0.3;1;1;0.1;0.1;1", "0;0.55;0.57;0.6;0.62;0.66;0.85;0.87;0.93;0.95", "5.3s"),
               ("1;0.2;1;1;0.15;0.15;1;1", "0;0.03;0.07;0.7;0.72;0.8;0.83;1", "6.7s")]
    for i, ch in enumerate("42"):
        tubes = []
        for st in GLYPH_42[ch]:
            pts = [(x0 + (i * 58 + x) * s, y0 + y * s) for x, y in st]
            d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            o.append(f'<path d="{d}" fill="none" stroke="#3b1d6e" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>')
            tubes.append(d)
        col = "#ff2bd6" if i == 0 else "#22d3ee"
        vals, kts, dur = rhythms[i]
        lit = "".join(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" filter="url(#glow)"/>'
                      f'<path d="{d}" fill="none" stroke="#fff" stroke-width="1" stroke-linejoin="round" stroke-linecap="round" opacity="0.8"/>'
                      for d in tubes)
        o.append(f'<g opacity="0">{lit}<set attributeName="opacity" to="1" begin="{t_on + 0.3 + i * 0.25:.2f}s"/>'
                 f'<animate attributeName="opacity" values="{vals}" keyTimes="{kts}" dur="{dur}" begin="{t_on + 0.3 + i * 0.25:.2f}s" repeatCount="indefinite"/></g>')
    return "".join(o)


def neon_thesis(t_on):
    """Turtlebot driving its figure-8 with the MPC horizon running ahead."""
    cx, cy = 75, 36
    pts = [(cx + 56 * math.sin(t), cy + 19 * math.sin(2 * t)) for t in [i * 2 * math.pi / 96 for i in range(97)]]
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"
    dur = 10
    o = [f'<path d="{d}" fill="none" stroke="#a78bfa" stroke-dasharray="3 3" stroke-opacity="0.7"/>']
    for k in range(4, 0, -1):
        o.append(f'<circle r="{2.8 - k * 0.35:.2f}" fill="#ff2bd6" opacity="{0.95 - k * 0.17:.2f}" filter="url(#glow)">'
                 f'<animateMotion path="{d}" dur="{dur}s" begin="{-k * 0.3:.2f}s" repeatCount="indefinite"/></circle>')
    o.append(f'<g><rect x="-5" y="-9" width="10" height="3" rx="1" fill="#4c1d95"/><rect x="-5" y="6" width="10" height="3" rx="1" fill="#4c1d95"/>'
             f'<circle r="7.5" fill="#14062e" stroke="#22d3ee" stroke-width="1.4" filter="url(#glow)"/>'
             f'<path d="M3 -2.5 L7.5 0 L3 2.5 Z" fill="#22d3ee"/>'
             f'<animateMotion path="{d}" dur="{dur}s" rotate="auto" repeatCount="indefinite"/></g>')
    return "".join(o)


NEON_ICONS = {"robotics": neon_robot, "42": neon_42, "thesis": neon_thesis}


# ------------------------------------------------------------------ content

def trace_to_bus(S, y):
    """Short traces tying a content card to the inner buses on both sides."""
    T = S.T
    return (f'<line x1="{BUS[1]}" y1="{y}" x2="{X0}" y2="{y}" stroke="{T["trace"]}" stroke-width="1.6"/>'
            f'<line x1="{X1}" y1="{y}" x2="{BUS[2]}" y2="{y}" stroke="{T["trace"]}" stroke-width="1.6"/>'
            f'<circle cx="{BUS[1]}" cy="{y}" r="3" fill="{T["pad"]}"/><circle cx="{BUS[2]}" cy="{y}" r="3" fill="{T["pad"]}"/>')


def header(S, key, n, idx):
    T, c = S.T, CATEGORIES[key]
    style = T["header"]
    col = CAT_COLOR[key]
    o = [trace_to_bus(S, 44)]
    title_x = 244
    if style == "neon":
        icon = (f'<rect x="{X0}" y="8" width="150" height="72" rx="10" fill="#0a0118" stroke="{col}" stroke-width="1.3" stroke-opacity="0.7"/>'
                f'<g transform="translate({X0},8)">{NEON_ICONS[key](S.t_on)}</g>')
    else:
        icon = f'<rect x="{X0}" y="8" width="150" height="72" rx="7" fill="#06120d" stroke="{T["trace"] if style != "card" else T["edge"]}" stroke-width="1.5"/>' \
               f'<g transform="translate({X0},8)">{ICONS[key]()}</g>'
    if style == "silk":
        o.append(f'<rect x="{X0 - 4}" y="4" width="{X1 - X0 + 8}" height="80" rx="4" fill="none" stroke="{T["ink"]}" stroke-width="1.2"/>'
                 f'<text x="{X1 - 6}" y="16" class="m" font-size="8" fill="{T["ink"]}" text-anchor="end">J{idx + 1}</text>')
    elif style == "titleblock":
        o.append(f'<rect x="{X0 - 4}" y="4" width="{X1 - X0 + 8}" height="80" fill="{T["bg"]}" stroke="{T["ink"]}" stroke-width="1.4"/>'
                 f'<line x1="{X1 - 120}" y1="4" x2="{X1 - 120}" y2="84" stroke="{T["ink"]}"/>'
                 f'<text x="{X1 - 112}" y="18" class="m" font-size="7" fill="{T["soft"]}" letter-spacing="1">QTY</text>'
                 f'<text x="{title_x}" y="20" class="m" font-size="7" fill="{T["soft"]}" letter-spacing="1">CATEGORY {idx + 1:02d}</text>')
    elif style == "plate":
        o.append(f'<rect x="{X0 - 4}" y="4" width="{X1 - X0 + 8}" height="80" rx="8" fill="url(#plate)" stroke="url(#chrome)" stroke-width="1.6"/>')
        for sx in (X0 + 166, X1 - 10):
            o.append(f'<circle cx="{sx}" cy="14" r="3" fill="url(#chrome)"/><circle cx="{sx}" cy="74" r="3" fill="url(#chrome)"/>')
        S.energy.append(f'<g opacity="0"><rect x="0" y="4" width="120" height="80" fill="url(#sheen)" transform="skewX(-20)">'
                        f'<animate attributeName="x" values="{X0};{X1 + 60}" dur="1.4s" begin="{S.t_on + 1 + idx * 0.4:.2f}s;'
                        f'{S.t_on + 7 + idx * 0.4:.2f}s" fill="freeze"/></rect>'
                        f'<set attributeName="opacity" to="1" begin="{S.t_on + 1:.2f}s"/></g>')
    elif style == "neon":
        o.append(f'<rect x="{X0 - 4}" y="4" width="{X1 - X0 + 8}" height="80" rx="14" fill="{T["card"]}" stroke="{col}" stroke-opacity="0.35"/>')
    elif style == "card":
        o.append(f'<rect x="{X0 - 4}" y="4" width="{X1 - X0 + 8}" height="80" rx="10" fill="{T["card"]}" stroke="{T["edge"]}"/>'
                 f'<rect x="{X0 - 4}" y="4" width="5" height="80" rx="2.5" fill="{col}"/>')
    o.append(icon)
    title_fill = T["ink"] if style != "plate" else "#e5e7eb"
    if style == "neon":
        flick = f'values="0.2;1;0.3;1;0.6;1" keyTimes="0;0.15;0.3;0.5;0.7;1" dur="0.9s" begin="{S.t_on + 0.4:.2f}s;{S.t_on + 9 + idx:.2f}s"'
        o.append(f'<text x="{title_x}" y="50" class="m" font-size="26" font-weight="700" fill="none" stroke="{col}" stroke-width="1.2" '
                 f'letter-spacing="3" filter="url(#glow)">{c["title"]}<animate attributeName="opacity" {flick}/></text>')
        o.append(f'<text x="{title_x}" y="50" class="m" font-size="26" font-weight="700" fill="#fff" fill-opacity="0.9" letter-spacing="3">{c["title"]}</text>')
    else:
        if style == "plate":
            o.append(f'<text x="{title_x}" y="51" class="m" font-size="26" font-weight="700" fill="#000" fill-opacity="0.6" letter-spacing="3">{c["title"]}</text>')
        o.append(f'<text x="{title_x}" y="50" class="m" font-size="26" font-weight="700" fill="{title_fill}" letter-spacing="3">{c["title"]}</text>')
    o.append(f'<text x="{title_x + 1}" y="70" class="m" font-size="10" fill="{T["soft"]}" letter-spacing="2">{c["sub"]}</text>')
    o.append(f'<text x="{X1 - 12}" y="56" class="m" font-size="28" font-weight="700" fill="{T["ink"]}" text-anchor="end">{n:02d}</text>'
             f'<text x="{X1 - 12}" y="72" class="m" font-size="8" fill="{T["soft"]}" text-anchor="end" letter-spacing="1.5">REPOS</text>')
    # status LED by the count, steady once powered with an occasional blink
    S.energy.append(f'<circle cx="{X1 - 70}" cy="46" r="4" fill="{col}" opacity="0" filter="url(#glow)">'
                    f'<set attributeName="opacity" to="1" begin="{S.t_on + 0.5:.2f}s"/>'
                    f'<animate attributeName="opacity" values="1;0.2;1" dur="0.5s" begin="{S.t_on + 3 + idx:.2f}s;{S.t_on + 8 + idx:.2f}s"/></circle>')
    S.content.append("".join(o))


def repo_row(S, repo, idx, key):
    T = S.T
    style = T["header"]
    name = repo["name"]
    lang = repo["primaryLanguage"]
    desc = DESC.get(name) or (repo["description"] or "")
    nw = len(name) * 7.8
    room = int((X1 - 140 - (104 + nw + 18)) / 6.3)
    if len(desc) > room:
        desc = desc[:room - 1].rsplit(" ", 1)[0] + "…"
    col = CAT_COLOR[key]
    y0, hh = 5, 34
    o = [trace_to_bus(S, 22)]
    if style == "silk":
        o.append(f'<rect x="{X0}" y="{y0}" width="{X1 - X0}" height="{hh}" rx="3" fill="none" stroke="{T["ink"]}" stroke-opacity="0.6"/>'
                 f'<text x="{X0 + 8}" y="{y0 + 12}" class="m" font-size="6.5" fill="{T["soft"]}">U{idx + 1}</text>')
    elif style == "titleblock":
        o.append(f'<rect x="{X0}" y="{y0}" width="{X1 - X0}" height="{hh}" fill="{T["bg"]}" stroke="{T["soft"]}"/>'
                 f'<line x1="{X1 - 120}" y1="{y0}" x2="{X1 - 120}" y2="{y0 + hh}" stroke="{T["soft"]}"/>')
    elif style == "plate":
        o.append(f'<rect x="{X0}" y="{y0}" width="{X1 - X0}" height="{hh}" rx="7" fill="{T["card"]}" stroke="url(#chrome)" stroke-width="1.2"/>'
                 f'<line x1="{X0 + 8}" y1="{y0 + 1}" x2="{X1 - 8}" y2="{y0 + 1}" stroke="#fff" stroke-opacity="0.15"/>')
    elif style == "neon":
        o.append(f'<rect x="{X0}" y="{y0}" width="{X1 - X0}" height="{hh}" rx="17" fill="{T["card"]}" stroke="{col}" stroke-width="1.3" filter="url(#glow)"/>')
    else:
        o.append(f'<rect x="{X0}" y="{y0}" width="{X1 - X0}" height="{hh}" rx="8" fill="{T["card"]}" stroke="{T["edge"]}"/>')
    dot = (lang or {}).get("color") or "#9ca3af"
    o.append(f'<circle cx="{X0 + 22}" cy="{y0 + hh / 2}" r="5" fill="{dot}"/>')
    o.append(f'<text x="{X0 + 36}" y="{y0 + 22}" class="m" font-size="13" font-weight="700" fill="{T["ink"]}" '
             f'textLength="{nw:.1f}" lengthAdjust="spacingAndGlyphs">{name}</text>')
    o.append(f'<text x="{X0 + 36 + nw + 18:.1f}" y="{y0 + 21.5}" class="s" font-size="11.5" fill="{T["soft"]}">{desc}</text>')
    o.append(f'<text x="{X1 - 16}" y="{y0 + 21.5}" class="m" font-size="9.5" fill="{T["soft"]}" text-anchor="end" letter-spacing="1">'
             f'{(lang or {}).get("name", "").upper()}  ↗</text>')
    S.energy.append(f'<circle cx="{X0 + 22}" cy="{y0 + hh / 2}" r="7" fill="{dot}" opacity="0" filter="url(#soft)">'
                    f'<animate attributeName="opacity" values="0;0.8;0" dur="0.6s" begin="{S.t_on + 0.15:.2f}s"/></circle>')
    S.content.append("".join(o))


def about(S):
    T = S.T
    o = [trace_to_bus(S, 20)]
    style = T["header"]
    h = S.h - 10
    if style == "neon":
        o.append(f'<rect x="{X0}" y="6" width="{X1 - X0}" height="{h - 2}" rx="16" fill="{T["card"]}" stroke="{T["energy2"]}" stroke-width="1.2" filter="url(#glow)"/>')
    elif style in ("plate",):
        o.append(f'<rect x="{X0}" y="6" width="{X1 - X0}" height="{h - 2}" rx="8" fill="{T["card"]}" stroke="url(#chrome)" stroke-width="1.2"/>')
    elif style == "card":
        o.append(f'<rect x="{X0}" y="6" width="{X1 - X0}" height="{h - 2}" rx="10" fill="{T["card"]}" stroke="{T["edge"]}"/>')
    else:
        o.append(f'<rect x="{X0}" y="6" width="{X1 - X0}" height="{h - 2}" fill="{T["bg"]}" stroke="{T["ink"]}" stroke-opacity="0.8"/>')
    o.append(f'<text x="{X0 + 20}" y="30" class="m" font-size="9" fill="{T["soft"]}" letter-spacing="2">ABOUT</text>')
    for i, (k, v) in enumerate(ABOUT):
        y = 54 + i * 19
        o.append(f'<text x="{X0 + 20}" y="{y}" class="m" font-size="12" fill="{T["energy"] if T["header"] != "silk" else "#7df9ff"}">{k}:</text>'
                 f'<text x="{X0 + 130}" y="{y}" class="m" font-size="12" fill="{T["ink"]}">{v}</text>')
    S.content.append("".join(o))


def skills(S, skills_svg):
    T = S.T
    data = base64.b64encode(skills_svg.encode()).decode()
    w = 442
    S.content.append(trace_to_bus(S, S.h / 2) +
                     f'<rect x="{(W - w) / 2 - 16}" y="10" width="{w + 32}" height="{S.h - 20}" rx="10" fill="{T["card"] if T["card"] != "none" else T["bg"]}" '
                     f'stroke="{T["edge"]}" stroke-opacity="0.8"/>'
                     f'<image href="data:image/svg+xml;base64,{data}" x="{(W - w) / 2}" y="{(S.h - 51) / 2}" width="{w}" height="51"/>')


def footer(S):
    T = S.T
    o = []
    for x in BUS:
        o.append(f'<line x1="{x - 6}" y1="{S.h - 14}" x2="{x + 6}" y2="{S.h - 14}" stroke="{T["pad"]}" stroke-width="1.6"/>'
                 f'<line x1="{x - 4}" y1="{S.h - 10}" x2="{x + 4}" y2="{S.h - 10}" stroke="{T["pad"]}" stroke-width="1.4"/>'
                 f'<line x1="{x - 2}" y1="{S.h - 6}" x2="{x + 2}" y2="{S.h - 6}" stroke="{T["pad"]}" stroke-width="1.2"/>')
    S.content.append("".join(o))


# ------------------------------------------------------------------ build

def build(user, out_dir, theme, cache=None, base=".", skills_path=None):
    T = THEMES[theme]
    d = fetch(user, cache)
    saved = dict(assembly.BP)
    if T["bg"]:
        assembly.BP.update(bg=T["bg"], soft=T["soft"] if theme != "mainboard" else "#9fd8b4")
    hero = assembly.render(d, exits=True, start_near_deploy=True)
    assembly.BP.clear()
    assembly.BP.update(saved)
    t0 = 1.0 if T["boot"] == "fast" else assembly.TIMING["first_hit"] + 0.55
    os.makedirs(out_dir, exist_ok=True)
    files = [("hero.svg", hero, "Karim Taher", None)]
    cats = categorise(fetch_repos(user))
    i = 0
    for key in CATEGORIES:
        if key not in cats:
            continue
        S = Section(T, 88, t0 + i * 0.12, seed=i)
        header(S, key, len(cats[key]), list(CATEGORIES).index(key))
        files.append((f"cat-{key}.svg", S.render(CATEGORIES[key]["title"].title()), CATEGORIES[key]["title"].title(), None))
        i += 1
        for r in cats[key]:
            S = Section(T, 44, t0 + i * 0.12, seed=i)
            repo_row(S, r, i, key)
            files.append((f"repo-{r['name']}.svg", S.render(r["name"]), r["name"], r["url"]))
            i += 1
    S = Section(T, 178, t0 + i * 0.12, seed=i)
    about(S)
    files.append(("about.svg", S.render("About"), "About", None))
    i += 1
    if skills_path:
        S = Section(T, 84, t0 + i * 0.12, seed=i)
        skills(S, open(skills_path).read())
        files.append(("skills.svg", S.render("C, C++, Python, ROS, Linux, Bash, TypeScript, Git"), "C, C++, Python, ROS, Linux, Bash, TypeScript, Git", None))
        i += 1
    S = Section(T, 34, t0 + i * 0.12, seed=i, last=True)
    footer(S)
    files.append(("footer.svg", S.render(""), "", None))

    lines = ['<p align="center">']
    for name, svg, alt, url in files:
        with open(os.path.join(out_dir, name), "w") as f:
            f.write(svg)
        img = f'<img src="{base}/{name}" width="100%" alt="{alt}">'
        lines.append(f'  <a href="{url}">{img}</a>' if url else f"  {img}")
    lines.append("</p>")
    return "\n".join(lines)


START, END = "<!-- board:start -->", "<!-- board:end -->"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("user")
    ap.add_argument("out_dir")
    ap.add_argument("--theme", default="blueprint", choices=sorted(THEMES))
    ap.add_argument("--cache")
    ap.add_argument("--base", default=".")
    ap.add_argument("--skills")
    ap.add_argument("--readme", help="rewrite the block between the board markers in this file")
    args = ap.parse_args()
    block = build(args.user, args.out_dir, args.theme, args.cache, args.base, args.skills)
    if args.readme:
        text = open(args.readme).read()
        if START in text and END in text:
            text = text[:text.index(START)] + START + "\n" + block + "\n" + text[text.index(END):]
        else:
            text = f"{START}\n{block}\n{END}\n"
        with open(args.readme, "w") as f:
            f.write(text)
    else:
        print(block)


if __name__ == "__main__":
    main()
