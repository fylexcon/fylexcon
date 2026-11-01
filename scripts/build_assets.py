"""Builds the SVG images used in the profile README.

Run from the repo root:  python3 scripts/build_assets.py   (needs fonttools + brotli)

Theme: a wave function. The header shows a particle in superposition that is
"measured" every few seconds, collapses to one spot and spreads out again,
the same idea as QuantumMechanics/WaveFunctionCollapse.py. Fonts are embedded
as small subsets because GitHub serves README images without web fonts.
"""

import base64
import math
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BG = "#0b0f14"
PANEL = "#111821"
INK = "#e6edf3"
DIM = "#8b98a5"
FAINT = "#2a3440"
CYAN = "#4fd1c5"
AMBER = "#ffb547"
VIOLET = "#a78bfa"
ROSE = "#ff6b8b"


def font_face(name, file):
    data = base64.b64encode((ASSETS / "fonts" / file).read_bytes()).decode()
    return f"@font-face{{font-family:{name};src:url(data:font/woff2;base64,{data}) format('woff2');}}"


def load_metrics(file):
    font = TTFont(ASSETS / "fonts" / file)
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    upm = font["head"].unitsPerEm
    return {chr(c): hmtx[g][0] / upm for c, g in cmap.items()}


METRICS = {"d": load_metrics("inter-800-subset.woff2"), "m": load_metrics("jbm-400-subset.woff2")}


def text_width(s, size, cls="m"):
    return sum(METRICS[cls].get(ch, 0.6) for ch in s) * size


FONTS = font_face("D8", "inter-800-subset.woff2") + font_face("M4", "jbm-400-subset.woff2")
BASE_CSS = (
    FONTS
    + ".d{font-family:D8,'Inter','Helvetica Neue',Arial,sans-serif;font-weight:800}"
    + ".m{font-family:M4,ui-monospace,'SF Mono',Menlo,Consolas,monospace;font-weight:400}"
    + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
)


def svg(w, h, body, css="", title=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" role="img">'
        f"<title>{escape(title)}</title><style>{BASE_CSS}{css}</style>{body}</svg>\n"
    )


def text(x, y, s, size, cls="m", fill=INK, anchor="start", extra=""):
    return (
        f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" {extra}>{escape(s)}</text>'
    )


def dots(pid, step=20, opacity=0.09):
    return (
        f'<pattern id="{pid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
        f'<circle cx="1" cy="1" r="1" fill="{INK}" fill-opacity="{opacity}"/></pattern>'
    )


def pts(points):
    return "M" + "L".join(f"{x:.0f} {y:.0f}" if abs(x) > 50 else f"{x:.1f} {y:.1f}" for x, y in points)


# ------------------------------------------------------------------ physics

def gauss(x, mu, s):
    return math.exp(-((x - mu) ** 2) / (2 * s * s))


def wave_frames(n_x=110, n_frames=40):
    """Frames of (Re psi, |psi|^2) over x in [-10, 10].

    Most of the loop is a two-packet superposition whose phase rotates.
    Around 60% of the way through it is measured: the density collapses
    onto one narrow peak, then spreads back into the superposition.
    """
    xs = [-10 + 20 * i / (n_x - 1) for i in range(n_x)]
    hit = 3.0
    frames = []
    for f in range(n_frames):
        t = f / n_frames
        phase = 2 * math.pi * t * 3
        # c: 0 = superposition, 1 = fully collapsed
        if 0.58 <= t < 0.64:
            c = (t - 0.58) / 0.06
        elif 0.64 <= t < 0.72:
            c = 1.0
        elif 0.72 <= t < 0.98:
            c = 1 - (t - 0.72) / 0.26
        else:
            c = 0.0
        c = c * c * (3 - 2 * c)
        re, rho = [], []
        for x in xs:
            env_s = gauss(x, -3, 1.6) + gauss(x, 3, 1.6)
            env_c = gauss(x, hit, 0.45) * 1.6
            env = (1 - c) * env_s + c * env_c
            re.append(env * math.cos(2.2 * x - phase))
            rho.append(env * env)
        frames.append((re, rho, c))
    return xs, frames


# ------------------------------------------------------------------ header

