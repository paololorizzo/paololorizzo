#!/usr/bin/env python3
"""Render the animated SVG cards for the GitHub profile README.

Reads data/profile.json, data/contributions.json and data/oss.json and writes
cards/{light,dark}/*.svg. Everything (fonts, styles) is embedded in each SVG
because GitHub serves README images through <img>, which blocks external
resources and JavaScript.

  python scripts/render_cards.py            # animated cards
  STATIC=1 python scripts/render_cards.py   # final frame only (screenshots)
"""
import base64
import json
import math
import os
import random
from collections import OrderedDict
from datetime import date, timedelta
from html import escape
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
DATA, FONTS, OUT = ROOT / "data", ROOT / "fonts", ROOT / "cards"
STATIC = os.environ.get("STATIC") == "1"
W = 900

THEMES = {
    "light": dict(bg="#ffffff", border="#d0d7de", ink="#1f2328", muted="#59636e",
                  faint="#f3f4f6", grid="#e6e8eb", violet="#7c3aed", green="#16a34a",
                  amber="#d97706", violet_soft="#ede9fe", green_soft="#dcfce7"),
    "dark": dict(bg="#0d1117", border="#30363d", ink="#e6edf3", muted="#9198a1",
                 faint="#161b22", grid="#21262d", violet="#a78bfa", green="#3fb950",
                 amber="#f0b429", violet_soft="#2e1f5e", green_soft="#0f2d1a"),
}

# ----------------------------------------------------------------- fonts ---
FONT_FILES = {
    ("sg", 400): "space-grotesk-400.woff2", ("sg", 500): "space-grotesk-500.woff2",
    ("sg", 700): "space-grotesk-700.woff2", ("jb", 400): "jetbrains-mono-400.woff2",
    ("jb", 600): "jetbrains-mono-600.woff2",
}
FAMILY = {"sg": "SG", "jb": "JB"}
_metrics = {}


def _font(key):
    if key not in _metrics:
        f = TTFont(FONTS / FONT_FILES[key])
        _metrics[key] = (f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm)
    return _metrics[key]


