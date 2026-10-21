"""Circuit-board contribution graph: robots relay a data packet across a PCB.

Every day is a pad on the board; days with contributions are LEDs. A copper
trace snakes through the LEDs week by week, from a power header to a CPU.
A team of robots relays a glowing packet along the trace: each one drives its
leg, hands the packet to the next robot, then rolls back to its dock. LEDs
light up as the packet passes, the trace energises behind it, and once the
packet reaches the CPU the whole board pulses before the loop restarts.

Pure SVG + SMIL, so it animates inside a GitHub README <img>.

usage: python circuit.py USER OUT_DIR [--cache file.json]
writes OUT_DIR/circuit-board.svg (green PCB) and OUT_DIR/circuit-board-dark.svg
"""
import argparse
import math
import os

from contrib import fetch
from smil import finalize

CELL, STEP = 12, 16
LEFT, TOP, RIGHT, BOTTOM = 78, 66, 118, 46
SPEED = 120.0         # px/s along the trace
HOLD = 3.5            # seconds the board stays lit at the end of a loop
N_ROBOTS = 4
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

THEMES = {
    "dark": dict(board="#06120d", edge="#1f4d36", grid="#0c2219", silk="#9fb8ac",
                 copper="#6b5426", pad="#3b3218", led_off="#0f2a22",
                 lit=["#0b6e86", "#06a3c4", "#22d3ee", "#a5f3fc"],
                 energy="#22d3ee", chip="#10161c", chip_edge="#2d3a44"),
    "light": dict(board="#145a36", edge="#0d3f25", grid="#1a6a41", silk="#e8f5ec",
                  copper="#c08a2e", pad="#d4a94c", led_off="#0f4a2c",
                  lit=["#0b6e86", "#06a3c4", "#22d3ee", "#a5f3fc"],
                  energy="#7df9ff", chip="#15191d", chip_edge="#3b4650"),
}
ROBOT_COLORS = ["#22d3ee", "#f472b6", "#facc15", "#a3e635", "#c084fc", "#fb923c"]


def cell_center(w, d):
    return LEFT + w * STEP + CELL / 2, TOP + d * STEP + CELL / 2


# ---------- route geometry ----------

def l_route(p, q, chamfer=5.0):
    """Horizontal-then-vertical PCB trace from p to q with a 45° corner."""
    (x1, y1), (x2, y2) = p, q
    if x1 == x2 or y1 == y2:
        return [q]
    c = min(chamfer, abs(x2 - x1), abs(y2 - y1))
    sx = math.copysign(1, x2 - x1)
    sy = math.copysign(1, y2 - y1)
    return [(x2 - sx * c, y1), (x2, y1 + sy * c), q]


def build_route(weeks, start, end, center=None):
    center = center or cell_center
    pts = [start]
    stops = []                    # (point index, week, day) for each LED
    for w, week in enumerate(weeks):
        active = [d["weekday"] for d in week if d["count"]]
        if not active:
            continue
        cy = pts[-1][1]
        # visit the column top-down or bottom-up, whichever starts nearer
        if abs(center(w, active[-1])[1] - cy) < abs(center(w, active[0])[1] - cy):
            active.reverse()
        for d in active:
            pts += l_route(pts[-1], center(w, d))
            stops.append((len(pts) - 1, w, d))
    pts += l_route(pts[-1], end)
    return pts, stops


def cumulative(pts):
    out = [0.0]
    for a, b in zip(pts, pts[1:]):
        out.append(out[-1] + math.dist(a, b))
    return out


def point_at(pts, cum, s):
    for i in range(1, len(pts)):
        if cum[i] >= s:
            seg = cum[i] - cum[i - 1] or 1
            t = (s - cum[i - 1]) / seg
            (x1, y1), (x2, y2) = pts[i - 1], pts[i]
            return (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t), i
    return pts[-1], len(pts) - 1


def sub_path(pts, cum, s0, s1):
    p0, i0 = point_at(pts, cum, s0)
    p1, i1 = point_at(pts, cum, s1)
    return [p0] + pts[i0:i1] + [p1]


def d_attr(pts):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def kt(values):
    """Format keyTimes, clamped to [0,1] and strictly non-decreasing."""
    out, last = [], 0.0
    for v in values:
        v = min(1.0, max(last, v))
        out.append(v)
        last = v
    return ";".join(f"{v:.4f}" for v in out)


# ---------- sprites ----------