def header():
    w, h = 1200, 400
    ox, oy, pw, ph = 600, 70, 560, 260  # plot area
    base = oy + ph * 0.72

    xs, frames = wave_frames()

    def to_px(i, v, scale):
        x = ox + pw * i / (len(xs) - 1)
        return x, base - v * scale

    re_paths, rho_paths = [], []
    for re, rho, _ in frames:
        re_paths.append(pts(to_px(i, v, 62) for i, v in enumerate(re)))
        top = [to_px(i, v, 70) for i, v in enumerate(rho)]
        rho_paths.append(pts(top) + f"L{ox + pw} {base}L{ox} {base}Z")

    dur = "8s"
    n = len(frames)
    key_times = ";".join(f"{i / (n - 1):.4f}" for i in range(n))
    measure_ops = ";".join("1" if fr[2] > 0.6 else "0" for fr in frames)
    hit_x = ox + pw * (3.0 + 10) / 20

    def anim(values):
        return (
            f'<animate attributeName="d" dur="{dur}" repeatCount="indefinite" '
            f'keyTimes="{key_times}" values="{";".join(values)}"/>'
        )

    css = """
.blink{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}
"""
    axis_ticks = "".join(
        f'<path d="M{ox + pw * i / 10:.1f} {base}v5" stroke="{DIM}" stroke-opacity=".5"/>' for i in range(11)
    )

    name_size = 66
    body = f"""
<defs>{dots("g")}<clipPath id="card"><rect width="{w}" height="{h}" rx="16"/></clipPath>
<linearGradient id="rho" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{AMBER}" stop-opacity=".55"/><stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></linearGradient></defs>
<g clip-path="url(#card)">
<rect width="{w}" height="{h}" fill="{BG}"/>
<rect width="{w}" height="{h}" fill="url(#g)"/>

{text(56, 92, "|ψ⟩ = α|full-stack⟩ + β|quantum⟩", 17, "m", CYAN)}
{text(56, 168, "Mehmet Selim", name_size, "d", INK, extra='letter-spacing="-1.5"')}
{text(56, 238, "Suna", name_size, "d", INK, extra='letter-spacing="-1.5"')}
<rect x="{56 + text_width("Suna", name_size, "d") - 4 + 14}" y="196" width="12" height="44" fill="{AMBER}" class="blink"/>
{text(56, 290, "Full-stack developer · computer engineering student", 17, "m", DIM)}
{text(56, 316, "Software developer at Caladrius · IEEE İnönü VP", 17, "m", DIM)}
{text(56, 360, "Malatya, Türkiye · TR · EN · ES · JP", 14, "m", "#56636f")}

<path d="M{ox} {base}H{ox + pw}" stroke="{DIM}" stroke-opacity=".5"/>
{axis_ticks}
{text(ox, oy - 6, "ψ(x, t)", 14, "m", CYAN)}
{text(ox + 70, oy - 6, "|ψ|²", 14, "m", AMBER)}
{text(ox + pw, base + 26, "x", 13, "m", DIM, "end")}
<path d="{rho_paths[0]}" fill="url(#rho)">{anim(rho_paths)}</path>
<path d="{re_paths[0]}" stroke="{CYAN}" stroke-width="2" stroke-linejoin="round">{anim(re_paths)}</path>
<g opacity="0"><animate attributeName="opacity" dur="{dur}" repeatCount="indefinite" keyTimes="{key_times}" values="{measure_ops}" calcMode="discrete"/>
<path d="M{hit_x:.1f} {oy + 4}V{base}" stroke="{ROSE}" stroke-width="1.5" stroke-dasharray="4 4"/>
<rect x="{hit_x + 8:.1f}" y="{oy + 4}" width="{text_width("measured x = 3.0", 12) + 12:.0f}" height="20" fill="{ROSE}"/>
{text(hit_x + 14, oy + 18, "measured x = 3.0", 12, "m", BG)}
</g>
</g>"""
    return svg(w, h, body, css, "Mehmet Selim Suna: full-stack developer and computer engineering student")


def divider():
    w, h = 1200, 28
    n = 240
    p = pts((w * i / (n - 1), h / 2 - 7 * math.sin(i / (n - 1) * 2 * math.pi * 9) * math.exp(-((i / (n - 1) - 0.5) ** 2) / 0.05)) for i in range(n))
    body = f'<path d="{p}" stroke="{CYAN}" stroke-opacity=".7" stroke-width="1.5"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">{body}</svg>\n'


