"""Reusable planar robot-arm pieces: 2-link IK and a blueprint-style SVG arm.

Coordinates are SVG (y down); angles are degrees, positive = clockwise, so they
can be fed straight into rotate().
"""
import math


def ik2(dx, dy, l1, l2, sign):
    """Joint angles reaching (dx, dy) from the shoulder with a given elbow branch."""
    d = math.hypot(dx, dy)
    c2 = (d * d - l1 * l1 - l2 * l2) / (2 * l1 * l2)
    t2 = sign * math.acos(max(-1.0, min(1.0, c2)))
    t1 = math.atan2(dy, dx) - math.atan2(l2 * math.sin(t2), l1 + l2 * math.cos(t2))
    return math.degrees(t1), math.degrees(t2)


def ik_high_elbow(dx, dy, l1, l2):
    """Branch that keeps the elbow highest on screen (never through the floor)."""
    best = None
    for sign in (-1, 1):
        a1, a2 = ik2(dx, dy, l1, l2, sign)
        ey = l1 * math.sin(math.radians(a1))
        if best is None or ey < best[0]:
            best = (ey, a1, a2)
    return best[1], best[2]


def unwrap(seq):
    out = [seq[0]]
    for v in seq[1:]:
        while v - out[-1] > 180:
            v -= 360
        while v - out[-1] < -180:
            v += 360
        out.append(v)
    return out


def fmt_times(times, dur):
    out, last = [], 0.0
    for t in times:
        v = min(1.0, max(last, t / dur))
        out.append(v)
        last = v
    out[0], out[-1] = 0.0, 1.0
    return ";".join(f"{v:.4f}" for v in out)


def gripper_arm(base, l1, l2, grip, keys, dur, carried="", carry=(0, 0),
                ink="#e6f0ff", soft="#9cc2ee", fill="#0b2747", label=None, eased=True):
    """Blueprint line-art arm with a parallel gripper that always points down.

    keys: [(t_seconds, (x, y) grip-centre target, closed?)], first at 0, last at dur.
    carried: SVG drawn in the gripper frame around (0,0); shown while carry[0] <= t < carry[1].
    """
    a1s, a2s, a3s = [], [], []
    for _, (tx, ty), _ in keys:
        a1, a2 = ik_high_elbow(tx - base[0], ty - grip - base[1], l1, l2)
        a1s.append(a1)
        a2s.append(a2)
        a3s.append(90 - (a1 + a2))
    a1s, a2s, a3s = unwrap(a1s), unwrap(a2s), unwrap(a3s)
    kt = fmt_times([k[0] for k in keys], dur)
    n = len(keys)
    ease = (f'calcMode="spline" keySplines="{";".join(["0.45 0 0.55 1"] * (n - 1))}"' if eased else "")

    def rot(vals):
        return (f'<animateTransform attributeName="transform" type="rotate" values="{";".join(f"{v:.2f}" for v in vals)}" '
                f'keyTimes="{kt}" {ease} dur="{dur:.2f}s" repeatCount="indefinite"/>')

    stroke = f'fill="{fill}" stroke="{ink}" stroke-width="1.4"'
    thin = f'fill="none" stroke="{soft}" stroke-width="0.8"'
    gaps = [grip * 0.32 if c else grip * 0.47 for _, _, c in keys]
    fingers = ""
    for s in (-1, 1):
        vals = ";".join(f"0,{s * g:.1f}" for g in gaps)
        fingers += (f'<g><rect x="{grip - 16}" y="-1.5" width="22" height="3" rx="1" fill="{ink}"/>'
                    f'<animateTransform attributeName="transform" type="translate" values="{vals}" keyTimes="{kt}" '
                    f'dur="{dur:.2f}s" repeatCount="indefinite"/></g>')
    c0, c1 = carry
    carried_svg = ""
    if carried:
        carried_svg = (f'<g transform="translate({grip},0) rotate(-90)" opacity="0">{carried}'
                       f'<animate attributeName="opacity" values="0;1;0" keyTimes="0;{c0 / dur:.4f};{c1 / dur:.4f}" '
                       f'calcMode="discrete" dur="{dur:.2f}s" repeatCount="indefinite"/></g>')
    tag = (f'<text x="{l1 / 2}" y="-12" font-size="8" text-anchor="middle" fill="{soft}" '
           f'font-family="ui-monospace,Menlo,Consolas,monospace">{label}</text>' if label else "")
    return f'''<g transform="translate({base[0]},{base[1]})"><g>{rot(a1s)}
  <rect x="-8" y="-8" width="{l1 + 16}" height="16" rx="8" {stroke}/>
  <line x1="0" y1="0" x2="{l1}" y2="0" {thin} stroke-dasharray="10 3 2 3"/>{tag}
  <circle r="9" {stroke}/><circle r="3" fill="{ink}"/>
  <g transform="translate({l1},0)"><g>{rot(a2s)}
    <rect x="-6.5" y="-6.5" width="{l2 + 13}" height="13" rx="6.5" {stroke}/>
    <line x1="0" y1="0" x2="{l2}" y2="0" {thin} stroke-dasharray="10 3 2 3"/>
    <circle r="8" {stroke}/><circle r="2.5" fill="{ink}"/>
    <g transform="translate({l2},0)"><g>{rot(a3s)}
      <circle r="6" {stroke}/><circle r="2" fill="{ink}"/>
      <rect x="4" y="-{grip * 0.55:.1f}" width="{grip - 18}" height="{grip * 1.1:.1f}" rx="2" {stroke}/>
      {carried_svg}{fingers}
    </g></g>
  </g></g>
</g></g>'''