def robot(i, color):
    """Side-view robot on tracks; origin = where the tracks touch the trace."""
    blink_delay = 0.7 * i
    return f'''
  <g class="robot" transform="scale(1.35)">
    <ellipse cx="0" cy="1.5" rx="10" ry="2" fill="#000" opacity="0.35"/>
    <rect x="-9" y="-6" width="18" height="6" rx="3" fill="#1f2933" stroke="#4b5563" stroke-width="0.8"/>
    <g transform="translate(-5,-3)"><circle r="2.3" fill="#374151"/>
      <line x1="-2" y1="0" x2="2" y2="0" stroke="#9ca3af" stroke-width="0.8">
        <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="0.6s" repeatCount="indefinite"/></line></g>
    <g transform="translate(5,-3)"><circle r="2.3" fill="#374151"/>
      <line x1="-2" y1="0" x2="2" y2="0" stroke="#9ca3af" stroke-width="0.8">
        <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="0.6s" repeatCount="indefinite"/></line></g>
    <rect x="-7" y="-17" width="14" height="11" rx="2.5" fill="#d1d5db" stroke="#6b7280" stroke-width="0.8"/>
    <rect x="-4" y="-14" width="8" height="5" rx="1" fill="#111827"/>
    <text x="0" y="-10.2" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="4.2" font-weight="700" fill="{color}" text-anchor="middle">R{i + 1}</text>
    <rect x="-6" y="-26" width="12" height="8.5" rx="2.5" fill="#e5e7eb" stroke="#6b7280" stroke-width="0.8"/>
    <rect x="-4.5" y="-24" width="9" height="4.5" rx="1.5" fill="#0b1220"/>
    <g fill="{color}">
      <rect x="-3.2" y="-23.2" width="2.2" height="2.8" rx="0.8">
        <animate attributeName="height" values="2.8;2.8;0.3;2.8" keyTimes="0;0.9;0.95;1" dur="3.1s" begin="{blink_delay}s" repeatCount="indefinite"/></rect>
      <rect x="1" y="-23.2" width="2.2" height="2.8" rx="0.8">
        <animate attributeName="height" values="2.8;2.8;0.3;2.8" keyTimes="0;0.9;0.95;1" dur="3.1s" begin="{blink_delay}s" repeatCount="indefinite"/></rect>
    </g>
    <line x1="0" y1="-26" x2="0" y2="-30" stroke="#6b7280" stroke-width="0.9"/>
    <circle cx="0" cy="-31" r="1.6" fill="{color}">
      <animate attributeName="opacity" values="1;0.25;1" dur="1.2s" begin="{blink_delay / 2}s" repeatCount="indefinite"/></circle>
    <rect x="-9.5" y="-15" width="2.5" height="7" rx="1.2" fill="#9ca3af"/>
    <rect x="7" y="-15" width="2.5" height="7" rx="1.2" fill="#9ca3af"/>
  </g>'''


def header_pins(x, y, n=4):
    out = [f'<rect x="{x - 9}" y="{y - n * 6}" width="18" height="{n * 12}" rx="2" fill="#111" stroke="#333"/>']
    for k in range(n):
        out.append(f'<rect x="{x - 3}" y="{y - n * 6 + 3 + k * 12}" width="6" height="6" fill="#c9a227"/>')
    return "\n  ".join(out)


def chip(x, y, w, h, t, label, sub, core_anim):
    pins = []
    for k in range(6):
        py = y + 10 + k * (h - 20) / 5
        pins.append(f'<rect x="{x - 5}" y="{py - 1.5:.1f}" width="5" height="3" fill="{t["pad"]}"/>')
        pins.append(f'<rect x="{x + w}" y="{py - 1.5:.1f}" width="5" height="3" fill="{t["pad"]}"/>')
    for k in range(5):
        px = x + 10 + k * (w - 20) / 4
        pins.append(f'<rect x="{px - 1.5:.1f}" y="{y - 5}" width="3" height="5" fill="{t["pad"]}"/>')
        pins.append(f'<rect x="{px - 1.5:.1f}" y="{y + h}" width="3" height="5" fill="{t["pad"]}"/>')
    return f'''
  {''.join(pins)}
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{t["chip"]}" stroke="{t["chip_edge"]}"/>
  <circle cx="{x + 7}" cy="{y + 7}" r="2" fill="{t["chip_edge"]}"/>
  <rect x="{x + w / 2 - 14}" y="{y + h / 2 - 20}" width="28" height="22" rx="3" fill="{t["energy"]}" opacity="0.08" filter="url(#glow)">{core_anim}</rect>
  <text x="{x + w / 2}" y="{y + h / 2 + 18}" class="silk" font-size="9" font-weight="700" text-anchor="middle" fill="#e5e7eb">{label}</text>
  <text x="{x + w / 2}" y="{y + h / 2 + 29}" class="silk" font-size="6.5" text-anchor="middle" fill="#9ca3af">{sub}</text>'''


