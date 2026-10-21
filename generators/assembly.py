"""Assembly Line: blueprint arms + PCB relay robots in one loop.

1. LOADER arm picks a power cell from the feeder and plugs it into the PWR socket.
2. The board powers up; robots R1-R4 relay the data packet across the
   contribution trace, lighting each day's LED on the way.
3. At the CPU the packet is processed and handed to the DEPLOYER arm, which
   drops it into the deploy bin. Then everything resets.

usage: python assembly.py USER OUT_DIR [--cache file.json]  ->  OUT_DIR/assembly-line.svg
"""
import argparse
import os

from arm import gripper_arm
from circuit import (MONTHS, ROBOT_COLORS, build_route, cumulative, d_attr,
                     point_at, robot, sub_path)
from contrib import fetch
from smil import finalize

W, H = 900, 400
CELL, STEP = 10, 13
GX0, GY0 = 100, 252                 # contribution grid origin
BOARD = (22, 214, 878, 378)         # x0, y0, x1, y1
SPEED = 125.0
N_ROBOTS = 4
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
BP = dict(bg="#0b2747", ink="#e6f0ff", soft="#9cc2ee")
PCB = dict(board="#06120d", edge="#1f4d36", grid="#0c2219", pad="#5c4a1e", copper="#8a6a2c",
           led_off="#0f2a22", lit=["#0b6e86", "#06a3c4", "#22d3ee", "#a5f3fc"], energy="#22d3ee", silk="#9fb8ac")

LOADER = dict(base=(118, 150), l1=74, l2=64, grip=24)
DEPLOYER = dict(base=(782, 150), l1=74, l2=64, grip=24)
FEEDER = (44, 160)                  # grip centre when holding the cell on the feeder
SOCKET = (60, 296)                  # PWR socket on the board
CPU = (796, 262, 66, 76)            # x, y, w, h
OUT_PAD = (829, 252)                # packet waits here for the deployer
BIN = (866, 150)


def kt(times, dur):
    out, last = [], 0.0
    for t in times:
        v = min(1.0, max(last, t / dur))
        out.append(v)
        last = v
    return ";".join(f"{v:.4f}" for v in out)


CELL_SVG = ('<rect x="-7" y="-11" width="14" height="22" rx="2.5" fill="#14532d" stroke="#4ade80" stroke-width="1.2"/>'
            '<rect x="-3" y="-14" width="6" height="3" rx="1" fill="#4ade80"/>'
            '<path d="M1 -7 L-3 1 L0 1 L-1 7 L3 -1 L0 -1 Z" fill="#bbf7d0"/>')
PACKET_SVG = ('<circle r="8" fill="#22d3ee" opacity="0.3" filter="url(#bigglow)"/>'
              '<rect x="-4" y="-4" width="8" height="8" rx="1.5" fill="#ecfeff" stroke="#22d3ee" stroke-width="1.3" transform="rotate(45)"/>')