# ------------------------------------------------------------------ cards

def wrap(s, size, max_w, cls="m"):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if text_width(trial, size, cls) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def pill(x, y, s, color):
    tw = text_width(s, 11) + 14
    return (
        f'<rect x="{x}" y="{y - 14}" width="{tw:.0f}" height="20" rx="10" stroke="{color}" stroke-opacity=".6"/>'
        + text(x + 7, y, s, 11, "m", color)
    ), tw


def card(title, kicker, desc, tags, motif, accent):
    w, h = 600, 280
    body = [
        f'<defs>{dots("g", 18, .07)}</defs>',
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="{PANEL}" stroke="{FAINT}"/>',
        f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14" fill="url(#g)"/>',
        f'<rect x="28" y="28" width="8" height="8" fill="{accent}"/>',
        text(46, 36, kicker, 12, "m", accent),
        text(28, 78, title, 30, "d", INK, extra='letter-spacing="-.5"'),
    ]
    for i, line in enumerate(wrap(desc, 13.5, 300)):
        body.append(text(28, 112 + i * 21, line, 13.5, "m", DIM))
    x, y = 28, h - 30
    for t in tags:
        p, tw = pill(x, y, t, accent)
        if x + tw > 340:
            break
        body.append(p)
        x += tw + 6
    body.append(f'<g transform="translate(360 24)">{motif}</g>')
    body.append(
        f'<path d="M{w - 40} 38L{w - 28} 26M{w - 37} 26H{w - 28}V35" stroke="{DIM}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    return svg(w, h, "".join(body), "", f"{title}: {kicker}")


# motifs live in a 212 x 232 box

def motif_trellis():
    out = []
    # a vault with a daily-limit bar and a 48h cooldown timeline
    out.append(f'<rect x="20" y="22" width="172" height="92" rx="8" stroke="{CYAN}" stroke-opacity=".7"/>')
    out.append(f'<circle cx="62" cy="68" r="22" stroke="{CYAN}" stroke-width="2"/>')
    for k in range(6):
        a = k * math.pi / 3
        out.append(f'<path d="M{62 + 12 * math.cos(a):.1f} {68 + 12 * math.sin(a):.1f}L{62 + 22 * math.cos(a):.1f} {68 + 22 * math.sin(a):.1f}" stroke="{CYAN}" stroke-width="2"/>')
    out.append(text(100, 58, "USDC vault", 11, "m", INK))
    out.append(text(100, 78, "owner +", 11, "m", DIM))
    out.append(text(100, 94, "guardians", 11, "m", DIM))
    out.append(text(20, 146, "daily limit", 11, "m", DIM))
    out.append(f'<rect x="20" y="154" width="172" height="10" rx="5" fill="{FAINT}"/>')
    out.append(f'<rect x="20" y="154" width="118" height="10" rx="5" fill="{CYAN}"/>')
    out.append(text(20, 194, "new payee cooldown", 11, "m", DIM))
    out.append(f'<path d="M20 208H192" stroke="{FAINT}" stroke-width="2"/>')
    for i in range(5):
        out.append(f'<circle cx="{20 + i * 43}" cy="208" r="4" fill="{AMBER if i == 4 else FAINT}"/>')
    out.append(text(192, 228, "48 h", 11, "m", AMBER, "end"))
    return "".join(out)


def motif_qaoa():
    out = []
    ys = [40, 80, 120, 160]
    for i, y in enumerate(ys):
        out.append(text(0, y + 4, f"q{i}", 11, "m", DIM))
        out.append(f'<path d="M26 {y}H200" stroke="{FAINT}" stroke-width="1.5"/>')
    # H gates
    for y in ys:
        out.append(f'<rect x="34" y="{y - 11}" width="22" height="22" rx="3" fill="{PANEL}" stroke="{VIOLET}"/>')
        out.append(text(45, y + 4, "H", 11, "m", VIOLET, "middle"))
    # ZZ couplings
    for (a, b), x in zip([(0, 1), (1, 2), (2, 3), (0, 3)], [78, 100, 122, 144]):
        out.append(f'<path d="M{x} {ys[a]}V{ys[b]}" stroke="{VIOLET}" stroke-width="1.5"/>')
        out.append(f'<circle cx="{x}" cy="{ys[a]}" r="4" fill="{VIOLET}"/><circle cx="{x}" cy="{ys[b]}" r="4" fill="{VIOLET}"/>')
    for y in ys:
        out.append(f'<rect x="164" y="{y - 11}" width="28" height="22" rx="3" fill="{PANEL}" stroke="{CYAN}"/>')
        out.append(text(178, y + 4, "Rx", 10, "m", CYAN, "middle"))
    out.append(text(26, 204, "pick k of n assets", 11, "m", DIM))
    out.append(text(26, 224, "|1010⟩  p = 0.41", 11, "m", AMBER))
    return "".join(out)


def motif_sentiment():
    out = []
    prices = [120, 112, 118, 104, 108, 96, 100, 86, 90, 78, 82, 70, 64]
    xs = [10 + i * 15.5 for i in range(len(prices))]
    out.append(f'<path d="{pts(zip(xs, prices))}" stroke="{CYAN}" stroke-width="2" stroke-linejoin="round"/>')
    out.append(f'<path d="M{xs[-1]} 64L{xs[-1] + 18} 50" stroke="{AMBER}" stroke-width="2" stroke-dasharray="3 3"/>')
    out.append(f'<path d="M{xs[-1]} 64L{xs[-1] + 18} 46L{xs[-1] + 18} 84Z" fill="{AMBER}" fill-opacity=".15"/>')
    sent = [0.4, -0.2, 0.7, 0.1, -0.6, 0.8, 0.3, -0.1, 0.9, 0.5]
    for i, s in enumerate(sent):
        x = 14 + i * 19
        hgt = abs(s) * 32
        col = CYAN if s > 0 else ROSE
        y0 = 172
        out.append(f'<rect x="{x}" y="{y0 - hgt if s > 0 else y0}" width="11" height="{hgt:.1f}" fill="{col}" fill-opacity=".75"/>')
    out.append(f'<path d="M8 172H200" stroke="{DIM}" stroke-opacity=".4"/>')
    out.append(text(8, 226, "news → Gemini → score", 11, "m", DIM))
    out.append(text(8, 30, "BTC  +2.4% (t+1h)", 11, "m", AMBER))
    return "".join(out)


def motif_sar():
    import random
    rnd = random.Random(7)
    out = []
    cell = 10
    for gy in range(19):
        for gx in range(20):
            v = rnd.random()
            in_river = abs(gy - (6 + 4 * math.sin(gx / 3.2))) < 2.2
            if in_river:
                v *= 0.25
            out.append(f'<rect x="{gx * cell + 6}" y="{gy * cell + 8}" width="{cell}" height="{cell}" fill="{INK}" fill-opacity="{0.05 + 0.32 * v:.2f}"/>')
    river = [(gx * cell + 11, (6 + 4 * math.sin(gx / 3.2)) * cell + 13) for gx in range(20)]
    out.append(f'<path d="{pts(river)}" stroke="{CYAN}" stroke-width="2.5" stroke-opacity=".9"/>')
    out.append(f'<rect x="116" y="128" width="62" height="44" stroke="{AMBER}" stroke-width="1.5"/>')
    out.append(f'<rect x="116" y="113" width="{text_width("changed 0.87", 10) + 10:.0f}" height="15" fill="{AMBER}"/>')
    out.append(text(121, 124, "changed 0.87", 10, "m", BG))
    out.append(text(6, 226, "Sentinel-1 · water", 11, "m", DIM))
    return "".join(out)


def motif_rover():
    out = []
    cell = 16
    walls = {(3, 2), (3, 3), (3, 4), (3, 5), (7, 6), (7, 7), (8, 7), (9, 7), (6, 10), (7, 10), (8, 10), (10, 3), (10, 4)}
    craters = [(5, 8, 22), (10, 11, 16)]
    for cx, cy, r in craters:
        out.append(f'<circle cx="{cx * cell + 8}" cy="{cy * cell + 8}" r="{r}" stroke="{DIM}" stroke-opacity=".35" stroke-dasharray="2 3"/>')
    for gy in range(13):
        for gx in range(12):
            if (gx, gy) in walls:
                out.append(f'<rect x="{gx * cell + 2}" y="{gy * cell + 2}" width="{cell - 4}" height="{cell - 4}" fill="{DIM}" fill-opacity=".45"/>')
            else:
                out.append(f'<circle cx="{gx * cell + 8}" cy="{gy * cell + 8}" r="1" fill="{INK}" fill-opacity=".15"/>')
    path_a = [(1, 1), (2, 1), (3, 1), (4, 1), (5, 2), (6, 3), (6, 4), (7, 5), (8, 5), (9, 5), (10, 6), (11, 7), (11, 8), (11, 9), (10, 10), (10, 11)]
    path_d = [(1, 1), (1, 2), (2, 3), (2, 4), (2, 5), (2, 6), (3, 7), (4, 8), (5, 9), (5, 10), (5, 11), (6, 12), (7, 12), (8, 12), (9, 12), (10, 11)]
    out.append(f'<path d="{pts((x * cell + 8, y * cell + 8) for x, y in path_d)}" stroke="{VIOLET}" stroke-width="2" stroke-dasharray="3 4"/>')
    out.append(f'<path d="{pts((x * cell + 8, y * cell + 8) for x, y in path_a)}" stroke="{CYAN}" stroke-width="2.5" stroke-linejoin="round"/>')
    out.append(f'<rect x="{1 * cell + 2}" y="{1 * cell + 2}" width="12" height="12" fill="{AMBER}"/>')
    out.append(f'<circle cx="{10 * cell + 8}" cy="{11 * cell + 8}" r="6" stroke="{AMBER}" stroke-width="2"/>')
    out.append(text(0, 226, "A*", 11, "m", CYAN))
    out.append(text(28, 226, "Dijkstra", 11, "m", VIOLET))
    out.append(text(100, 226, "D* Lite", 11, "m", DIM))
    return "".join(out)


def motif_rov():
    out = []
    # depth vs time with setpoint and PID response
    out.append(text(0, 14, "depth (m)", 11, "m", DIM))
    out.append(f'<path d="M30 30V180H206" stroke="{DIM}" stroke-opacity=".4"/>')
    for i, d in enumerate([0, 1, 2, 3]):
        y = 40 + i * 44
        out.append(text(22, y + 4, str(d), 10, "m", DIM, "end"))
    sp = 40 + 2 * 44
    out.append(f'<path d="M30 {sp}H206" stroke="{AMBER}" stroke-dasharray="4 4"/>')
    resp = []
    for i in range(120):
        t = i / 119 * 6
        y = 2 * (1 - math.exp(-1.1 * t) * (math.cos(2.4 * t) + 0.46 * math.sin(2.4 * t)))
        resp.append((30 + 176 * i / 119, 40 + y * 44))
    out.append(f'<path d="{pts(resp)}" stroke="{CYAN}" stroke-width="2"/>')
    out.append(text(206, sp - 8, "setpoint 2.0", 10, "m", AMBER, "end"))
    out.append(text(30, 206, "BNO055 · Bar30 · YOLOv8", 11, "m", DIM))
    out.append(text(30, 226, "ROS 2 Humble · Jetson", 11, "m", DIM))
    return "".join(out)


def motif_swarm():
    import random
    rnd = random.Random(3)
    out = []
    for i in range(12):
        x, y = rnd.randint(4, 30) * 6, rnd.randint(2, 30) * 6
        out.append(f'<rect x="{x}" y="{y}" width="{rnd.randint(14, 40)}" height="{rnd.randint(6, 18)}" fill="{DIM}" fill-opacity=".18" transform="rotate({rnd.randint(-30, 30)} {x} {y})"/>')
    bots = [(40, 50), (80, 30), (120, 70), (60, 110), (150, 120), (100, 150), (30, 170), (170, 40)]
    for a in range(len(bots)):
        for b in range(a + 1, len(bots)):
            (x1, y1), (x2, y2) = bots[a], bots[b]
            if math.hypot(x1 - x2, y1 - y2) < 70:
                out.append(f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{CYAN}" stroke-opacity=".35"/>')
    for x, y in bots:
        out.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{CYAN}"/>')
    out.append(f'<circle cx="128" cy="140" r="16" fill="{ROSE}" fill-opacity=".2"/><circle cx="128" cy="140" r="6" fill="{ROSE}"/>')
    out.append(f'<rect x="146" y="126" width="{text_width("breath 0.93", 10) + 10:.0f}" height="15" fill="{ROSE}"/>')
    out.append(text(151, 137, "breath 0.93", 10, "m", BG))
    out.append(text(4, 226, "thermal + audio, edge AI", 11, "m", DIM))
    return "".join(out)


def motif_fylex():
    out = []
    # a party finder: library tiles and an LFG chat
    for i in range(3):
        for j in range(2):
            out.append(f'<rect x="{j * 54 + 4}" y="{i * 46 + 10}" width="46" height="38" rx="4" fill="{VIOLET}" fill-opacity="{0.15 + 0.12 * ((i + j) % 3)}"/>')
    msgs = [("LFG: 2 slots", CYAN, 0), ("in, mic on", INK, 22), ("inviting…", AMBER, 0)]
    for k, (m, col, indent) in enumerate(msgs):
        y = 52 + k * 40
        out.append(f'<rect x="{118 + indent - 6}" y="{y - 14}" width="{min(96, text_width(m, 10) + 12):.0f}" height="22" rx="6" stroke="{col}" stroke-opacity=".5"/>')
        out.append(text(118 + indent, y + 1, m, 10, "m", col))
    out.append(text(4, 182, "Steam library sync", 11, "m", DIM))
    out.append(text(4, 204, "LFG · chat · deals", 11, "m", DIM))
    out.append(text(4, 226, "NestJS · Prisma · Expo", 11, "m", DIM))
    return "".join(out)


CARDS = {
    "trellis": ("Trellis", "solana · co-builder", "A family USDC vault on Solana. The program enforces payee lists, daily limits, a 48-hour cooldown and guardian approvals; web, desktop and kiosk apps only talk to it.", ["Rust", "Anchor", "Next.js", "Tauri"], motif_trellis, CYAN),
    "quantlab": ("Quant Quantum Lab", "research · qaoa", "Vectorised backtests for SMA-RSI trend strategies without look-ahead bias, plus small portfolio selection solved with QAOA on Qiskit.", ["Python", "Qiskit", "pandas"], motif_qaoa, VIOLET),
    "quantvantage": ("QuantVantage AI", "fintech · nlp", "An n8n pipeline reads financial news, Gemini scores sentiment per ticker, and a PyTorch model forecasts short-term moves for AAPL, IONQ and crypto.", ["Next.js", "FastAPI", "PyTorch", "n8n"], motif_sentiment, AMBER),
    "noctis": ("NOCTIS ORBIT", "nasa space apps · team", "SAR change detection on Sentinel-1 that runs entirely in the browser: Otsu thresholding, morphology and an ONNX model, drawn on a Leaflet map.", ["TypeScript", "ONNX", "Leaflet"], motif_sar, CYAN),
    "moonrover": ("Moon-Rover", "tua lunar programme · team", "Procedural lunar terrain and a rover that plans with A*, Dijkstra and D* Lite over slope and roughness, re-planning when its radar finds rocks.", ["Python", "Pygame", "A*"], motif_rover, AMBER),
    "openrov": ("OpenROV-Base", "robotics · ros 2", "A ROS 2 Humble stack for underwater vehicles: IMU and depth drivers, PID for depth and heading, thruster control, YOLOv8 vision and leak failsafes.", ["ROS 2", "Python", "Docker"], motif_rov, CYAN),
    "resqswarm": ("ResQSwarm", "search & rescue", "Command panel for a swarm of insect-sized rescue robots: live telemetry over WebSockets and a debris map that flags breathing and heartbeat.", ["FastAPI", "WebSocket", "React"], motif_swarm, ROSE),
    "fylex": ("FYLEX", "social gaming", "A Steam-first social platform: library sync, looking-for-group, real-time chat and deals, in one monorepo with a shared schema package.", ["NestJS", "Postgres", "Redis", "Expo"], motif_fylex, VIOLET),
}


def main():
    (ASSETS / "header.svg").write_text(header())
    (ASSETS / "divider.svg").write_text(divider())
    for key, (title, kicker, desc, tags, motif, accent) in CARDS.items():
        (ASSETS / "cards" / f"{key}.svg").write_text(card(title, kicker, desc, tags, motif(), accent))
    print("built", 2 + len(CARDS), "images")


if __name__ == "__main__":
    main()