# ---------- main render ----------

def render(data, theme):
    t = THEMES[theme]
    weeks = data["weeks"]
    nw = len(weeks)
    W = LEFT + nw * STEP + RIGHT
    H = TOP + 7 * STEP + BOTTOM
    start = (LEFT - 34, TOP + 3 * STEP + CELL / 2)
    cpu_x, cpu_y, cpu_w, cpu_h = LEFT + nw * STEP + 22, TOP + 4, 74, 7 * STEP - 12
    end = (cpu_x - 5, TOP + 3 * STEP + CELL / 2)

    pts, stops = build_route(weeks, start, end)
    cum = cumulative(pts)
    L = cum[-1]
    move = L / SPEED
    D = move + HOLD
    m = move / D                      # fraction of the loop spent moving
    frac = lambda s: (s / L) * m      # route distance -> loop fraction

    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
      f'role="img" aria-label="{data["login"]}\'s contributions as a circuit board relayed by robots">')
    a(f'''<defs>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="bigglow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="4"/></filter>
  <pattern id="grid" width="8" height="8" patternUnits="userSpaceOnUse">
    <path d="M8 0H0V8" fill="none" stroke="{t["grid"]}" stroke-width="0.6"/></pattern>
  <style>.silk{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:{t["silk"]}}}</style>
</defs>''')

    # board
    a(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="{t["board"]}" stroke="{t["edge"]}" stroke-width="2"/>')
    a(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="url(#grid)" opacity="0.6"/>')
    for hx, hy in [(14, 14), (W - 14, 14), (14, H - 14), (W - 14, H - 14)]:
        a(f'<circle cx="{hx}" cy="{hy}" r="5.5" fill="none" stroke="{t["pad"]}" stroke-width="2"/>'
          f'<circle cx="{hx}" cy="{hy}" r="3" fill="#000" opacity="0.6"/>')

    # silkscreen
    a(f'<text x="28" y="24" class="silk" font-size="10" font-weight="700" letter-spacing="1.5">'
      f'{data["login"].upper()} // CONTRIBUTION BUS</text>')
    a(f'<text x="{W - 28}" y="24" class="silk" font-size="8.5" text-anchor="end" opacity="0.8">'
      f'{data["total"]} commits · {data["active_days"]} active days · REV {weeks[-1][-1]["date"][:4]}</text>')
    last = None
    for w, week in enumerate(weeks):
        mo = int(week[0]["date"][5:7])
        if mo != last and week[0]["date"][8:10] <= "07":
            a(f'<text x="{LEFT + w * STEP}" y="{TOP - 8}" class="silk" font-size="8" opacity="0.75">{MONTHS[mo - 1]}</text>')
        last = mo
    a(f'<text x="28" y="{H - 16}" class="silk" font-size="7.5" opacity="0.7">'
      f'1 LED = 1 day · brightness = activity · robots R1–R{N_ROBOTS} relay the packet to the CPU</text>')

    # power header + CPU
    a(header_pins(start[0] - 4, start[1]))
    a(f'<text x="{start[0] - 4}" y="{start[1] + 36}" class="silk" font-size="7" text-anchor="middle">PWR</text>')
    t_end = m
    core = (f'<animate attributeName="opacity" values="0.08;0.08;0.9;0.5;0.9;0.08" '
            f'keyTimes="{kt([0, t_end, t_end + 0.02, t_end + 0.06, t_end + 0.1, 1])}" dur="{D:.2f}s" repeatCount="indefinite"/>')
    a(chip(cpu_x, cpu_y, cpu_w, cpu_h, t, "KT-42", "NEURAL CPU", core))

    # pads for all days
    active = {(w, d) for _, w, d in stops}
    for w, week in enumerate(weeks):
        for d in week:
            x, y = cell_center(w, d["weekday"])
            if (w, d["weekday"]) in active:
                continue
            a(f'<circle cx="{x}" cy="{y}" r="2.1" fill="{t["pad"]}" opacity="0.55"/>')

    # copper trace + energised overlay that follows the packet
    a(f'<path d="{d_attr(pts)}" fill="none" stroke="{t["copper"]}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>')
    a(f'<path d="{d_attr(pts)}" fill="none" stroke="{t["energy"]}" stroke-width="1.6" stroke-linejoin="round" '
      f'stroke-linecap="round" stroke-dasharray="{L:.1f} {L + 6:.1f}" stroke-dashoffset="{L:.1f}" filter="url(#glow)" opacity="0.9">'
      f'<animate attributeName="stroke-dashoffset" values="{L:.1f};0;0;{L:.1f}" keyTimes="{kt([0, m, 0.97, 1])}" '
      f'dur="{D:.2f}s" repeatCount="indefinite"/></path>')

    # LEDs
    for idx, w, d in stops:
        x, y = pts[idx]
        lvl = next(dd["level"] for dd in weeks[w] if dd["weekday"] == d)
        col = t["lit"][max(lvl, 1) - 1]
        ft = frac(cum[idx])
        a(f'<rect x="{x - CELL / 2}" y="{y - CELL / 2}" width="{CELL}" height="{CELL}" rx="3" fill="{t["led_off"]}" stroke="{t["copper"]}" stroke-width="1"/>')
        a(f'<rect x="{x - CELL / 2 + 1}" y="{y - CELL / 2 + 1}" width="{CELL - 2}" height="{CELL - 2}" rx="2.5" fill="{col}" opacity="0.22" filter="url(#glow)">'
          f'<animate attributeName="opacity" values="0.22;0.22;1;0.9;0.9;0.22" '
          f'keyTimes="{kt([0, ft, ft + 0.004, ft + 0.03, 0.97, 1])}" dur="{D:.2f}s" repeatCount="indefinite"/></rect>')

    # relay legs: split the route into equal-length legs, one per robot
    legs = [(L * k / N_ROBOTS, L * (k + 1) / N_ROBOTS) for k in range(N_ROBOTS)]
    for k, (s0, s1) in enumerate(legs):
        f0, f1 = frac(s0), frac(s1)
        back = f1 + (f1 - f0) * 0.55            # roll home at ~1.8x speed
        if k == N_ROBOTS - 1:
            back = min(back, 0.995)
        leg = sub_path(pts, cum, s0, s1)
        a(f'<g>{robot(k, ROBOT_COLORS[k % len(ROBOT_COLORS)])}'
          f'<animateMotion path="{d_attr(leg)}" keyPoints="0;0;1;1;0;0" keyTimes="{kt([0, f0, f1, f1 + 0.01, back, 1])}" '
          f'calcMode="linear" dur="{D:.2f}s" repeatCount="indefinite"/></g>')
        # spark at each hand-off point
        if k > 0:
            (hx, hy), _ = point_at(pts, cum, s0)
            a(f'<circle cx="{hx:.1f}" cy="{hy - 26:.1f}" r="12" fill="{t["energy"]}" opacity="0" filter="url(#bigglow)">'
              f'<animate attributeName="opacity" values="0;0;0.9;0;0" keyTimes="{kt([0, f0 - 0.004, f0, f0 + 0.02, 1])}" '
              f'dur="{D:.2f}s" repeatCount="indefinite"/></circle>')

    # the packet, carried just above the robots' heads
    a(f'''<g>
  <g transform="translate(0,-51)">
    <circle r="7" fill="{t["energy"]}" opacity="0.35" filter="url(#bigglow)"/>
    <rect x="-3.5" y="-3.5" width="7" height="7" rx="1.5" fill="#ecfeff" stroke="{t["energy"]}" stroke-width="1.2" transform="rotate(45)">
      <animateTransform attributeName="transform" type="rotate" from="45" to="405" dur="2s" repeatCount="indefinite"/></rect>
  </g>
  <animate attributeName="opacity" values="1;1;0;0;1" keyTimes="{kt([0, m, m + 0.01, 0.99, 1])}" dur="{D:.2f}s" repeatCount="indefinite"/>
  <animateMotion path="{d_attr(pts)}" keyPoints="0;1;1" keyTimes="{kt([0, m, 1])}" calcMode="linear" dur="{D:.2f}s" repeatCount="indefinite"/>
</g>''')

    a('</svg>')
    return finalize("\n".join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("user")
    ap.add_argument("out_dir")
    ap.add_argument("--cache")
    args = ap.parse_args()
    data = fetch(args.user, args.cache)
    os.makedirs(args.out_dir, exist_ok=True)
    for theme, name in [("light", "circuit-board.svg"), ("dark", "circuit-board-dark.svg")]:
        with open(os.path.join(args.out_dir, name), "w") as f:
            f.write(render(data, theme))
    print(f"circuit: {data['active_days']} LEDs, {data['total']} contributions")


if __name__ == "__main__":
    main()
