"""Post-process generated SVG so every SMIL animation is valid.

For calcMode linear/spline/paced, SMIL requires keyTimes to end at exactly 1;
otherwise browsers silently drop the whole animation. Any animation whose last
keyTime is below 1 gets its final value held until the end of the loop.
"""
import re

TAG = re.compile(r"<animate(?:Transform|Motion)?\b[^>]*>")


def _attr(tag, name):
    m = re.search(rf'\s{name}="([^"]*)"', tag)
    return m.group(1) if m else None


def _set(tag, name, value):
    return re.sub(rf'(\s{name}=")[^"]*(")', lambda m: m.group(1) + value + m.group(2), tag, count=1)


def _fix(match):
    tag = match.group(0)
    times = _attr(tag, "keyTimes")
    if not times or _attr(tag, "calcMode") == "discrete":
        return tag
    kts = times.split(";")
    if float(kts[-1]) >= 1:
        return tag
    tag = _set(tag, "keyTimes", times + ";1")
    for name in ("values", "keyPoints"):
        v = _attr(tag, name)
        if v:
            tag = _set(tag, name, v + ";" + v.split(";")[-1])
    splines = _attr(tag, "keySplines")
    if splines:
        tag = _set(tag, "keySplines", splines + ";0 0 1 1")
    return tag


def finalize(svg):
    return TAG.sub(_fix, svg)