def text_width(s, fam="sg", weight=400, size=16):
    cmap, hmtx, upm = _font((fam, weight))
    return sum(hmtx.get(cmap.get(ord(c), ".notdef"), (upm // 2, 0))[0] for c in s) * size / upm


def truncate(s, max_w, **kw):
    if text_width(s, **kw) <= max_w:
        return s
    while s and text_width(s + "…", **kw) > max_w:
        s = s[:-1]
    return s.rstrip() + "…"


def font_css(keys):
    out = []
    for k in sorted(keys):
        b64 = base64.b64encode((FONTS / FONT_FILES[k]).read_bytes()).decode()
        out.append(f"@font-face{{font-family:{FAMILY[k[0]]};font-weight:{k[1]};"
                   f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "".join(out)


# ------------------------------------------------------------ svg helpers ---
BASE_CSS = """
.sg{font-family:SG,'Segoe UI',Helvetica,Arial,sans-serif}
.jb{font-family:JB,ui-monospace,SFMono-Regular,Menlo,monospace}
@keyframes up{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes pop{from{opacity:0;transform:scale(.3)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
@keyframes flash{0%,100%{opacity:1}}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
.up{animation:up .7s cubic-bezier(.2,.7,.2,1) both}
.fade{animation:fade .6s ease-out both}
.pop{animation:pop .45s cubic-bezier(.3,1.6,.5,1) both;transform-box:fill-box;transform-origin:center}
.grow{animation:grow .8s cubic-bezier(.2,.8,.2,1) both;transform-box:fill-box;transform-origin:bottom}
.draw{stroke-dasharray:1;animation:draw .9s ease-out both}
.ch{animation:fade .01s linear both}
.frame{opacity:0;animation:flash var(--d) steps(1) none}
.cursor{animation:blink 1s steps(1) 5 both}
"""
NO_MOTION = "*{animation:none!important}.pulse{display:none}"


def svg(width, height, body, fonts, theme, extra_css=""):
    t = THEMES[theme]
    css = font_css(fonts) + BASE_CSS + extra_css
    css += NO_MOTION if STATIC else f"@media (prefers-reduced-motion:reduce){{{NO_MOTION}}}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" fill="none" role="img">'
        f"<style>{css}</style>"
        f'<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="14" '
        f'fill="{t["bg"]}" stroke="{t["border"]}"/>'
        f"{body}</svg>"
    )


def d(seconds):
    return f'style="animation-delay:{seconds:.2f}s"'


def header(label, t, x=32, y=40, delay=0.0, color=None):
    color = color or t["green"]
    return (f'<g class="fade" {d(delay)}><circle cx="{x+4}" cy="{y-4}" r="4" fill="{color}"/>'
            f'<text x="{x+16}" y="{y}" class="jb" font-size="12" font-weight="600" '
            f'letter-spacing="1.5" fill="{t["muted"]}">{escape(label.upper())}</text></g>')


# ------------------------------------------------------------------ cards ---
def card_hero(p, t, theme):
    H = 280
    parts = []
    # typed prompt, one character at a time
    chars = "".join(
        f'<tspan class="ch" {d(0.15 + i * 0.045)}>{escape(c)}</tspan>'
        for i, c in enumerate(p["prompt"]))
    px = 40 + text_width(p["prompt"], "jb", 400, 15) + 6
    t_end = 0.15 + len(p["prompt"]) * 0.045
    parts.append(f'<text x="40" y="56" class="jb" font-size="15" fill="{t["muted"]}" '
                 f'xml:space="preserve">{chars}</text>')
    parts.append(f'<rect class="cursor" {d(t_end)} x="{px:.1f}" y="44" width="9" height="16" '
                 f'fill="{t["green"]}"/>')

    parts.append(f'<text class="sg up" {d(t_end + 0.1)} x="38" y="118" font-size="54" '
                 f'font-weight="700" letter-spacing="-1.5" fill="{t["ink"]}">{escape(p["name"])}</text>')
    nw = text_width(p["name"], "sg", 700, 54) - 1.5 * len(p["name"])
    parts.append(
        f'<defs><linearGradient id="ul" x1="0" x2="1"><stop offset="0" stop-color="{t["violet"]}"/>'
        f'<stop offset="1" stop-color="{t["green"]}"/></linearGradient></defs>'
        f'<path class="draw" {d(t_end + 0.45)} pathLength="1" d="M40 134 H{40 + nw:.0f}" '
        f'stroke="url(#ul)" stroke-width="4" stroke-linecap="round"/>')
    role = f'{p["role"]}  ·  {p["location"]}'
    parts.append(f'<text class="jb fade" {d(t_end + 0.6)} x="40" y="166" font-size="14" '
                 f'font-weight="600" fill="{t["violet"]}">{escape(role)}</text>')
    for i, line in enumerate(p["tagline"]):
        parts.append(f'<text class="sg up" {d(t_end + 0.75 + i * 0.12)} x="40" y="{196 + i * 24}" '
                     f'font-size="17" fill="{t["muted"]}">{escape(line)}</text>')

    parts.append(network(t, t_end + 0.3))
    fonts = {("jb", 400), ("jb", 600), ("sg", 700), ("sg", 400)}
    return svg(W, H, "".join(parts), fonts, theme)


def network(t, start):
    """A small layered network: the stack flows in, products come out."""
    layers = [
        [("ts", t["green"]), ("react", t["green"]), ("expo", t["green"]), ("supabase", t["green"])],
        [(None, t["ink"])] * 5,
        [("ai", t["violet"]), ("ship", t["amber"])],
    ]
    xs, top, bottom = [660, 750, 840], 50, 236
    pos = []
    for li, layer in enumerate(layers):
        n = len(layer)
        step = (bottom - top) / (n - 1) if n > 1 else 0
        pad = (bottom - top - step * (n - 1)) / 2
        pos.append([(xs[li], top + pad + step * k) for k in range(n)])
    rnd = random.Random(7)
    edges, out = [], []
    for li in range(len(layers) - 1):
        for a in pos[li]:
            for b in pos[li + 1]:
                if rnd.random() < 0.72:
                    edges.append((a, b))
    for i, (a, b) in enumerate(edges):
        out.append(f'<path class="draw" {d(start + 0.25 + i * 0.025)} pathLength="1" '
                   f'd="M{a[0]} {a[1]:.1f} L{b[0]} {b[1]:.1f}" stroke="{t["border"]}" stroke-width="1.2"/>')
    k = 0
    for li, layer in enumerate(layers):
        for (label, color), (x, y) in zip(layer, pos[li]):
            r = 7 if li != 1 else 5
            fill = t["bg"] if li == 1 else color
            out.append(f'<circle class="pop" {d(start + 0.1 + k * 0.05)} cx="{x}" cy="{y:.1f}" r="{r}" '
                       f'fill="{fill}" stroke="{color}" stroke-width="2"/>')
            if label:
                anchor, lx = ("end", x - 14) if li == 0 else ("start", x + 14)
                out.append(f'<text class="jb fade" {d(start + 0.4 + k * 0.05)} x="{lx}" y="{y + 4:.1f}" '
                           f'text-anchor="{anchor}" font-size="11" fill="{t["muted"]}">{label}</text>')
            k += 1
    # signals travelling through the network (hidden when motion is reduced)
    paths = [(pos[0][1], pos[1][2], pos[2][0]), (pos[0][3], pos[1][3], pos[2][1]),
             (pos[0][0], pos[1][1], pos[2][0])]
    for i, (a, b, c) in enumerate(paths):
        color = t["violet"] if c == pos[2][0] else t["amber"]
        begin = start + 1.6 + i * 1.3
        out.append(
            f'<circle class="pulse" r="3.2" fill="{color}" opacity="0">'
            f'<animateMotion path="M{a[0]} {a[1]:.1f} L{b[0]} {b[1]:.1f} L{c[0]} {c[1]:.1f}" '
            f'dur="1.6s" begin="{begin:.2f}s;{begin + 6:.2f}s;{begin + 12:.2f}s" fill="freeze"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" dur="1.6s" '
            f'begin="{begin:.2f}s;{begin + 6:.2f}s;{begin + 12:.2f}s"/></circle>')
    return "".join(out)


def card_now(p, t, theme):
    H = 120
    col_w = (W - 64) / 3
    parts = []
    colors = [t["green"], t["violet"], t["amber"]]
    for i, item in enumerate(p["now"]):
        x = 32 + i * col_w
        delay = 0.2 + i * 0.15
        if i:
            parts.append(f'<line class="fade" {d(delay)} x1="{x - 12:.0f}" y1="28" x2="{x - 12:.0f}" '
                         f'y2="{H - 28}" stroke="{t["grid"]}"/>')
        parts.append(f'<g class="up" {d(delay)}>'
                     f'<circle cx="{x + 4:.0f}" cy="44" r="4" fill="{colors[i % 3]}"/>'
                     f'<text x="{x + 16:.0f}" y="48" class="jb" font-size="12" font-weight="600" '
                     f'letter-spacing="1.5" fill="{t["muted"]}">NOW {escape(item["label"].upper())}</text>'
                     f'<text x="{x:.0f}" y="80" class="sg" font-size="16" font-weight="500" fill="{t["ink"]}">'
                     f'{escape(truncate(item["text"], col_w - 24, fam="sg", weight=500, size=16))}</text></g>')
    return svg(W, H, "".join(parts), {("jb", 600), ("sg", 500)}, theme)


def card_stack(p, t, theme):
    row_h, top = 46, 74
    H = top + row_h * len(p["stack"]) + 8
    parts = [header("stack", t, delay=0.1)]
    k = 0
    for r, group in enumerate(p["stack"]):
        y = top + r * row_h
        learning = group.get("learning")
        parts.append(f'<text class="jb fade" {d(0.2 + r * 0.1)} x="32" y="{y + 21}" font-size="13" '
                     f'fill="{t["muted"]}">{escape(group["group"])}</text>')
        x = 150
        for item in group["items"]:
            w = text_width(item, "sg", 500, 15) + 28
            stroke = t["violet"] if learning else t["border"]
            fill = t["violet_soft"] if learning else t["faint"]
            dash = ' stroke-dasharray="4 3"' if learning else ""
            parts.append(
                f'<g class="pop" {d(0.3 + k * 0.06)}><rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="32" '
                f'rx="8" fill="{fill}" stroke="{stroke}"{dash}/>'
                f'<text x="{x + w / 2:.1f}" y="{y + 21}" text-anchor="middle" class="sg" font-size="15" '
                f'font-weight="500" fill="{t["ink"]}">{escape(item)}</text></g>')
            x += w + 10
            k += 1
        if learning:
            parts.append(f'<text class="jb fade" {d(0.4 + k * 0.06)} x="{x + 6:.1f}" y="{y + 21}" '
                         f'font-size="12" fill="{t["violet"]}">← learning now</text>')
        if r < len(p["stack"]) - 1:
            parts.append(f'<line x1="32" x2="{W - 32}" y1="{y + row_h - 7}" y2="{y + row_h - 7}" '
                         f'stroke="{t["grid"]}" stroke-dasharray="2 4"/>')
    return svg(W, H, "".join(parts), {("jb", 400), ("jb", 600), ("sg", 500)}, theme)


def stats(contrib):
    days = sorted(contrib["days"], key=lambda x: x["date"])
    months = OrderedDict()
    for dd in days:
        months.setdefault(dd["date"][:7], 0)
        months[dd["date"][:7]] += dd["count"]
    months = list(months.items())[-12:]
    longest = cur = 0
    for dd in days:
        cur = cur + 1 if dd["count"] else 0
        longest = max(longest, cur)
    current = 0
    for i, dd in enumerate(reversed(days)):
        if dd["count"]:
            current += 1
        elif i == 0:  # today may still be empty
            continue
        else:
            break
    active = sum(1 for dd in days if dd["count"])
    return months, longest, current, active


MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def counter(value, x, y, t, start, dur=1.3, frames=22):
    """Count up with CSS only: each frame flashes once, the final one stays."""
    out = []
    vals = sorted({round(value * (1 - (1 - i / frames) ** 3)) for i in range(frames)} - {value})
    step = dur / max(len(vals), 1)
    common = f'x="{x}" y="{y}" font-size="56" font-weight="700" letter-spacing="-1.5" fill="{t["ink"]}"'
    for i, v in enumerate(vals):
        out.append(f'<text {common} class="sg frame" style="--d:{step:.3f}s;animation-delay:{start + i * step:.3f}s">{v:,}</text>')
    out.append(f'<text {common} class="sg fade" style="animation-duration:.01s;animation-delay:{start + len(vals) * step:.3f}s">{value:,}</text>')
    return "".join(out)


def card_activity(contrib, t, theme):
    H = 300
    months, longest, current, active = stats(contrib)
    parts = [header("activity · last 12 months", t, delay=0.1)]
    parts.append(counter(contrib["total"], 30, 128, t, 0.3))
    parts.append(f'<text class="jb fade" {d(0.3)} x="32" y="154" font-size="13" fill="{t["muted"]}">contributions</text>')
    best = max(months, key=lambda m: m[1]) if months else ("", 0)
    rows = [("longest streak", f"{longest} days"), ("current streak", f"{current} days"),
            ("active days", f"{active}"),
            ("best month", f"{MONTHS[int(best[0][5:]) - 1]} · {best[1]}" if best[1] else "—")]
    for i, (k, v) in enumerate(rows):
        y = 192 + i * 24
        parts.append(f'<g class="up" {d(1.0 + i * 0.1)}><text x="32" y="{y}" class="jb" font-size="13" '
                     f'fill="{t["muted"]}">{k}</text><text x="250" y="{y}" text-anchor="end" class="sg" '
                     f'font-size="15" font-weight="500" fill="{t["ink"]}">{escape(v)}</text></g>')

    # monthly bars
    x0, x1, base, top = 310, W - 32, 250, 70
    peak = max([m[1] for m in months] + [1])
    slot = (x1 - x0) / max(len(months), 1)
    bw = slot * 0.62
    for g in range(4):
        gy = base - (base - top) * g / 3
        dash = "" if g == 0 else ' stroke-dasharray="2 4"'
        parts.append(f'<line x1="{x0}" x2="{x1}" y1="{gy:.1f}" y2="{gy:.1f}" stroke="{t["grid"]}"{dash}/>')
    for i, (ym, n) in enumerate(months):
        h = max((base - top) * n / peak, 2)
        x = x0 + i * slot + (slot - bw) / 2
        color = t["violet"] if n == peak and n else t["green"]
        parts.append(f'<rect class="grow" {d(0.5 + i * 0.06)} x="{x:.1f}" y="{base - h:.1f}" width="{bw:.1f}" '
                     f'height="{h:.1f}" rx="3" fill="{color}"/>')
        if n:
            parts.append(f'<text class="jb fade" {d(1.1 + i * 0.06)} x="{x + bw / 2:.1f}" y="{base - h - 7:.1f}" '
                         f'text-anchor="middle" font-size="11" fill="{t["muted"]}">{n}</text>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{base + 20}" text-anchor="middle" class="jb" '
                     f'font-size="11" fill="{t["muted"]}">{MONTHS[int(ym[5:]) - 1]}</text>')
    parts.append(f'<text x="{W - 32}" y="{H - 14}" text-anchor="end" class="jb" font-size="10" '
                 f'fill="{t["muted"]}" opacity=".7">updated {contrib.get("updated", "")}</text>')
    return svg(W, H, "".join(parts), {("jb", 400), ("jb", 600), ("sg", 500), ("sg", 700)}, theme)


def card_oss(oss, t, theme):
    prs = oss.get("prs", [])[:5]
    parts = [header("open source", t, delay=0.1, color=t["violet"])]
    if not prs:
        H = 190
        parts.append(f'<text class="sg up" {d(0.25)} x="32" y="86" font-size="22" font-weight="700" '
                     f'fill="{t["ink"]}">First contributions on the way.</text>')
        parts.append(f'<text class="sg up" {d(0.35)} x="32" y="114" font-size="15" fill="{t["muted"]}">'
                     f'Looking for issues in TypeScript, React, Supabase and AI projects.</text>')
        parts.append(f'<text class="sg up" {d(0.45)} x="32" y="136" font-size="15" fill="{t["muted"]}">'
                     f'Merged pull requests will show up here automatically.</text>')
        for i in range(3):
            x = 32 + i * 284
            parts.append(f'<rect class="fade" {d(0.6 + i * 0.12)} x="{x}" y="152" width="268" height="12" rx="6" '
                         f'fill="{t["faint"]}" stroke="{t["grid"]}" stroke-dasharray="3 3"/>')
        return svg(W, H, "".join(parts), {("jb", 600), ("sg", 400), ("sg", 700)}, theme)

    row_h, top = 44, 62
    H = top + row_h * len(prs) + 16
    total = oss.get("total_merged", len(prs))
    parts.append(f'<text class="jb fade" {d(0.1)} x="{W - 32}" y="40" text-anchor="end" font-size="12" '
                 f'fill="{t["muted"]}">{total} merged PR{"s" if total != 1 else ""}</text>')
    for i, pr in enumerate(prs):
        y = top + i * row_h
        repo = truncate(pr["repo"], 230, fam="jb", weight=600, size=13)
        meta = f'{pr["stars"]:,}  ·  {pr["merged"]}'
        meta_w = text_width(meta, "jb", 400, 12)
        sx, sy = W - 40 - meta_w - 10, y + 18.5
        star = " ".join(f"{sx + (5 if k % 2 == 0 else 2.2) * math.sin(k * 0.6283):.1f},"
                        f"{sy - (5 if k % 2 == 0 else 2.2) * math.cos(k * 0.6283):.1f}"
                        for k in range(10))
        title = truncate(pr["title"], sx - 10 - 16 - 300, fam="sg", weight=400, size=15)
        parts.append(
            f'<g class="up" {d(0.25 + i * 0.1)}>'
            f'<rect x="24" y="{y}" width="{W - 48}" height="{row_h - 8}" rx="8" fill="{t["faint"]}"/>'
            f'<path d="M38 {y + 11} v14 M38 {y + 18} q0 -7 7 -7" stroke="{t["violet"]}" stroke-width="1.8" '
            f'stroke-linecap="round" fill="none"/><circle cx="38" cy="{y + 25}" r="2.6" fill="{t["violet"]}"/>'
            f'<circle cx="46" cy="{y + 11}" r="2.6" fill="{t["violet"]}"/>'
            f'<text x="58" y="{y + 23}" class="jb" font-size="13" font-weight="600" fill="{t["violet"]}">{escape(repo)}</text>'
            f'<text x="300" y="{y + 23}" class="sg" font-size="15" fill="{t["ink"]}">{escape(title)}</text>'
            f'<text x="{W - 40}" y="{y + 23}" text-anchor="end" class="jb" font-size="12" '
            f'fill="{t["muted"]}" xml:space="preserve">{meta}</text>'
            f'<polygon points="{star}" fill="{t["amber"]}"/></g>')
    return svg(W, H, "".join(parts), {("jb", 400), ("jb", 600), ("sg", 400)}, theme)


def load(name, default):
    path = DATA / name
    return json.loads(path.read_text()) if path.exists() else default


def main():
    profile = load("profile.json", None)
    today = date.today()
    contrib = load("contributions.json", {
        "updated": today.isoformat(), "total": 0,
        "days": [{"date": (today - timedelta(days=i)).isoformat(), "count": 0} for i in range(365)]})
    oss = load("oss.json", {"prs": []})
    for theme, t in THEMES.items():
        out = OUT / theme
        out.mkdir(parents=True, exist_ok=True)
        cards = {
            "hero": card_hero(profile, t, theme),
            "now": card_now(profile, t, theme),
            "stack": card_stack(profile, t, theme),
            "activity": card_activity(contrib, t, theme),
            "oss": card_oss(oss, t, theme),
        }
        for name, content in cards.items():
            (out / f"{name}.svg").write_text(content)
    print("rendered", ", ".join(cards), "for", ", ".join(THEMES))


if __name__ == "__main__":
    main()