def finale(d, pts, stops, t_b0, t_b1, D, dur, tx0, ty0, tw):
    """Packet flies from the bin into the title block, the board answers with a wave."""
    o = []
    a = o.append
    p0, c, p1 = (BIN[0], BIN[1]), (770, -40), (tx0 + tw / 2, ty0 + 26)
    curve = [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u * u * p1[0],
              (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u * u * p1[1]) for u in [i / 60 for i in range(61)]]
    ln = sum(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 for (x1, y1), (x2, y2) in zip(curve, curve[1:]))
    path = f"M{p0[0]},{p0[1]} Q{c[0]},{c[1]} {p1[0]},{p1[1]}"
    a(f'<path d="{path}" fill="none" stroke="#22d3ee" stroke-width="2" stroke-linecap="round" filter="url(#glow)" '
      f'stroke-dasharray="{ln:.0f} {ln + 6:.0f}" stroke-dashoffset="{ln:.0f}" opacity="0">'
      f'<animate attributeName="stroke-dashoffset" values="{ln:.0f};{ln:.0f};0;0" keyTimes="{kt([0, t_b0, t_b1, D], D)}" {dur}/>'
      f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="{kt([0, t_b0 - 0.01, t_b0, t_b1, t_b1 + 0.6, D], D)}" {dur}/></path>')
    a(f'<g opacity="0"><g transform="scale(1.4)">{PACKET_SVG}</g>'
      f'<animate attributeName="opacity" values="0;1;0" keyTimes="{kt([0, t_b0, t_b1], D)}" calcMode="discrete" {dur}/>'
      f'<animateMotion path="{path}" keyPoints="0;0;1;1" keyTimes="{kt([0, t_b0, t_b1, D], D)}" calcMode="spline" '
      f'keySplines="0 0 1 1;0.5 0 0.6 1;0 0 1 1" {dur}/></g>')
    a(f'<circle cx="{p1[0]}" cy="{p1[1]}" r="4" fill="none" stroke="#22d3ee" stroke-width="2.5" opacity="0" filter="url(#glow)">'
      f'<animate attributeName="r" values="4;4;90;90" keyTimes="{kt([0, t_b1, t_b1 + 0.7, D], D)}" {dur}/>'
      f'<animate attributeName="opacity" values="0;0;1;0;0" keyTimes="{kt([0, t_b1 - 0.01, t_b1, t_b1 + 0.7, D], D)}" {dur}/></circle>')
    flash = f'values="0;0;1;0.5;1;0;0" keyTimes="{kt([0, t_b1, t_b1 + 0.1, t_b1 + 0.35, t_b1 + 0.55, t_b1 + 1.5, D], D)}" {dur}'
    a(f'<rect x="{tx0}" y="{ty0}" width="{tw}" height="150" fill="#22d3ee" fill-opacity="0.07" stroke="#22d3ee" stroke-width="2.5" '
      f'filter="url(#glow)" opacity="0"><animate attributeName="opacity" {flash}/></rect>')
    a(f'<text x="{tx0 + 14}" y="{ty0 + 30}" class="t" font-size="20" font-weight="700" fill="#a5f3fc" letter-spacing="3" '
      f'filter="url(#glow)" opacity="0">{d["name"].upper()}<animate attributeName="opacity" {flash}/></text>')
    # light wave runs back from the CPU to the power socket
    span = GX0 + len(d["weeks"]) * STEP - GX0
    for idx, _, _ in stops:
        x, y = pts[idx]
        tw_ = t_b1 + 0.15 + (1 - (x - GX0) / span) * 1.0
        a(f'<rect x="{x - CELL / 2}" y="{y - CELL / 2}" width="{CELL}" height="{CELL}" rx="2.5" fill="#f0fdff" opacity="0" filter="url(#glow)">'
          f'<animate attributeName="opacity" values="0;0;1;0;0" keyTimes="{kt([0, tw_ - 0.01, tw_, tw_ + 0.35, D], D)}" {dur}/></rect>')
    sx, sy = SOCKET
    t_pwr = t_b1 + 1.2
    a(f'<rect x="{sx - 12}" y="{sy - 18}" width="24" height="36" rx="3" fill="#4ade80" opacity="0" filter="url(#bigglow)">'
      f'<animate attributeName="opacity" values="0;0;1;0;0" keyTimes="{kt([0, t_pwr - 0.01, t_pwr, t_pwr + 0.5, D], D)}" {dur}/></rect>')
    return "\n".join(o)


def render(d):
    weeks = d["weeks"]
    center = lambda w, day: (GX0 + w * STEP + CELL / 2, GY0 + day * STEP + CELL / 2)
    cpu_x, cpu_y, cpu_w, cpu_h = CPU
    start = (SOCKET[0] + 12, GY0 + 3 * STEP + CELL / 2)
    end = (cpu_x - 5, GY0 + 3 * STEP + CELL / 2)
    pts, stops = build_route(weeks, start, end, center)
    cum = cumulative(pts)
    L = cum[-1]

    # ---- timeline (seconds) ----
    t_power = 3.4
    M = L / SPEED
    t_cpu = t_power + M
    t_dep = t_cpu + 2.4                                 # packet lands in the bin
    t_b0, t_b1 = t_dep + 0.15, t_dep + 1.0              # packet launches back to the title block
    D = t_b1 + 2.2
    dur = f'dur="{D:.2f}s" repeatCount="indefinite"'
    rf = lambda s: (t_power + s / L * M) / D            # route distance -> loop fraction

    lb, db = LOADER["base"], DEPLOYER["base"]
    loader_keys = [
        (0.0, (150, 96), False), (0.5, (FEEDER[0], FEEDER[1] - 40), False), (1.0, FEEDER, False),
        (1.25, FEEDER, True), (1.7, (FEEDER[0], FEEDER[1] - 40), True), (2.6, (SOCKET[0], SOCKET[1] - 44), True),
        (3.1, SOCKET, True), (3.35, SOCKET, False), (3.8, (SOCKET[0], SOCKET[1] - 44), False),
        (4.6, (150, 96), False), (D, (150, 96), False)]
    deploy_keys = [
        (0.0, (752, 96), False), (t_cpu - 1.3, (752, 96), False), (t_cpu - 0.2, (OUT_PAD[0], OUT_PAD[1] - 36), False),
        (t_cpu + 0.2, OUT_PAD, False), (t_cpu + 0.45, OUT_PAD, True), (t_cpu + 0.9, (OUT_PAD[0], OUT_PAD[1] - 40), True),
        (t_cpu + 1.8, (BIN[0], BIN[1] - 40), True), (t_cpu + 2.2, (BIN[0], BIN[1] - 6), True),
        (t_cpu + 2.4, (BIN[0], BIN[1] - 6), False), (t_cpu + 2.9, (BIN[0], BIN[1] - 46), False),
        (t_cpu + 3.7, (752, 96), False), (D, (752, 96), False)]

    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
      f'aria-label="{d["name"]}">')
    a(f'''<defs>
<style>.t{{font-family:{FONT}}} .silk{{font-family:{FONT};fill:{PCB["silk"]}}}</style>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/>
  <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="bigglow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="4"/></filter>
<pattern id="bpgrid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M10 0H0V10" fill="none" stroke="{BP["soft"]}" stroke-opacity="0.08"/></pattern>
<pattern id="bpmajor" width="50" height="50" patternUnits="userSpaceOnUse"><path d="M50 0H0V50" fill="none" stroke="{BP["soft"]}" stroke-opacity="0.17"/></pattern>
<pattern id="pcbgrid" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M8 0H0V8" fill="none" stroke="{PCB["grid"]}" stroke-width="0.6"/></pattern>
<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="{BP["soft"]}"/></pattern>
</defs>''')
    a(f'<rect width="{W}" height="{H}" rx="12" fill="{BP["bg"]}"/><rect width="{W}" height="{H}" rx="12" fill="url(#bpgrid)"/>'
      f'<rect width="{W}" height="{H}" rx="12" fill="url(#bpmajor)"/>')

    # ---- title block --------------------------------------------------
    tx0, ty0, tw = 262, 16, 376
    a(f'<rect x="{tx0}" y="{ty0}" width="{tw}" height="150" fill="{BP["bg"]}" fill-opacity="0.7" stroke="{BP["ink"]}" stroke-width="1.4"/>')
    a(f'<text x="{tx0 + 14}" y="{ty0 + 30}" class="t" font-size="20" font-weight="700" fill="{BP["ink"]}" letter-spacing="3">{d["name"].upper()}</text>')
    a(f'<text x="{tx0 + 14}" y="{ty0 + 47}" class="t" font-size="8.5" fill="{BP["soft"]}" letter-spacing="1.4">ROBOTICS ENGINEER · 42 BERLIN · ASSEMBLY LINE KT-42</text>')
    a(f'<line x1="{tx0}" y1="{ty0 + 58}" x2="{tx0 + tw}" y2="{ty0 + 58}" stroke="{BP["ink"]}"/>')
    stats = [("CONTRIB", d["total"]), ("ACTIVE", f'{d["active_days"]} D'), ("STREAK", f'{d["longest_streak"]} D'), ("REPOS", d["repo_count"])]
    for i, (k, v) in enumerate(stats):
        x = tx0 + i * tw / 4
        if i:
            a(f'<line x1="{x}" y1="{ty0 + 58}" x2="{x}" y2="{ty0 + 102}" stroke="{BP["soft"]}" stroke-width="0.8"/>')
        a(f'<text x="{x + 10}" y="{ty0 + 74}" class="t" font-size="7.5" fill="{BP["soft"]}">{k}</text>'
          f'<text x="{x + 10}" y="{ty0 + 94}" class="t" font-size="15" font-weight="700" fill="{BP["ink"]}">{v}</text>')
    a(f'<line x1="{tx0}" y1="{ty0 + 102}" x2="{tx0 + tw}" y2="{ty0 + 102}" stroke="{BP["ink"]}"/>')
    phases = [("01 LOAD", 0, t_power), ("02 RELAY", t_power, t_cpu), ("03 DEPLOY", t_cpu, t_b1)]
    for i, (label, p0, p1) in enumerate(phases):
        x = tx0 + 12 + i * 120
        a(f'<rect x="{x}" y="{ty0 + 114}" width="110" height="24" rx="4" fill="none" stroke="{BP["soft"]}" stroke-width="0.8"/>')
        a(f'<rect x="{x}" y="{ty0 + 114}" width="110" height="24" rx="4" fill="#fbbf24" opacity="0">'
          f'<animate attributeName="opacity" values="0;0.9;0;0.9;0" keyTimes="{kt([0, p0, p1, t_b1, D - 0.3], D)}" calcMode="discrete" {dur}/></rect>')
        a(f'<text x="{x + 55}" y="{ty0 + 130}" class="t" font-size="10" font-weight="700" fill="{BP["ink"]}" text-anchor="middle" letter-spacing="1.5">{label}</text>')

    # ---- station labels + fixtures -------------------------------------
    for x, y, txt, anchor in [(22, 34, "STAGE 01 · LOADER", "start"), (W - 22, 34, "STAGE 03 · DEPLOYER", "end")]:
        a(f'<text x="{x}" y="{y}" class="t" font-size="9" font-weight="700" fill="{BP["ink"]}" letter-spacing="1.5" text-anchor="{anchor}">{txt}</text>')
    a(f'<text x="22" y="48" class="t" font-size="7.5" fill="{BP["soft"]}">2-DOF · L1 {LOADER["l1"]} · L2 {LOADER["l2"]}</text>')
    a(f'<text x="{W - 22}" y="48" class="t" font-size="7.5" fill="{BP["soft"]}" text-anchor="end">2-DOF · L1 {DEPLOYER["l1"]} · L2 {DEPLOYER["l2"]}</text>')
    for (bx, by) in (lb, db):
        a(f'<path d="M{bx - 22} {by + 46} L{bx - 13} {by + 8} L{bx + 13} {by + 8} L{bx + 22} {by + 46} Z" fill="{BP["bg"]}" stroke="{BP["ink"]}" stroke-width="1.4"/>'
          f'<rect x="{bx - 30}" y="{by + 46}" width="60" height="6" fill="url(#hatch)" stroke="{BP["ink"]}"/>')
    # feeder tray + deploy bin
    a(f'<rect x="{FEEDER[0] - 16}" y="{FEEDER[1] + 12}" width="32" height="8" fill="url(#hatch)" stroke="{BP["ink"]}"/>'
      f'<text x="{FEEDER[0]}" y="{FEEDER[1] + 32}" class="t" font-size="7" fill="{BP["soft"]}" text-anchor="middle">CELL FEEDER</text>')
    bx, by = BIN
    a(f'<path d="M{bx - 18} {by - 14} L{bx - 14} {by + 16} L{bx + 14} {by + 16} L{bx + 18} {by - 14}" fill="none" stroke="{BP["ink"]}" stroke-width="1.4"/>'
      f'<text x="{bx}" y="{by + 30}" class="t" font-size="7" fill="{BP["soft"]}" text-anchor="middle">DEPLOY</text>')
    a(f'<rect x="{bx - 14}" y="{by - 12}" width="28" height="27" fill="#22d3ee" opacity="0" filter="url(#bigglow)">'
      f'<animate attributeName="opacity" values="0;0;0.9;0.25;0" keyTimes="{kt([0, t_cpu + 2.35, t_cpu + 2.45, t_cpu + 3.0, D], D)}" {dur}/></rect>')

    # ---- the PCB ---------------------------------------------------------
    x0, y0, x1, y1 = BOARD
    a(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="12" fill="{PCB["board"]}" stroke="{PCB["edge"]}" stroke-width="2"/>'
      f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="12" fill="url(#pcbgrid)" opacity="0.7"/>')
    last = None
    for w, week in enumerate(weeks):
        mo = int(week[0]["date"][5:7])
        if mo != last and week[0]["date"][8:10] <= "07":
            a(f'<text x="{GX0 + w * STEP}" y="{GY0 - 7}" class="silk" font-size="7">{MONTHS[mo - 1]}</text>')
        last = mo
    active = {(w, day) for _, w, day in stops}
    for w, week in enumerate(weeks):
        for dd in week:
            if (w, dd["weekday"]) not in active:
                x, y = center(w, dd["weekday"])
                a(f'<circle cx="{x}" cy="{y}" r="1.8" fill="{PCB["pad"]}"/>')
    a(f'<path d="{d_attr(pts)}" fill="none" stroke="{PCB["copper"]}" stroke-width="2.2" stroke-linejoin="round"/>')
    a(f'<path d="{d_attr(pts)}" fill="none" stroke="{PCB["energy"]}" stroke-width="1.5" stroke-linejoin="round" filter="url(#glow)" '
      f'stroke-dasharray="{L:.0f} {L + 6:.0f}" stroke-dashoffset="{L:.0f}"><animate attributeName="stroke-dashoffset" '
      f'values="{L:.0f};{L:.0f};0;0;{L:.0f}" keyTimes="{kt([0, t_power, t_cpu, D - 0.6, D], D)}" {dur}/></path>')
    for idx, w, day in stops:
        x, y = pts[idx]
        lvl = next(dd["level"] for dd in weeks[w] if dd["weekday"] == day)
        ft = rf(cum[idx])
        a(f'<rect x="{x - CELL / 2}" y="{y - CELL / 2}" width="{CELL}" height="{CELL}" rx="2.5" fill="{PCB["led_off"]}" stroke="{PCB["copper"]}" stroke-width="0.9"/>'
          f'<rect x="{x - CELL / 2 + 1}" y="{y - CELL / 2 + 1}" width="{CELL - 2}" height="{CELL - 2}" rx="2" fill="{PCB["lit"][max(lvl, 1) - 1]}" opacity="0.15" filter="url(#glow)">'
          f'<animate attributeName="opacity" values="0.15;0.15;1;0.88;0.88;0.15" keyTimes="{kt([0, ft * D, ft * D + 0.1, ft * D + 0.6, D - 0.6, D], D)}" {dur}/></rect>')

    # PWR socket (cell sits here once plugged) and CPU
    sx, sy = SOCKET
    a(f'<rect x="{sx - 12}" y="{sy - 18}" width="24" height="36" rx="3" fill="#111" stroke="#c9a227" stroke-width="1.2"/>'
      f'<text x="{sx}" y="{sy + 30}" class="silk" font-size="7" text-anchor="middle">PWR</text>')
    a(f'<rect x="{sx - 12}" y="{sy - 18}" width="24" height="36" rx="3" fill="#4ade80" opacity="0" filter="url(#bigglow)">'
      f'<animate attributeName="opacity" values="0;0;0.8;0.35;0.35;0" keyTimes="{kt([0, t_power - 0.05, t_power, t_power + 0.4, D - 0.6, D], D)}" {dur}/></rect>')
    a(f'<g transform="translate({sx},{sy})" opacity="0">{CELL_SVG}<animate attributeName="opacity" values="0;1;0" '
      f'keyTimes="{kt([0, 3.35, D - 0.5], D)}" calcMode="discrete" {dur}/></g>')
    a(f'<g transform="translate({FEEDER[0]},{FEEDER[1]})">{CELL_SVG}<animate attributeName="opacity" values="1;0;1" '
      f'keyTimes="{kt([0, 1.25, D - 0.5], D)}" calcMode="discrete" {dur}/></g>')
    pins = ""
    for k in range(5):
        py = cpu_y + 10 + k * (cpu_h - 20) / 4
        pins += f'<rect x="{cpu_x - 5}" y="{py - 1.5:.1f}" width="5" height="3" fill="#c9a227"/><rect x="{cpu_x + cpu_w}" y="{py - 1.5:.1f}" width="5" height="3" fill="#c9a227"/>'
    a(pins + f'<rect x="{cpu_x}" y="{cpu_y}" width="{cpu_w}" height="{cpu_h}" rx="4" fill="#10161c" stroke="#2d3a44"/>'
      f'<text x="{cpu_x + cpu_w / 2}" y="{cpu_y + cpu_h - 22}" class="t" font-size="9" font-weight="700" fill="#e5e7eb" text-anchor="middle">KT-42</text>'
      f'<text x="{cpu_x + cpu_w / 2}" y="{cpu_y + cpu_h - 11}" class="t" font-size="6" fill="#9ca3af" text-anchor="middle">CPU</text>'
      f'<rect x="{cpu_x + 18}" y="{cpu_y + 24}" width="30" height="20" rx="3" fill="#22d3ee" opacity="0.06" filter="url(#glow)">'
      f'<animate attributeName="opacity" values="0.06;0.06;0.9;0.06;0.06" keyTimes="{kt([0, t_cpu - 0.05, t_cpu + 0.2, t_cpu + 1.2, D], D)}" {dur}/></rect>'
      f'<rect x="{OUT_PAD[0] - 8}" y="{OUT_PAD[1] - 3}" width="16" height="6" rx="1.5" fill="#c9a227"/>'
      f'<text x="{OUT_PAD[0]}" y="{OUT_PAD[1] - 6}" class="silk" font-size="5.5" text-anchor="middle">OUT</text>')

    # cables from the board to each arm, pulsing while that arm works
    cables = [(f'M{sx - 4} {y0} C {sx - 4} {y0 - 30}, {lb[0] - 4} {lb[1] + 80}, {lb[0] - 4} {lb[1] + 52}', 0.0, 4.6),
              (f'M{cpu_x + 40} {y0} C {cpu_x + 40} {y0 - 30}, {db[0] + 4} {db[1] + 80}, {db[0] + 4} {db[1] + 52}', t_cpu - 1.3, t_cpu + 3.7)]
    for path, c0, c1 in cables:
        a(f'<path d="{path}" fill="none" stroke="#111827" stroke-width="5" stroke-linecap="round"/>'
          f'<path d="{path}" fill="none" stroke="{BP["soft"]}" stroke-width="1" stroke-opacity="0.4"/>'
          f'<path d="{path}" fill="none" stroke="#fbbf24" stroke-width="2" stroke-dasharray="3 9" opacity="0" filter="url(#glow)">'
          f'<animate attributeName="stroke-dashoffset" from="0" to="-48" dur="0.5s" repeatCount="indefinite"/>'
          f'<animate attributeName="opacity" values="0;1;0" keyTimes="{kt([0, c0, c1], D)}" calcMode="discrete" {dur}/></path>')

    # ---- relay robots ----------------------------------------------------
    legs = [(L * k / N_ROBOTS, L * (k + 1) / N_ROBOTS) for k in range(N_ROBOTS)]
    for k, (s0, s1) in enumerate(legs):
        f0, f1 = rf(s0), rf(s1)
        back = min(f1 + (f1 - f0) * 0.55, 0.99)
        leg = sub_path(pts, cum, s0, s1)
        sprite = robot(k, ROBOT_COLORS[k]).replace("scale(1.35)", "scale(1.05)")
        h0 = t_b1 + 0.15 + 0.12 * k
        hop = (f'<animateTransform attributeName="transform" type="translate" values="0,0;0,0;0,-8;0,0;0,-8;0,0;0,0" '
               f'keyTimes="{kt([0, h0, h0 + 0.14, h0 + 0.28, h0 + 0.42, h0 + 0.56, D], D)}" {dur}/>')
        a(f'<g><g>{sprite}{hop}</g><animateMotion path="{d_attr(leg)}" keyPoints="0;0;1;1;0;0" '
          f'keyTimes="0;{f0:.4f};{f1:.4f};{min(f1 + 0.01, back):.4f};{back:.4f};1" calcMode="linear" {dur}/></g>')
        if k:
            (hx, hy), _ = point_at(pts, cum, s0)
            a(f'<circle cx="{hx:.1f}" cy="{hy - 20:.1f}" r="10" fill="{PCB["energy"]}" opacity="0" filter="url(#bigglow)">'
              f'<animate attributeName="opacity" values="0;0;0.9;0;0" keyTimes="{kt([0, f0 * D - 0.1, f0 * D, f0 * D + 0.4, D], D)}" {dur}/></circle>')
    # packet on the trace, then waiting on the OUT pad, then in the bin
    a(f'<g opacity="0"><g transform="translate(0,-40)">{PACKET_SVG}</g>'
      f'<animate attributeName="opacity" values="0;1;0" keyTimes="{kt([0, t_power, t_cpu], D)}" calcMode="discrete" {dur}/>'
      f'<animateMotion path="{d_attr(pts)}" keyPoints="0;0;1;1" keyTimes="{kt([0, t_power, t_cpu, D], D)}" calcMode="linear" {dur}/></g>')
    a(f'<g transform="translate({OUT_PAD[0]},{OUT_PAD[1] - 9})" opacity="0">{PACKET_SVG}<animate attributeName="opacity" values="0;1;0" '
      f'keyTimes="{kt([0, t_cpu + 0.1, t_cpu + 0.45], D)}" calcMode="discrete" {dur}/></g>')
    a(f'<g transform="translate({BIN[0]},{BIN[1] + 6})" opacity="0">{PACKET_SVG}<animate attributeName="opacity" values="0;1;0" '
      f'keyTimes="{kt([0, t_dep, t_b0], D)}" calcMode="discrete" {dur}/></g>')

    # ---- the two arms (drawn last so they pass over the board) ---------
    a(gripper_arm(lb, LOADER["l1"], LOADER["l2"], LOADER["grip"], loader_keys, D, carried=CELL_SVG,
                  carry=(1.25, 3.35), fill=BP["bg"], label="J1"))
    a(gripper_arm(db, DEPLOYER["l1"], DEPLOYER["l2"], DEPLOYER["grip"], deploy_keys, D, carried=PACKET_SVG,
                  carry=(t_cpu + 0.45, t_cpu + 2.4), fill=BP["bg"], label="J1"))
    a(finale(d, pts, stops, t_b0, t_b1, D, dur, tx0, ty0, tw))
    a('</svg>')
    return finalize("\n".join(o))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("user")
    ap.add_argument("out_dir")
    ap.add_argument("--cache")
    args = ap.parse_args()
    data = fetch(args.user, args.cache)
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "assembly-line.svg"), "w") as fh:
        fh.write(render(data))
    print("assembly: ok")


if __name__ == "__main__":
    main()
